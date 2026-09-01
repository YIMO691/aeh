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
from . import coordination as coord
from . import grounding as gr
from . import ownership as omod
from . import execution as xmod

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


def _portable_hashes(data):
    normalized = data.replace(b"\r\n", b"\n")
    return {
        hashlib.sha256(data).hexdigest(),
        hashlib.sha256(normalized).hexdigest(),
        hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest(),
    }


def _read_bytes(path):
    with open(path, "rb") as stream:
        return stream.read()


def _git_blob(target, relative):
    result = subprocess.run(
        ["git", "-C", target, "show", "HEAD:" + relative.replace(os.sep, "/")],
        capture_output=True, timeout=10, check=False)
    return result.stdout if result.returncode == 0 else None


def _validate_red_relock_context(target, change_id, plan, ae_root,
                                 red_bytes, lock_bytes, load_log):
    cdir = ch._change_dir(target, change_id)
    try:
        previous_red = yaml.safe_load(red_bytes.decode("utf-8"))
        lock = yaml.safe_load(lock_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError):
        return None
    jsonschema.validate(
        previous_red, _load_yaml(os.path.join(ae_root, "schemas", "red.schema.json")))
    jsonschema.validate(
        lock, _load_yaml(os.path.join(ae_root, "schemas", "test-lock.schema.json")))
    if previous_red.get("change_id") != change_id or lock.get("change_id") != change_id:
        return None
    required_ids = {item["id"] for item in plan.get("tests", []) if item.get("required", True)}
    records = previous_red.get("tests") or []
    if ({item.get("test_id") for item in records} != required_ids or
            any(item.get("verdict") != "VALID_RED" for item in records)):
        return None
    current_test_hash = _test_files_hash(target, plan)
    if any(item.get("test_files_hash") != current_test_hash for item in records):
        return None
    locked_files = lock.get("files") or []
    if {item.get("path") for item in locked_files} != {
            item["dest"] for item in plan.get("test_files", [])}:
        return None
    for item in locked_files:
        path = os.path.join(target, item["path"])
        if not os.path.isfile(path) or item.get("hash") not in _portable_hashes(_read_bytes(path)):
            return None
    saved_logs = {}
    for item in records:
        relative = str(item.get("output_ref", "")).replace("\\", "/")
        prefix = ".aeh/changes/" + change_id + "/evidence/"
        if not relative.startswith(prefix) or ".." in relative.split("/"):
            return None
        data = load_log(relative)
        if data is None:
            return None
        if item.get("output_hash") not in _portable_hashes(data):
            return None
        path = os.path.join(target, *relative.split("/"))
        saved_logs[path] = data
    protected = lock.get("protected") or {}
    evidence_changed = False
    for relative, expected in protected.items():
        path = relative if os.path.isabs(relative) else os.path.join(target, relative)
        if not os.path.isfile(path):
            path = os.path.join(cdir, relative)
        if not os.path.isfile(path):
            return None
        matches = expected in _portable_hashes(_read_bytes(path))
        if relative == "evidence.yaml":
            evidence_changed = not matches
        elif not matches:
            return None
    if not evidence_changed:
        return None
    return {"red_bytes": red_bytes, "lock": lock, "logs": saved_logs}


def _existing_red_relock_context(target, change_id, plan, ae_root):
    """Load a sealed or committed VALID_RED context eligible for a narrow relock."""
    cdir = ch._change_dir(target, change_id)
    red_path = os.path.join(cdir, "red.yaml")
    lock_path = os.path.join(cdir, "test-lock.yaml")
    if os.path.isfile(red_path) and os.path.isfile(lock_path):
        current = _validate_red_relock_context(
            target, change_id, plan, ae_root,
            _read_bytes(red_path), _read_bytes(lock_path),
            lambda relative: (
                _read_bytes(os.path.join(target, *relative.split("/")))
                if os.path.isfile(os.path.join(target, *relative.split("/"))) else None))
        if current is not None:
            return current
    red_relative = ".aeh/changes/" + change_id + "/red.yaml"
    lock_relative = ".aeh/changes/" + change_id + "/test-lock.yaml"
    committed_red = _git_blob(target, red_relative)
    committed_lock = _git_blob(target, lock_relative)
    if committed_red is None or committed_lock is None:
        return None
    return _validate_red_relock_context(
        target, change_id, plan, ae_root, committed_red, committed_lock,
        lambda relative: _git_blob(target, relative))


def _complete_context_relock(target, change_id, context, ae_root):
    """Refresh only the Controller-produced Grounding hash in a proven RED lock."""
    cdir = ch._change_dir(target, change_id)
    coord.atomic_write_bytes(os.path.join(cdir, "red.yaml"), context["red_bytes"])
    for path, content in context["logs"].items():
        coord.atomic_write_bytes(path, content)
    lock = dict(context["lock"])
    protected = dict(lock.get("protected") or {})
    protected["evidence.yaml"] = hashlib.sha256(
        _read_bytes(os.path.join(cdir, "evidence.yaml"))).hexdigest()
    lock["protected"] = protected
    lock["locked_at"] = datetime.now(timezone.utc).isoformat()
    jsonschema.validate(
        lock, _load_yaml(os.path.join(ae_root, "schemas", "test-lock.schema.json")))
    coord.atomic_write_text(os.path.join(cdir, "test-lock.yaml"), _dump_yaml(lock))
    change = ch.load_change(target, change_id)
    change["gates"] = dict(change.get("gates") or {})
    change["gates"]["red"] = "PASS"
    change["gates"]["lock_test"] = "PASS"
    ch.save_change(target, change)
    transition = ch.change_transition(target, change_id, "LOCK_TEST", condition="VALID_RED")
    if transition["status"] != "TRANSITION_OK":
        return {"status": "RED_RELOCK_TRANSITION_FAILED", "change_id": change_id,
                "transition": transition}
    omod.record_checkpoint(target, change_id)
    return {"status": "RED_CONTEXT_RELOCKED", "change_id": change_id,
            "verdicts": ["NO_RED_ALREADY_GREEN"], "state": "LOCK_TEST", "gate": "PASS"}


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

@coord.coordinated_change_mutator("CHANGE_RED")
def change_red(target, change_id, ae_root=None, allow_shell=False):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        omod.ensure_state_available(target, change_id)
        had_checkpoint = omod.checkpoint_exists(target, change_id)
        red_only_checkpoint_drift = False
        if had_checkpoint:
            try:
                omod.assert_checkpoint(target, change_id)
            except omod.OwnershipError as exc:
                if str(exc) != "BLOCKED_MACHINE_TRUTH_PROVENANCE: modified=red.yaml":
                    raise
                red_only_checkpoint_drift = True
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
        relock_context = (
            _existing_red_relock_context(target, change_id, plan, ae_root)
            if had_checkpoint else None)
        if red_only_checkpoint_drift:
            current_red = _load_yaml(os.path.join(ch._change_dir(target, change_id), "red.yaml"))
            current_verdicts = [item.get("verdict") for item in current_red.get("tests", [])]
            if (relock_context is None or not current_verdicts or
                    any(verdict != "NO_RED_ALREADY_GREEN" for verdict in current_verdicts)):
                raise omod.OwnershipError(
                    "BLOCKED_MACHINE_TRUTH_PROVENANCE: modified=red.yaml")
            # The external lease CAS already binds this exact late-replay result.
            # Adopt it only after a committed VALID_RED context has been proven.
            omod.record_checkpoint(target, change_id)
        if change["state"]["current"] == "TEST_DESIGN":
            tr0 = ch.change_transition(target, change_id, "RED")
            if tr0["status"] != "TRANSITION_OK":
                return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id, "transition": tr0}
            change = ch.load_change(target, change_id)
            if had_checkpoint:
                # The transition itself is a Controller-owned mutation. Advance
                # the repair checkpoint before executing repository test code.
                omod.record_checkpoint(target, change_id)
        before = _snapshot(target, os.path.join(".aeh", "changes", change_id))
        cdir = ch._change_dir(target, change_id)
        base_commit = _git_base(target)
        tests_hash = _test_files_hash(target, plan)
        results = []
        required = [t for t in plan["tests"] if t.get("required", True)]
        for t in required:
            execution = t.get("execution", {})
            cmd = execution.get("command") or t["command"]
            run_spec = {
                "command": execution.get("command") or (
                    None if execution.get("argv") is not None else t["command"]),
                "argv": execution.get("argv"),
                "cwd": execution.get("cwd"),
                "timeout_seconds": execution.get("timeout_seconds", 60),
                "shell": execution.get("shell", False),
                "env": execution.get("env"),
            }
            try:
                exit_code, output, _ = xmod.run_execution(
                    target, run_spec, allow_shell=allow_shell, ae_root=ae_root)
            except xmod.ExecutionPolicyError as exc:
                raise RedError(str(exc)) from exc
            verdict, actual = classify_red(exit_code, output, t)
            out_path = os.path.join(cdir, "evidence", "red-" + t["id"] + ".log")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            coord.atomic_write_text(out_path, output)
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
        coord.atomic_write_text(
            os.path.join(cdir, "red.yaml"), _dump_yaml(red_record))
        verdicts = [r["verdict"] for r in results]
        if any(v == "NO_RED_ALREADY_GREEN" for v in verdicts):
            if relock_context is not None and all(v == "NO_RED_ALREADY_GREEN" for v in verdicts):
                return _complete_context_relock(
                    target, change_id, relock_context, ae_root)
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
        coord.atomic_write_text(
            os.path.join(cdir, "test-lock.yaml"), _dump_yaml(lock))
        change = ch.load_change(target, change_id)
        change["gates"] = dict(change.get("gates") or {})
        change["gates"]["red"] = "PASS"
        change["gates"]["lock_test"] = "PASS"
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
