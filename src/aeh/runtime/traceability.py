# AEH TRACEABILITY (Phase 13)
# 建立并验证 REQ<->AC<->TEST<->CODE<->VER 双向链 + 孤儿检测。
# 机器事实：traceability.yaml（YAML 契约）；review.md 只是人工叙事投影。
import os
import yaml
import jsonschema

from .. import paths as aeh_paths
from . import change as ch


class TraceError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _norm(p):
    return p.replace(os.sep, "/")


def build_traceability(target, change_id, ae_root=None):
    ae_root = ae_root or aeh_paths.ae_root()
    cdir = ch._change_dir(target, change_id)
    spec = _load_yaml(os.path.join(cdir, "spec.yaml"))
    plan = _load_yaml(os.path.join(cdir, "test-plan.yaml"))
    refactor_path = os.path.join(cdir, "refactor.yaml")
    if os.path.isfile(refactor_path):
        green = _load_yaml(refactor_path)
    else:
        green = _load_yaml(os.path.join(cdir, "green.yaml"))
    ver_path = os.path.join(cdir, "verification.yaml")
    ver = _load_yaml(ver_path) if os.path.isfile(ver_path) else {"results": []}

    # 索引：AC -> tests；CODE path -> 归属测试集合；VER -> verifies
    ac_to_tests = {}
    test_targets = {}
    for t in plan.get("tests", []):
        for ac in t.get("verifies", []):
            ac_to_tests.setdefault(ac, []).append(t["id"])
        test_targets[t["id"]] = [x for x in t.get("targets", [])]
    non_auto = {n["ac_id"]: n.get("reason", "") for n in plan.get("non_automatable", [])}
    code_files = green.get("changed_files", [])
    ver_by_id = {r["id"]: r for r in ver.get("results", [])}

    requirements = []
    issues = []
    covered_code = set()
    used_tests = set()
    used_ver = set()

    for req in spec.get("requirements", []):
        acs = [a["id"] for a in req.get("acceptance", [])]
        tests = []
        for a in acs:
            tests.extend(ac_to_tests.get(a, []))
        tests = sorted(set(tests))
        used_tests.update(tests)
        # 前向：automated/invariant AC 必须有测试（除非 non_automatable 且带理由）
        for a in req.get("acceptance", []):
            if a.get("type") in ("automated", "invariant") and a["id"] not in ac_to_tests:
                if a["id"] not in non_auto or not non_auto[a["id"]]:
                    issues.append("uncovered AC " + a["id"] + " (REQ " + req["id"] + ") has no test")
        # CODE：被这些测试 targets 引用的生产文件
        tgt = set()
        for tid in tests:
            tgt.update(test_targets.get(tid, []))
        code = []
        for cf in code_files:
            if _norm(cf["path"]) in tgt:
                item = {"path": _norm(cf["path"])}
                if cf.get("code_id"):
                    item["code_id"] = cf["code_id"]
                code.append(item)
                covered_code.add(_norm(cf["path"]))
        # VER：verifies 命中本 REQ AC 的验证记录
        vids = []
        for vid, r in ver_by_id.items():
            if set(r.get("verifies", [])) & set(acs):
                vids.append(vid)
                used_ver.add(vid)
            elif r.get("type") == "regression" and not r.get("verifies"):
                vids.append(vid)
                used_ver.add(vid)
        requirements.append({"id": req["id"], "acceptance": acs, "tests": tests,
                             "code": code, "verification": sorted(vids)})

    # 反向：孤儿检测
    known_acs = {a["id"] for r in spec.get("requirements", []) for a in r.get("acceptance", [])}
    for t in plan.get("tests", []):
        if t["id"] not in used_tests:
            unknown = [v for v in t.get("verifies", []) if v not in known_acs]
            issues.append("orphan test " + t["id"] + " verifies unknown AC " + ",".join(unknown or ["(none)"]))
    for cf in code_files:
        if _norm(cf["path"]) not in covered_code:
            issues.append("orphan code " + cf["path"] + " not linked to any REQ via test targets")
    for vid in ver_by_id:
        if vid not in used_ver and not (ver_by_id[vid].get("type") == "regression" and not ver_by_id[vid].get("verifies")):
            issues.append("orphan verification " + vid + " not linked to any REQ")

    body = {"requirements": requirements}
    schema = _load_yaml(os.path.join(ae_root, "schemas", "traceability.schema.json"))
    jsonschema.validate(body, schema)
    with open(os.path.join(cdir, "traceability.yaml"), "w", encoding="utf-8") as f:
        f.write(_dump_yaml(body))
    if issues:
        return {"status": "BLOCKED_TRACEABILITY_INCOMPLETE", "change_id": change_id,
                "issues": issues, "traceability": body}
    return {"status": "TRACEABILITY_COMPLETE", "change_id": change_id,
            "requirements": len(requirements), "traceability": body}
