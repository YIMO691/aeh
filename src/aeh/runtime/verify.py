# AEH VERIFY Runtime (Phase 13)
# 最终工程闭环：风险分级验证 + 可信人工批准 + 可追溯性，产出 verification.yaml。
# AEH 是 Validator：验证/判定/写证据，绝不 merge/push/PR（停在 MERGE_READY）。
import hashlib
import os
import yaml
import jsonschema
from datetime import datetime, timezone

from .. import paths as aeh_paths
from ..doctor import doctor as doc
from . import change as ch
from . import green as gmod
from . import approval as amod
from . import traceability as tmod


class VerifyError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _level_of(change):
    cls = change.get("classification")
    if isinstance(cls, dict):
        return (cls.get("level") or "").upper()
    return (cls or "").upper()


def _log_result(cdir, change_id, prefix, rid, output):
    out_path = os.path.join(cdir, "evidence", prefix + "-" + str(rid) + ".log")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    with open(out_path, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    return os.path.join(".aeh", "changes", change_id, "evidence", prefix + "-" + str(rid) + ".log"), h


def _exec_spec(entry):
    spec = {"command": entry.get("command"), "argv": entry.get("argv"),
            "cwd": entry.get("cwd"), "timeout_seconds": entry.get("timeout_seconds", 120)}
    return spec


def _red_block(red_rec):
    for t in red_rec.get("tests", []):
        if t.get("verdict") == "VALID_RED":
            block = {"test_id": t["test_id"], "command": t["command"], "exit_code": t["exit_code"],
                     "output_ref": t["output_ref"], "output_hash": t["output_hash"],
                     "expected_failure": t.get("expected_failure"), "actual_failure": t.get("actual_failure"),
                     "repository_state": {"base_commit": t.get("base_commit"),
                                          "changed_files_hash": t.get("changed_files_hash"),
                                          "test_files_hash": t.get("test_files_hash")},
                     "verdict": t["verdict"]}
            if t.get("commit") is not None:
                block["commit"] = t["commit"]
            return block
    return None


def _record_blocked(cdir, change_id, reason, results, red_block, ae_root):
    # 诚实的失败记录：BLOCKED 也要落 verification.yaml（overall=BLOCKED + blocked_reason），
    # 绝不静默返回；verify gate 不会被置位。
    body = {"results": results, "overall": "BLOCKED", "blocked_reason": reason,
            "verified_at": datetime.now(timezone.utc).isoformat()}
    if red_block:
        body["red"] = red_block
    jsonschema.validate(body, _load_yaml(os.path.join(ae_root, "schemas", "verification.schema.json")))
    with open(os.path.join(cdir, "verification.yaml"), "w", encoding="utf-8") as f:
        f.write(_dump_yaml(body))


def _run_one(target, cdir, change_id, entry, rid, verifies, vtype, prefix):
    spec = _exec_spec(entry)
    exit_code, output, _ = gmod.run_execution(target, spec)
    out_ref, out_hash = _log_result(cdir, change_id, prefix, rid, output)
    verdict = "pass" if exit_code == 0 else "fail"
    rec = {"id": "VER-%03d" % rid, "type": vtype, "verifies": sorted(set(verifies)),
           "method": "automated_test", "status": verdict, "exit_code": exit_code,
           "output_ref": out_ref, "output_hash": out_hash, "verdict": verdict}
    if entry.get("argv") is not None:
        rec["argv"] = entry["argv"]
    return rec


def _verify_core(target, change_id, ae_root):
    ae_root = ae_root or aeh_paths.ae_root()
    d = doc.run_doctor(target, ae_root)
    if d["overall"] == "BLOCKED":
        return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
    change = ch.load_change(target, change_id)
    if change["state"]["current"] not in ("GREEN", "REFACTOR", "VERIFY"):
        return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                "state": change["state"]["current"]}
    for g in ("grounding", "spec", "red", "green"):
        if change.get("gates", {}).get(g) != "PASS":
            return {"status": "BLOCKED_VERIFY_PRECONDITION", "change_id": change_id, "gate": g}
    cdir = ch._change_dir(target, change_id)
    plan = _load_yaml(os.path.join(cdir, "test-plan.yaml"))
    jsonschema.validate(plan, _load_yaml(os.path.join(ae_root, "schemas", "test-plan.schema.json")))
    spec = _load_yaml(os.path.join(cdir, "spec.yaml"))
    red_rec = _load_yaml(os.path.join(cdir, "red.yaml"))
    green_rec = _load_yaml(os.path.join(cdir, "green.yaml")) if os.path.isfile(os.path.join(cdir, "green.yaml")) else _load_yaml(os.path.join(cdir, "refactor.yaml"))
    gmod._verify_lock(target, change_id, plan)
    exclude = [cf["path"] for cf in green_rec.get("changed_files", [])]
    stale = gmod._stale_excluding(target, change_id, exclude)
    if stale:
        return {"status": "BLOCKED_RUNTIME_CONTEXT_STALE", "change_id": change_id, "stale": stale}
    level = _level_of(change)
    if level not in ("DIRECT", "LIGHTWEIGHT", "STANDARD", "CRITICAL"):
        return {"status": "BLOCKED_VERIFY_PRECONDITION", "change_id": change_id, "error": "unknown classification " + level}
    red_block = _red_block(red_rec)
    tmap = {t["id"]: t for t in plan.get("tests", [])}

    results = []
    rid = 0
    # 1) 目标测试（GREEN 记录的 required 重跑）
    for gt in green_rec.get("tests", []):
        t = tmap.get(gt["test_id"])
        if t is None:
            return {"status": "BLOCKED_VERIFY_PRECONDITION", "change_id": change_id,
                    "error": "green test missing in plan: " + gt["test_id"]}
        rid += 1
        entry = {"command": t.get("command"), "argv": t.get("execution", {}).get("argv"),
                 "cwd": t.get("execution", {}).get("cwd"),
                 "timeout_seconds": t.get("execution", {}).get("timeout_seconds", 60)}
        results.append(_run_one(target, cdir, change_id, entry, rid, t.get("verifies", []), "target_test", "verify"))
    # 2) 回归
    for rg in plan.get("regression", []):
        rid += 1
        results.append(_run_one(target, cdir, change_id, rg, rid, [], "regression", "verify-reg"))
    # 3) 声明式附加验证
    ventries = plan.get("verification", [])
    vtypes = set()
    for v in ventries:
        vtypes.add(v.get("type", ""))
    if level == "CRITICAL" and not (vtypes & {"integration", "contract"}):
        _record_blocked(cdir, change_id, "CRITICAL requires declared integration/contract verification",
                        results, red_block, ae_root)
        return {"status": "BLOCKED_VERIFICATION_PLAN_INSUFFICIENT", "change_id": change_id,
                "error": "CRITICAL requires declared integration/contract verification"}
    for v in ventries:
        vtype = v.get("type", "")
        if vtype in ("target_test", "regression"):
            continue
        if vtype == "manual":
            rid += 1
            results.append({"id": "VER-%03d" % rid, "type": "manual", "verifies": sorted(set(v.get("verifies", []))),
                            "method": "manual_runtime", "status": "pending", "verdict": "pending"})
            continue
        if v.get("command") or v.get("argv"):
            rid += 1
            results.append(_run_one(target, cdir, change_id, v, rid, v.get("verifies", []), vtype or "runtime", "verify-v"))
        else:
            rid += 1
            results.append({"id": "VER-%03d" % rid, "type": vtype or "runtime",
                            "verifies": sorted(set(v.get("verifies", []))),
                            "method": "manual_runtime", "status": "not_applicable", "verdict": "not_applicable"})

    # 人工批准（approval 不能推翻技术失败；只解除需要人工的阻塞）
    approvals = amod.load_approvals(target, change_id)
    ap_path = os.path.join(cdir, "approvals.yaml")
    if os.path.isfile(ap_path):
        try:
            jsonschema.validate(_load_yaml(ap_path), _load_yaml(os.path.join(ae_root, "schemas", "approvals.schema.json")))
        except jsonschema.ValidationError:
            _record_blocked(cdir, change_id, "approvals.yaml failed schema validation (possible fabricated approval)",
                            results, red_block, ae_root)
            return {"status": "BLOCKED_INVALID_APPROVALS", "change_id": change_id}
    warnings = []
    manual_pending = []
    for r in results:
        if r.get("type") == "manual":
            # V0.1：手动验证不伪造自动化，也不引入 core 外的批准 gate；
            # 一律 pending，由 REVIEW 阶段人工完成（Phase 14）。
            manual_pending.append(r["id"])
    if manual_pending:
        _record_blocked(cdir, change_id, "manual verification pending human attestation: " + ",".join(manual_pending),
                        results, red_block, ae_root)
        return {"status": "BLOCKED_MANUAL_VERIFICATION_PENDING", "change_id": change_id, "vers": manual_pending}
    for r in results:
        if r.get("verdict") == "fail":
            failing = [x["id"] for x in results if x.get("verdict") == "fail"]
            _record_blocked(cdir, change_id, "verification failed: " + ",".join(failing),
                            results, red_block, ae_root)
            return {"status": "BLOCKED_VERIFICATION_FAILED", "change_id": change_id, "failing": failing}
        if r.get("verdict") == "not_applicable":
            warnings.append(r["id"] + " not_applicable")

    merge = approvals.get("MERGE_GATE", {})
    if merge.get("status") == "REJECTED":
        _record_blocked(cdir, change_id, "human MERGE_GATE approval REJECTED", results, red_block, ae_root)
        return {"status": "BLOCKED_HUMAN_MERGE_REJECTED", "change_id": change_id}
    if level == "CRITICAL" and merge.get("status") != "APPROVED":
        _record_blocked(cdir, change_id, "CRITICAL requires trusted human MERGE_GATE approval (aeh change approve)",
                        results, red_block, ae_root)
        return {"status": "BLOCKED_HUMAN_APPROVAL_REQUIRED", "change_id": change_id,
                "error": "CRITICAL requires trusted human MERGE_GATE approval (aeh change approve) before MERGE_READY"}
    if level == "CRITICAL" and merge.get("status") == "APPROVED":
        warnings.append("CRITICAL MERGE_GATE approved by " + (merge.get("actor", {}).get("id") or "?"))

    body = {"results": results, "overall": "READY_WITH_WARNINGS" if warnings else "MERGE_READY",
            "verified_at": datetime.now(timezone.utc).isoformat()}
    if warnings:
        body["warnings"] = warnings
    if red_block:
        body["red"] = red_block
    jsonschema.validate(body, _load_yaml(os.path.join(ae_root, "schemas", "verification.schema.json")))
    with open(os.path.join(cdir, "verification.yaml"), "w", encoding="utf-8") as f:
        f.write(_dump_yaml(body))

    # 可追溯性（必须先有 verification.yaml 才能建 VER 链）
    tr = tmod.build_traceability(target, change_id, ae_root)
    if tr["status"] != "TRACEABILITY_COMPLETE":
        _record_blocked(cdir, change_id, "traceability incomplete: " + "; ".join(tr.get("issues", [])),
                        results, red_block, ae_root)
        return {"status": tr["status"], "change_id": change_id, "issues": tr.get("issues")}

    overall = body["overall"]
    # 技术全绿才置 VERIFY gate 与状态迁移；approval 缺口不置 gate
    change = ch.load_change(target, change_id)
    change["gates"] = dict(change.get("gates") or {})
    change["gates"]["verify"] = "PASS"
    ch.save_change(target, change)
    if change["state"]["current"] != "VERIFY":
        tr2 = ch.change_transition(target, change_id, "VERIFY")
        if tr2["status"] != "TRANSITION_OK":
            return {"status": "BLOCKED_TRANSITION_FAILED", "change_id": change_id, "transition": tr2}

    _write_review_md(cdir, change_id, level, results, overall, warnings, tr["traceability"])
    return {"status": "VERIFY_COMPLETE", "change_id": change_id, "overall": overall,
            "state": "VERIFY", "results": len(results), "warnings": warnings}

def _write_review_md(cdir, change_id, level, results, overall, warnings, traceability):
    # review.md 是人工叙事投影（非机器事实）；机器事实 = verification.yaml + traceability.yaml
    lines = []
    lines.append("# AEH Review Projection — " + change_id)
    lines.append("")
    lines.append("> This file is a human-readable projection only. Machine truth lives in")
    lines.append("> verification.yaml / traceability.yaml / approvals.yaml.")
    lines.append("")
    lines.append("- classification: " + level)
    lines.append("- overall verdict: " + overall)
    lines.append("- state: VERIFY (stop — no merge/push/PR is performed by AEH)")
    lines.append("")
    lines.append("## Verification results")
    lines.append("")
    for r in results:
        extra = ""
        if r.get("exit_code") is not None:
            extra = " (exit " + str(r["exit_code"]) + ")"
        lines.append("- " + r["id"] + " [" + r.get("type", "?") + "] verdict=" + r.get("verdict", "?") + extra)
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        for w in warnings:
            lines.append("- " + w)
    lines.append("")
    lines.append("## Traceability")
    for req in traceability.get("requirements", []):
        lines.append("- " + req["id"] + ": AC=" + ",".join(req.get("acceptance", [])) +
                     " TEST=" + ",".join(req.get("tests", [])) +
                     " CODE=" + ",".join(c.get("path", "") for c in req.get("code", [])) +
                     " VER=" + ",".join(req.get("verification", [])))
    lines.append("")
    lines.append("## Human approval")
    lines.append("")
    lines.append("AEH records only honest human attestation via aeh change approve.")
    lines.append("Approval can never override a technical failure.")
    lines.append("")
    with open(os.path.join(cdir, "review.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def change_verify(target, change_id, ae_root=None):
    try:
        return _verify_core(target, change_id, ae_root)
    except (VerifyError, gmod.GreenError, ch.ChangeError, jsonschema.ValidationError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "VERIFY_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}

def change_review(target, change_id, ae_root=None):
    """只读投影：从 machine artifacts 重建 review.md。绝不写 APPROVED。"""
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        cdir = ch._change_dir(target, change_id)
        change = ch.load_change(target, change_id)
        ver_path = os.path.join(cdir, "verification.yaml")
        if not os.path.isfile(ver_path):
            return {"status": "BLOCKED_REVIEW_PRECONDITION", "change_id": change_id,
                    "error": "verification.yaml missing — run aeh change verify first"}
        ver = _load_yaml(ver_path)
        trace = _load_yaml(os.path.join(cdir, "traceability.yaml"))
        _write_review_md(cdir, change_id, _level_of(change), ver.get("results", []),
                         ver.get("overall", "BLOCKED"), ver.get("warnings", []), trace)
        return {"status": "REVIEW_READY", "change_id": change_id, "overall": ver.get("overall")}
    except (VerifyError, ch.ChangeError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "REVIEW_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}
