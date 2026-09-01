# AEH GREEN + REFACTOR Runtime (Phase 12)
# AEH = Harness/Controller/Validator; coding done by external Agent.
# Core enforcement: Test Lock hash unchanged before/after.
import hashlib
import os
import re
import subprocess
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths
from ..doctor import doctor as doc
from . import change as ch
from . import coordination as coord
from . import grounding as gr
from . import red as rmod
from . import ownership as omod
from . import execution as xmod


class GreenError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _git_base(target):
    try:
        base = subprocess.run(["git", "-C", target, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=5)
        return base.stdout.strip() or None
    except Exception:
        return None


def _scope_base(target, scope):
    declared = scope.get("base_commit")
    if declared is None:
        return _git_base(target)
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", declared):
        raise GreenError("BLOCKED_SCOPE_VIOLATION: invalid base_commit")
    return declared.lower()


def _resolve_cwd(target, cwd):
    # cwd 必须位于 target repository 内（含 symlink 越界防护）
    if not cwd:
        return target
    p = cwd if os.path.isabs(cwd) else os.path.join(target, cwd)
    try:
        real_t = os.path.realpath(target)
        real_p = os.path.realpath(p)
        if os.path.commonpath([real_t, real_p]) != real_t:
            return None
    except (OSError, ValueError):
        return None
    return p


def run_execution(target, spec, allow_shell=False, ae_root=None):
    try:
        return xmod.run_execution(
            target, spec, allow_shell=allow_shell, ae_root=ae_root)
    except xmod.ExecutionPolicyError as exc:
        raise GreenError(str(exc)) from exc


def _lock_hash(lock):
    return hashlib.sha256(("\n".join(f["path"] + "\0" + f["hash"] for f in lock["files"])).encode("utf-8")).hexdigest()


def _portable_file_hashes(path):
    """Hash ordinary Git LF/CRLF materializations without relaxing content."""
    with open(path, "rb") as stream:
        content = stream.read()
    variants = {content}
    if b"\x00" not in content:
        canonical = content.replace(b"\r\n", b"\n")
        variants.add(canonical)
        variants.add(canonical.replace(b"\n", b"\r\n"))
    return {hashlib.sha256(item).hexdigest() for item in variants}


def _verify_lock(target, change_id, plan):
    cdir = ch._change_dir(target, change_id)
    lock_path = os.path.join(cdir, "test-lock.yaml")
    if not os.path.isfile(lock_path):
        raise GreenError("test-lock.yaml missing")
    lock = _load_yaml(lock_path)
    # 当前测试文件哈希 vs lock
    rmod._test_files_hash(target, plan)
    locked_files = lock.get("files") or []
    locked_by_path = {item.get("path"): item.get("hash") for item in locked_files}
    current_paths = []
    for tf in plan.get("test_files", []):
        p = os.path.join(target, tf["dest"])
        expected = locked_by_path.get(tf["dest"])
        if (not os.path.isfile(p) or not expected or
                expected not in _portable_file_hashes(p)):
            raise GreenError("BLOCKED_TEST_CHANGED")
        current_paths.append(tf["dest"])
    if (len(locked_by_path) != len(locked_files) or
            set(current_paths) != set(locked_by_path)):
        raise GreenError("BLOCKED_TEST_CHANGED")
    # protected 哈希（spec/evidence/profile/workflow）
    for prel, expect in (lock.get("protected") or {}).items():
        p = prel if os.path.isabs(prel) else os.path.join(target, prel)
        if not os.path.isfile(p):
            p = os.path.join(cdir, prel)
        if not os.path.isfile(p):
            raise GreenError("BLOCKED_RUNTIME_CONTEXT_STALE: protected file missing " + prel)
        if expect not in _portable_file_hashes(p):
            raise GreenError("BLOCKED_RUNTIME_CONTEXT_STALE: " + prel)
    return lock, _lock_hash(lock)


def _stale_excluding(target, change_id, exclude_paths):
    stale_all = gr.check_stale(target, change_id)["stale"]
    # 需要映射 EV id → rel_path
    ev_path = os.path.join(ch._change_dir(target, change_id), "evidence.yaml")
    index = _load_yaml(ev_path) if os.path.isfile(ev_path) else {"evidence": []}
    id_to_path = {}
    for e in index.get("evidence", []):
        ss = e.get("source_state") or {}
        if ss.get("rel_path"):
            id_to_path[e["id"]] = ss["rel_path"]
    norm_exclude = [p.replace(os.sep, "/") for p in exclude_paths]
    remain = []
    for ev_id in stale_all:
        p = id_to_path.get(ev_id)
        if p is None or p.replace(os.sep, "/") not in norm_exclude:
            remain.append(ev_id)
    return remain


def _load_scope(target, scope_path, change_id):
    if scope_path and os.path.isfile(scope_path):
        return _load_yaml(scope_path)
    # 默认 allowlist：Grounding 相关 source rel_paths
    ev_path = os.path.join(ch._change_dir(target, change_id), "evidence.yaml")
    index = _load_yaml(ev_path) if os.path.isfile(ev_path) else {"evidence": []}
    allowed = []
    for e in index.get("evidence", []):
        ss = e.get("source_state") or {}
        if ss.get("rel_path") and e.get("type") in ("SOURCE", "CONFIG"):
            allowed.append(ss["rel_path"])
    return {"allowed_paths": sorted(set(allowed)), "changed_files": []}

def _run_required(target, plan, cdir, prefix, change_id, allow_shell=False, ae_root=None):
    records = []
    red_rec = _load_yaml(os.path.join(cdir, "red.yaml"))
    required_ids = [t["test_id"] for t in red_rec.get("tests", []) if t["verdict"] == "VALID_RED"]
    tmap = {t["id"]: t for t in plan["tests"]}
    for tid in required_ids:
        t = tmap.get(tid)
        if t is None:
            raise GreenError("required RED test missing in plan: " + tid)
        execution = t.get("execution", {})
        argv = execution.get("argv")
        spec = {"command": None if argv is not None else (
                    execution.get("command") or t.get("command")),
                "argv": argv,
                "cwd": execution.get("cwd"),
                "timeout_seconds": execution.get("timeout_seconds", 60),
                "shell": execution.get("shell", False),
                "env": execution.get("env")}
        exit_code, output, cmd_repr = run_execution(
            target, spec, allow_shell=allow_shell, ae_root=ae_root)
        out_path = os.path.join(cdir, "evidence", prefix + "-" + tid + ".log")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        coord.atomic_write_text(out_path, output)
        with open(out_path, "rb") as f:
            output_hash = hashlib.sha256(f.read()).hexdigest()
        rec = {"test_id": tid, "command": t.get("command"),
               "exit_code": exit_code,
                        "output_ref": os.path.join(".aeh", "changes", change_id, "evidence", prefix + "-" + tid + ".log"),
                        "output_hash": output_hash, "verdict": "PASS" if exit_code == 0 else "FAIL"}
        if spec.get("argv") is not None:
            rec["argv"] = spec["argv"]
        records.append(rec)
        if exit_code != 0:
            return records, False
    return records, True


def _run_regression(target, plan, cdir, prefix, change_id, allow_shell=False, ae_root=None):
    reg_records = []
    for i, rg in enumerate(plan.get("regression", [])):
        spec = {"command": rg.get("command"), "argv": rg.get("argv"),
                "cwd": rg.get("cwd"), "timeout_seconds": rg.get("timeout_seconds", 120),
                "shell": rg.get("shell", False), "env": rg.get("env")}
        exit_code, output, cmd_repr = run_execution(
            target, spec, allow_shell=allow_shell, ae_root=ae_root)
        rid = rg.get("id") or ("REG-%02d" % (i + 1))
        out_path = os.path.join(cdir, "evidence", prefix + "-" + rid + ".log")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        coord.atomic_write_text(out_path, output)
        with open(out_path, "rb") as f:
            output_hash = hashlib.sha256(f.read()).hexdigest()
        reg_records.append({"test_id": rid, "exit_code": exit_code,
                            "output_ref": os.path.join(".aeh", "changes", change_id, "evidence", prefix + "-" + rid + ".log"),
                            "output_hash": output_hash, "verdict": "PASS" if exit_code == 0 else "FAIL"})
        if exit_code != 0:
            return reg_records, False
    return reg_records, True


def _green_core(target, change_id, scope_path, ae_root, verdict_kind, allow_shell=False):
    ae_root = ae_root or aeh_paths.ae_root()
    d = doc.run_doctor(target, ae_root)
    if d["overall"] == "BLOCKED":
        return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
    omod.ensure_state_available(target, change_id)
    # RED/LOCK_TEST establishes the ownership boundary before the coding agent
    # starts. GREEN must never adopt current YAML/JSON as a new baseline.
    omod.assert_checkpoint(target, change_id)
    change = ch.load_change(target, change_id)
    post_refactor_states = (
        "REFACTOR", "INTEGRATION", "RUNTIME_PLATFORM_VERIFY", "REGRESSION",
        "VERIFY", "REVIEW", "DRIFT_CHECK", "HUMAN_MERGE_APPROVAL", "ARCHIVE")
    if (verdict_kind == "GREEN_PASS" and
            change["state"]["current"] not in ("LOCK_TEST", "GREEN") + post_refactor_states):
        return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id, "state": change["state"]["current"]}
    if (verdict_kind == "REFACTOR_PASS" and
            change["state"]["current"] not in ("GREEN",) + post_refactor_states):
        return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id, "state": change["state"]["current"]}
    for g in ("grounding", "spec", "red"):
        if change.get("gates", {}).get(g) != "PASS":
            return {"status": "BLOCKED_GREEN_PRECONDITION", "change_id": change_id, "gate": g}
    cdir = ch._change_dir(target, change_id)
    plan = _load_yaml(os.path.join(cdir, "test-plan.yaml"))
    schema_plan = _load_yaml(os.path.join(ae_root, "schemas", "test-plan.schema.json"))
    jsonschema.validate(plan, schema_plan)
    lock, cur_lock_hash = _verify_lock(target, change_id, plan)
    scope = _load_scope(target, scope_path, change_id)
    allowed = set(scope.get("allowed_paths", []))
    changed = scope.get("changed_files", [])
    for cf in changed:
        if cf["path"] not in allowed:
            return {"status": "BLOCKED_SCOPE_VIOLATION", "change_id": change_id, "path": cf["path"]}
        full = os.path.join(target, cf["path"])
        if not os.path.isfile(full) or _sha256_file(full) != cf["after_hash"]:
            return {"status": "BLOCKED_SCOPE_VIOLATION", "change_id": change_id,
                    "error": "after_hash mismatch: " + cf["path"]}
    # stale evidence（排除本次受控修改的生产文件）
    exclude = [cf["path"] for cf in changed]
    stale = _stale_excluding(target, change_id, exclude)
    if stale:
        return {"status": "BLOCKED_RUNTIME_CONTEXT_STALE", "change_id": change_id, "stale": stale}
    plan["_cid"] = change_id
    recs, ok = _run_required(
        target, plan, cdir,
        "green" if verdict_kind == "GREEN_PASS" else "refactor",
        change_id, allow_shell=allow_shell, ae_root=ae_root)
    # Test processes execute repository-controlled code. Re-check after they
    # exit so their writes cannot be adopted by the next Controller seal.
    omod.assert_checkpoint(target, change_id)
    if not ok:
        return {"status": "GREEN_FAILED" if verdict_kind == "GREEN_PASS" else "REFACTOR_REGRESSION",
                "change_id": change_id, "tests": recs}
    reg_recs, reg_ok = _run_regression(
        target, plan, cdir,
        "green-reg" if verdict_kind == "GREEN_PASS" else "refactor-reg",
        change_id, allow_shell=allow_shell, ae_root=ae_root)
    omod.assert_checkpoint(target, change_id)
    if not reg_ok:
        return {"status": "GREEN_FAILED" if verdict_kind == "GREEN_PASS" else "REFACTOR_REGRESSION",
                "change_id": change_id, "regression": reg_recs}
    # GREEN 后 test hash 仍 == lock
    lock2, cur_lock_hash2 = _verify_lock(target, change_id, plan)
    if cur_lock_hash2 != cur_lock_hash:
        return {"status": "BLOCKED_TEST_CHANGED", "change_id": change_id}
    base_commit = _scope_base(target, scope)
    if not changed:
        return {"status": "BLOCKED_SCOPE_VIOLATION", "change_id": change_id, "error": "no changed_files declared"}
    before_parts = sorted(cf["before_hash"] + "\0" + cf["path"] for cf in changed)
    after_parts = sorted(cf["after_hash"] + "\0" + cf["path"] for cf in changed)
    prod_before = hashlib.sha256("\n".join(before_parts).encode("utf-8")).hexdigest()
    prod_after = hashlib.sha256("\n".join(after_parts).encode("utf-8")).hexdigest()
    code_files = []
    for i, cf in enumerate(sorted(changed, key=lambda x: x["path"])):
        code_files.append({"code_id": "CODE-%03d" % (i + 1), "path": cf["path"],
                           "before_hash": cf["before_hash"], "after_hash": cf["after_hash"]})
    evidence = {"contract": "green.evidence", "version": 1, "change_id": change_id,
                "base_commit": base_commit, "test_lock_hash": cur_lock_hash,
                "production_before_hash": prod_before, "production_after_hash": prod_after,
                "tests": recs, "changed_files": code_files, "verdict": verdict_kind}
    schema_g = _load_yaml(os.path.join(ae_root, "schemas", "green.schema.json"))
    jsonschema.validate(evidence, schema_g)
    fname = "green.yaml" if verdict_kind == "GREEN_PASS" else "refactor.yaml"
    coord.atomic_write_text(os.path.join(cdir, fname), _dump_yaml(evidence))
    change = ch.load_change(target, change_id)
    change["gates"] = dict(change.get("gates") or {})
    if verdict_kind == "GREEN_PASS":
        change["gates"]["lock_test"] = "PASS"
        change["gates"]["green"] = "PASS"
        ch.save_change(target, change)
        if change["state"]["current"] in post_refactor_states:
            tr = {"status": "TRANSITION_OK", "change_id": change_id,
                  "from": change["state"]["current"],
                  "to": change["state"]["current"],
                  "state": change["state"], "idempotent": True}
        elif change["state"]["current"] == "GREEN":
            tr = {"status": "TRANSITION_OK", "change_id": change_id,
                  "from": "GREEN", "to": "GREEN",
                  "state": change["state"], "idempotent": True}
        else:
            tr = ch.change_transition(target, change_id, "GREEN")
    else:
        ch.save_change(target, change)
        if change["state"]["current"] in post_refactor_states:
            tr = {"status": "TRANSITION_OK", "change_id": change_id,
                  "from": change["state"]["current"],
                  "to": change["state"]["current"],
                  "state": change["state"], "idempotent": True}
        else:
            tr = ch.change_transition(target, change_id, "REFACTOR")
    if tr["status"] != "TRANSITION_OK":
        return {"status": verdict_kind + "_BUT_TRANSITION_FAILED", "change_id": change_id, "transition": tr}
    omod.record_checkpoint(target, change_id)
    return {"status": "GREEN_COMPLETE" if verdict_kind == "GREEN_PASS" else "REFACTOR_COMPLETE",
            "change_id": change_id, "verdict": verdict_kind,
            "state": change["state"]["current"]}


@coord.coordinated_change_mutator("CHANGE_GREEN")
def change_green(target, change_id, scope_path=None, ae_root=None, allow_shell=False):
    try:
        return _green_core(
            target, change_id, scope_path, ae_root, "GREEN_PASS",
            allow_shell=allow_shell)
    except (GreenError, omod.OwnershipError, ch.ChangeError, jsonschema.ValidationError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "GREEN_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}


@coord.coordinated_change_mutator("CHANGE_REFACTOR")
def change_refactor(target, change_id, scope_path=None, ae_root=None, allow_shell=False):
    try:
        return _green_core(
            target, change_id, scope_path, ae_root, "REFACTOR_PASS",
            allow_shell=allow_shell)
    except (GreenError, omod.OwnershipError, ch.ChangeError, jsonschema.ValidationError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "REFACTOR_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}
