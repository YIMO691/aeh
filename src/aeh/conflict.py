"""AEH Conflict Resolver — Normalize + Resolve（Phase 4）

原则（frozen P-07/P-08/P-10/P-13）：
- 不同优先级冲突：高覆盖低；被覆盖规则的 provenance 必须保留（shadowed）。
- 同一级别、同一 field、不同有效值 → BLOCKED_POLICY_CONFLICT，禁止静默选择。
- 同一级别、同一值 → 不产生冲突（确定性取 origin_ref 最小者）。
- 本阶段只输出阻塞与 conflict record，不做组织权限认证。
- Discovery Fact 是事实输入（source=repository_fact, scope=default），不伪装成政策。
- 只读、无网络。
"""
import hashlib
import json
import yaml

from . import paths as aeh_paths

class CompilerError(ValueError):
    pass


SCOPE_TO_PRECEDENCE = {
    # interview 问题 scope → 冻结优先级 scope（CD-018 补充）
    "organization": "organization",
    "team": "team",
    "developer": "developer",
    "core": "project",
    "ai_permissions": "project",
}


def load_precedence(path=None):
    with open(path or aeh_paths.join("core", "precedence.yaml"), "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    order = data["order"]
    assert data["same_level_conflict"]["verdict"] == "BLOCKED_POLICY_CONFLICT"
    return order


def _stable_value(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _answer_source(a):
    # 只有 ref ID，绝不携带正文（minimum disclosure）
    src_type = a.get("source", "user_answer")
    return {"type": src_type, "ref": a.get("origin_ref") or a.get("question_id")}


def normalize(questions, answers, discovery, precedence_order, harness_defaults=None, multi_fields=None):
    """输入归一化为统一 Rule Record {field, value, scope, source, confidence, origin_ref, type}。

    拒绝：非法 option 答案（banana 类）；未知 question_id；task 通道（Phase 4 无输入通道）。
    """
    qmap = {q["question_id"]: q for q in questions}
    records = []

    # 1) Discovery Facts（事实，不伪装成政策）
    for f in (discovery or {}).get("facts", []):
        records.append({
            "field": f["domain"] + "." + f["field"],
            "value": f["value"],
            "scope": "default",
            "source": "repository_fact",
            "confidence": f.get("confidence", "UNKNOWN"),
            "origin_ref": f["id"],
            "type": "FACT",
        })

    # 2) Interview Answers（保留四类语义）
    for qid, a in ((answers or {}).get("answers", {})).items():
        q = qmap.get(qid)
        if q is None:
            raise CompilerError("answers reference unknown question_id: " + qid)
        opts = q.get("options") or []
        if opts and a["answer"] not in [o["value"] for o in opts]:
            raise CompilerError("illegal interview answer for " + qid + ": " + repr(a["answer"]))
        if q.get("type") == "FACT":
            scope = "default"
        else:
            scope = SCOPE_TO_PRECEDENCE.get(q.get("scope"), "project")
        records.append({
            "field": q["field"],
            "value": a["answer"],
            "scope": scope,
            "source": a.get("source", "user_answer"),
            "confidence": a.get("confidence", "USER_CONFIRMED"),
            "origin_ref": qid,
            "type": q["type"],
        })

    # 3) Harness Defaults（问题 default + 显式 defaults；最低优先级）
    for q in questions:
        if q.get("default") is not None:
            records.append({
                "field": q["field"],
                "value": q["default"],
                "scope": "default",
                "source": "default_applied",
                "confidence": "UNKNOWN",
                "origin_ref": "default:" + q["question_id"],
                "type": q["type"],
            })
    for d in (harness_defaults or []):
        records.append({
            "field": d["field"],
            "value": d["value"],
            "scope": "default",
            "source": d.get("source", "default_applied"),
            "confidence": d.get("confidence", "UNKNOWN"),
            "origin_ref": d.get("origin_ref", "harness:" + d["field"]),
            "type": d.get("type", "POLICY"),
        })

    # 多值事实折叠（release-fix 002）：同一 field 的多个 repository_fact
    # 合并为单一列表值（确定性排序）；非 multi field 维持 BLOCKED_POLICY_CONFLICT 语义。
    multi = set(multi_fields or [])
    if multi:
        by_mf = {}
        rest = []
        for r in records:
            if r["source"] == "repository_fact" and r["field"] in multi:
                by_mf.setdefault(r["field"], []).append(r)
            else:
                rest.append(r)
        records = rest
        for field in sorted(by_mf):
            group = by_mf[field]
            values = sorted(set(_stable_value(v["value"]) for v in group))
            decoded = [json.loads(v) for v in values]
            merged_value = decoded[0] if len(decoded) == 1 else decoded
            conf = "UNKNOWN"
            for c in ("DETECTED", "INFERRED", "USER_CONFIRMED"):
                if any(v["confidence"] == c for v in group):
                    conf = c
                    break
            records.append({
                "field": field,
                "value": merged_value,
                "scope": "default",
                "source": "repository_fact",
                "confidence": conf,
                "origin_ref": "merged:" + ",".join(sorted(set(v["origin_ref"] for v in group))),
                "type": "FACT",
            })
    for r in records:
        if r["scope"] not in precedence_order:
            raise CompilerError("unsupported scope in rule record: " + r["scope"])
    return records


def resolve(records, precedence_order):
    """确定性冲突解析：返回 {resolved, conflicts, shadowed}。"""
    rank = {s: i for i, s in enumerate(precedence_order)}
    by_field = {}
    for r in records:
        by_field.setdefault(r["field"], []).append(r)

    resolved = {}
    conflicts = []
    shadowed = {}
    cid = 0
    for field in sorted(by_field):
        group = sorted(by_field[field], key=lambda r: (rank[r["scope"]], r["origin_ref"] or ""))
        top_rank = min(rank[r["scope"]] for r in group)
        top = [r for r in group if rank[r["scope"]] == top_rank]
        values = {_stable_value(r["value"]) for r in top}
        if len(values) > 1:
            cid += 1
            conflicts.append({
                "conflict_id": "CONF-%03d" % cid,
                "field": field,
                "level": top[0]["scope"],
                "candidates": [
                    {"value": r["value"], "source": {"type": r["source"], "ref": r["origin_ref"]}}
                    for r in sorted(top, key=lambda r: r["origin_ref"] or "")
                ],
                "resolution": None,
                "status": "BLOCKED_POLICY_CONFLICT",
            })
            overridden = [r for r in group if rank[r["scope"]] < top_rank]
            if overridden:
                shadowed[field] = overridden
            continue  # 该 field 被阻塞，不进入 resolved
        winner = top[0]
        overridden = [r for r in group if r is not winner]
        resolved[field] = winner
        if overridden:
            shadowed[field] = overridden
    return {"resolved": resolved, "conflicts": conflicts, "shadowed": shadowed}
