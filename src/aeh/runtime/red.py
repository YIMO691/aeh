"""AEH RED Runtime（Phase 11 后半）

真实执行 required tests，按冻结路由分类 verdict（VALID_RED / INVALID_RED_* / NO_RED_ALREADY_GREEN），
全部 VALID_RED → 计算 Test Lock → 进入 LOCK_TEST。绝不进入 GREEN，绝不修改生产实现。
"""
import hashlib
import os
import subprocess
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths
from ..doctor import doctor as doc
from . import change as ch
from . import grounding as gr
from . import ownership as omod

ENV_SIGNATURES = ["ModuleNotFoundError", "ImportError", "command not found", "No such file or directory"]


class RedError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _git_base(target):
    try:
        base = subprocess.run(["git", "-C", target, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=5)
        return base.stdout.strip() or None
    except Exception:
        return None


def _snapshot(target, exclude_rel):
    out = {}
    for dp, dns, fns in os.walk(target):
        dns[:] = [d for d in dns if d != "__pycache__"]
        if "__pycache__" in dp:
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, target)
            if rel.startswith(exclude_rel):
                continue
            with open(p, "rb") as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


def _test_files_hash(target, plan):
    parts = []
    paths = sorted(set(tf["dest"] for tf in plan.get("test_files", [])))
    for rel in paths:
        p = os.path.join(target, rel)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                parts.append(rel + "\0" + hashlib.sha256(f.read()).hexdigest())
    return hashlib.sha256(("\n".join(parts)).encode("utf-8")).hexdigest()


def classify_red(exit_code, output, t):
    if exit_code == 0:
        return "NO_RED_ALREADY_GREEN", {"category": "none", "signature": "exit_code==0"}
    sig = (t.get("expected_before_fix") or {}).get("signature", "")
    if sig and sig in output:
        return "VALID_RED", {"category": "behavior", "signature": sig}
    for s in t.get("test_defect_signatures", []):
        if s in output:
            return "INVALID_RED_TEST_DEFECT", {"category": "test_defect", "signature": s}
    for s in t.get("spec_mismatch_signatures", []):
        if s in output:
            return "INVALID_RED_SPEC_MISMATCH", {"category": "spec_mismatch", "signature": s}
    for s in t.get("fixture_signatures", []):
        if s in output:
            return "INVALID_RED_FIXTURE", {"category": "fixture", "signature": s}
    for s in ENV_SIGNATURES:
        if s in output:
            return "INVALID_RED_ENVIRONMENT", {"category": "environment", "signature": s}
    return "INVALID_RED_UNEXPECTED_FAILURE", {"category": "unexpected", "signature": "unmatched"}

def change_red(target, change_id, ae_root=None):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        omod.ensure_state_available(target, change_id)
        had_checkpoint = omod.checkpoint_exists(target, change_id)
        if had_checkpoint:
            omod.assert_checkpoint(target, change_id)
        change = ch.load_change(target, change_id)
        if change["state"]["current"] not in ("TEST_DESIGN", "RED", "LOCK_TEST"):
            return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                    "state": change["state"]["current"]}
        if change.get("gates", {}).get("test_design") != "PASS":
            return {"status": "BLOCKED_TEST_DESIGN_GATE", "change_id": change_id}
        stale = gr.check_stale(target, change_id)["stale"]
        if stale:
            return {"status": "BLOCKED_STALE_EVIDENCE", "change_id": change_id, "stale": stale}
        plan = _load_yaml(os.path.join(ch._change_dir(target, change_id), "test-plan.yaml"))
        schema_plan = _load_yaml(os.path.join(ae_root, "schemas", "test-plan.schema.json"))
        jsonschema.validate(plan, schema_plan)
        if change["state"]["current"] == "TEST_DESIGN":
            tr0 = ch.change_transition(target, change_id, "RED")
            if tr0["status"] != "TRANSITION_OK":
                return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id, "transition": tr0}
            change = ch.load_change(target, change_id)
        before = _snapshot(target, os.path.join(".aeh", "changes", change_id))
        cdir = ch._change_dir(target, change_id)
        base_commit = _git_base(target)
        tests_hash = _test_files_hash(target, plan)
        results = []
        required = [t for t in plan["tests"] if t.get("required", True)]
        for t in required:
            cmd = t.get("execution", {}).get("command") or t["command"]
            timeout = t.get("execution", {}).get("timeout_seconds", 60)
            try:
                proc = subprocess.run(cmd, shell=True, cwd=target, capture_output=True,
                                      text=True, timeout=timeout)
                exit_code = proc.returncode
                output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            except subprocess.TimeoutExpired:
                exit_code = 124
                output = "timeout"
            except OSError as e:
                exit_code = 127
                output = str(e)
            verdict, actual = classify_red(exit_code, output, t)
            out_path = os.path.join(cdir, "evidence", "red-" + t["id"] + ".log")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(output)
            with open(out_path, "rb") as f:
                output_hash = hashlib.sha256(f.read()).hexdigest()
            results.append({"test_id": t["id"], "command": cmd, "exit_code": exit_code,
                            "output_ref": os.path.join(".aeh", "changes", change_id, "evidence", "red-" + t["id"] + ".log"),
                            "output_hash": output_hash,
                            "expected_failure": {"category": "behavior", "signature": (t.get("expected_before_fix") or {}).get("signature", "")},
                            "actual_failure": actual,
                            "base_commit": base_commit,
                            "changed_files_hash": tests_hash, "test_files_hash": tests_hash,
                            "commit": None, "verdict": verdict})
        after = _snapshot(target, os.path.join(".aeh", "changes", change_id))
        if had_checkpoint:
            # A repeated RED executes repository code after the initial seal.
            # Do not let that execution extend Controller-owned machine truth.
            omod.assert_checkpoint(target, change_id)
        if before != after:
            return {"status": "BLOCKED_PRODUCTION_CHANGED_DURING_RED", "change_id": change_id,
                    "changed": sorted(set(before) ^ set(after))}
        red_record = {"contract": "red.evidence", "version": 1, "change_id": change_id, "tests": results}
        schema_red = _load_yaml(os.path.join(ae_root, "schemas", "red.schema.json"))
        jsonschema.validate(red_record, schema_red)
        with open(os.path.join(cdir, "red.yaml"), "w", encoding="utf-8") as f:
            f.write(_dump_yaml(red_record))
        verdicts = [r["verdict"] for r in results]
        if any(v == "NO_RED_ALREADY_GREEN" for v in verdicts):
            return {"status": "NO_RED_ALREADY_GREEN", "change_id": change_id, "verdicts": verdicts,
                    "diagnostics": "requirement may already be satisfied / test too weak / spec mismatch"}
        if any(v != "VALID_RED" for v in verdicts):
            routes = {v: [] for v in set(verdicts)}
            for r in results:
                routes[r["verdict"]].append(r["test_id"])
            return {"status": "RED_INVALID", "change_id": change_id, "routes": routes}
        lock_files = []
        for tf in plan.get("test_files", []):
            p = os.path.join(target, tf["dest"])
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    lock_files.append({"path": tf["dest"], "hash": hashlib.sha256(f.read()).hexdigest()})
        protected = {}
        for prel in ("spec.yaml", "evidence.yaml"):
            pp = os.path.join(cdir, prel)
            if os.path.isfile(pp):
                with open(pp, "rb") as fh:
                    protected[prel] = hashlib.sha256(fh.read()).hexdigest()
        for prel in (".aeh/profile.yaml", ".aeh/effective-workflow.yaml"):
            pp = os.path.join(target, prel)
            if os.path.isfile(pp):
                with open(pp, "rb") as fh:
                    protected[prel] = hashlib.sha256(fh.read()).hexdigest()
        lock = {"contract": "test-lock", "version": 1, "change_id": change_id,
                "files": lock_files, "protected": protected, "repository": {"base_commit": base_commit, "dirty": None},
                "locked_at": datetime.now(timezone.utc).isoformat()}
        schema_lock = _load_yaml(os.path.join(ae_root, "schemas", "test-lock.schema.json"))
        jsonschema.validate(lock, schema_lock)
        with open(os.path.join(cdir, "test-lock.yaml"), "w", encoding="utf-8") as f:
            f.write(_dump_yaml(lock))
        change = ch.load_change(target, change_id)
        change["gates"] = dict(change.get("gates") or {})
        change["gates"]["red"] = "PASS"
        ch.save_change(target, change)
        tr1 = ch.change_transition(target, change_id, "LOCK_TEST", condition="VALID_RED")
        if tr1["status"] != "TRANSITION_OK":
            return {"status": "RED_COMPLETE_BUT_TRANSITION_FAILED", "change_id": change_id, "transition": tr1}
        # LOCK_TEST is the last Controller step before the coding agent writes
        # production code. Seal machine truth here so GREEN can detect any
        # agent-side .aeh additions or rewrites made during implementation.
        omod.record_checkpoint(target, change_id)
        return {"status": "RED_COMPLETE", "change_id": change_id, "verdicts": verdicts,
                "state": "LOCK_TEST", "gate": "PASS"}
    except (RedError, omod.OwnershipError, ch.ChangeError, jsonschema.ValidationError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "RED_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}
