"""AEH Change Workspace + State Machine（Phase 8 Shell）

- change new：Runtime Preflight 前置；BLOCKED 不创建；READY_WITH_WARNINGS 记录 warnings。
- Change ID：确定性安全分配（已有 CHG 目录 max+1，禁止覆盖）。
- 每个 Change 独立 .aeh/changes/CHG-YYYY-NNNN/，无全局 current-change。
- Transition：读取 .aeh/runtime/core/states.yaml + gates.yaml（已安装快照）；
  只允许合法迁移；非法 → BLOCKED_ILLEGAL_STATE_TRANSITION；
  gate 未 PASS → BLOCKED_GATE_UNSATISFIED；runtime digest 失效 → 阻断。
- 本阶段不实现 Grounding/Spec/Test/RED/GREEN 自动执行；不伪造 evidence/spec/test 文件。
"""
import os
import re
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths
from ..doctor import doctor as doc
from . import classify as cls

CHG_RE = re.compile(r"^CHG-(\d{4})-(\d{4})$")


class ChangeError(ValueError):
    pass


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _change_dir(target, change_id):
    return os.path.join(target, ".aeh", "changes", change_id)


def allocate_change_id(target, now=None):
    root = os.path.join(target, ".aeh", "changes")
    os.makedirs(root, exist_ok=True)
    year = (now or datetime.now(timezone.utc)).year
    max_n = 0
    for name in os.listdir(root):
        m = CHG_RE.match(name)
        if m and int(m.group(1)) == year and os.path.isdir(os.path.join(root, name)):
            max_n = max(max_n, int(m.group(2)))
    n = max_n + 1
    while True:
        candidate = "CHG-%04d-%04d" % (year, n)
        if not os.path.exists(os.path.join(root, candidate)):
            return candidate
        n += 1


def _load_installed_contracts(target):
    states = _load_yaml(os.path.join(target, ".aeh", "runtime", "core", "states.yaml"))
    gates = _load_yaml(os.path.join(target, ".aeh", "runtime", "core", "gates.yaml"))
    return states, gates


def _workflow_for(target, level):
    ewf = _load_yaml(os.path.join(target, ".aeh", "effective-workflow.yaml"))
    lv = ewf.get("levels", {}).get(level)
    if not lv:
        raise ChangeError("workflow level missing in effective-workflow: " + level)
    return ewf, lv


def change_new(target, title, suggested_level=None, ae_root=None, now=None):
    try:
        d = doc.run_doctor(target, ae_root)
        pre = doc.runtime_preflight(d)
        if pre["verdict"] == "BLOCKED":
            return {"status": "BLOCKED_PREFLIGHT", "target": target,
                    "blocking_checks": [c["check_id"] for c in pre["blocking_checks"]]}
        warnings = [c["message"] for c in pre["warnings"]]
        hits = cls.detect_hits(title)
        classification = cls.classify(title, suggested_level=suggested_level, hits=hits)
        level = classification["level"]
        change_id = allocate_change_id(target, now)
        ewf, lv = _workflow_for(target, level)
        change = {
            "change_id": change_id,
            "title": title,
            "classification": classification,
            "state": {"current": "INTAKE", "previous": None},
            "gates": {"classification": "PASS"},
            "workflow": {"level": level, "phases": list(lv["phases"])},
            "preflight_warnings": warnings,
            "created_at": (now or datetime.now(timezone.utc)).isoformat(),
        }
        schema = _load_yaml(os.path.join(ae_root or aeh_paths.ae_root(), "schemas", "change.schema.json"))
        jsonschema.validate(change, schema)
        cdir = _change_dir(target, change_id)
        os.makedirs(cdir, exist_ok=False)
        with open(os.path.join(cdir, "change.yaml"), "w", encoding="utf-8") as f:
            f.write(_dump_yaml(change))
        return {"status": "CHANGE_CREATED", "target": target, "change_id": change_id,
                "classification": classification, "workflow_level": level,
                "preflight": {"verdict": pre["verdict"], "warnings": warnings}}
    except (ChangeError, cls.ClassifyError, jsonschema.ValidationError) as e:
        return {"status": "CHANGE_FAILED", "target": target, "error": str(e)}


def load_change(target, change_id):
    path = os.path.join(_change_dir(target, change_id), "change.yaml")
    if not os.path.isfile(path):
        raise ChangeError("change not found: " + change_id)
    return _load_yaml(path)


def save_change(target, change):
    cdir = _change_dir(target, change["change_id"])
    tmp = os.path.join(cdir, "change.yaml.aeh-tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(_dump_yaml(change))
    os.replace(tmp, os.path.join(cdir, "change.yaml"))


def _legal_transitions(states):
    return {(t["from"], t["to"]): t for t in states.get("transitions", [])}


def change_transition(target, change_id, to, condition=None, ae_root=None):
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        states, gates = _load_installed_contracts(target)
        change = load_change(target, change_id)
        current = change["state"]["current"]
        transitions = _legal_transitions(states)
        edge = transitions.get((current, to))
        if edge is None:
            return {"status": "BLOCKED_ILLEGAL_STATE_TRANSITION", "change_id": change_id,
                    "from": current, "to": to}
        if edge.get("condition") and edge["condition"] != condition:
            return {"status": "BLOCKED_CONDITION_REQUIRED", "change_id": change_id,
                    "from": current, "to": to, "required": edge["condition"]}
        gate = next((g for g in gates.get("gates", []) if g.get("phase") == to), None)
        if gate is not None:
            gate_status = change.get("gates", {}).get(gate["id"].lower())
            if gate_status != "PASS":
                return {"status": "BLOCKED_GATE_UNSATISFIED", "change_id": change_id,
                        "from": current, "to": to, "gate": gate["id"]}
        change["state"] = {"current": to, "previous": current}
        save_change(target, change)
        return {"status": "TRANSITION_OK", "change_id": change_id, "from": current, "to": to,
                "state": change["state"]}
    except (ChangeError, FileNotFoundError) as e:
        return {"status": "CHANGE_FAILED", "change_id": change_id, "error": str(e)}


def change_status(target, change_id, ae_root=None):
    change = load_change(target, change_id)
    phases = change.get("workflow", {}).get("phases", [])
    current = change["state"]["current"]
    idx = phases.index(current) if current in phases else -1
    rows = []
    for i, p in enumerate(phases):
        if i < idx:
            rows.append({"phase": p, "status": "PASS"})
        elif i == idx:
            rows.append({"phase": p, "status": "CURRENT"})
        elif i == idx + 1:
            rows.append({"phase": p, "status": "NEXT"})
        else:
            rows.append({"phase": p, "status": "LOCKED"})
    return {"change_id": change_id, "level": change.get("workflow", {}).get("level"),
            "classification": change.get("classification", {}).get("level", change.get("classification")),
            "state": change["state"], "gates": change.get("gates", {}), "phases": rows}


def change_repair(target, change_id, kind, ae_root=None):
    """Route GREEN into a frozen repair state without bypassing transition checks."""
    routes = {
        "ground": ("GROUND", "GROUNDING_STALE"),
        "test": ("TEST_REPAIR", "BLOCKED_TEST_CHANGED"),
        "spec": ("SPEC_REPAIR", "SPEC_CHANGED_IN_GREEN"),
    }
    if kind not in routes:
        return {"status": "CHANGE_FAILED", "change_id": change_id,
                "error": "unknown repair kind: " + str(kind)}
    destination, condition = routes[kind]
    return change_transition(target, change_id, destination, condition=condition, ae_root=ae_root)
