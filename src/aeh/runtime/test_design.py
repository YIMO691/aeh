"""AEH Test Design Runtime（Phase 11 前半）

把已过 SPEC Gate 的 REQ/AC 转成机器可追踪 Test Plan（test-plan.yaml），
验证 AC 覆盖、安装测试文件（只允许测试位置）、设置 TEST_DESIGN Gate。

边界：不得修改 production source/config/spec/profile/workflow。
"""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

import jsonschema
import yaml

from ..discovery import _resolve_within
from ..doctor import doctor as doc
from . import change as ch
from . import grounding as gr


class TestDesignError(ValueError):
    pass


def _default_root():
    # src/aeh/runtime/test_design.py -> 4 层到项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _snapshot(target, exclude_rel):
    out = {}
    for dp, _, fns in os.walk(target):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, target)
            if rel.startswith(exclude_rel):
                continue
            out[rel] = _sha256_file(p)
    return out


def _stable_test_key(t):
    return json.dumps([sorted(t.get("verifies", [])), t.get("intent", ""), t.get("kind", "")],
                      sort_keys=True, ensure_ascii=False)


def _existing_plan(target, change_id):
    p = os.path.join(ch._change_dir(target, change_id), "test-plan.yaml")
    if not os.path.isfile(p):
        return None
    return _load_yaml(p)


def validate_coverage(spec, plan, level):
    """返回 (status, missing)。自动 AC 必须有 Test；TEST.verifies 必须指向真实 AC；
    CRITICAL invariant AC 必须有 Test 或声明 non_automatable。"""
    ac_ids = set()
    automated = set()
    invariants = set()
    for r in spec.get("requirements", []):
        for a in r.get("acceptance", []):
            ac_ids.add(a["id"])
            if a.get("type") == "automated":
                automated.add(a["id"])
            if a.get("type") == "invariant":
                invariants.add(a["id"])
    verified = set()
    for t in plan.get("tests", []):
        for v in t.get("verifies", []):
            if v not in ac_ids:
                return "BLOCKED_INVALID_AC_REFERENCE", [v]
            verified.add(v)
    uncovered = automated - verified
    if uncovered:
        return "TEST_DESIGN_INCOMPLETE", sorted(uncovered)
    if level == "CRITICAL":
        declared_na = {n["ac_id"] for n in plan.get("non_automatable", [])}
        missing_invariant = (invariants - verified) - declared_na
        if missing_invariant:
            return "TEST_DESIGN_INCOMPLETE", ["critical invariant AC uncovered: " + x for x in sorted(missing_invariant)]
    return None, []


def change_test_design(target, change_id, plan_path, test_src=None, ae_root=None):
    ae_root = ae_root or _default_root()
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        change = ch.load_change(target, change_id)
        if change["state"]["current"] not in ("SPEC", "TEST_DESIGN", "RED", "LOCK_TEST"):
            return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                    "state": change["state"]["current"]}
        if change.get("gates", {}).get("spec") != "PASS":
            return {"status": "BLOCKED_SPEC_GATE", "change_id": change_id}
        stale = gr.check_stale(target, change_id)["stale"]
        if stale:
            return {"status": "BLOCKED_STALE_EVIDENCE", "change_id": change_id, "stale": stale}
        spec_path = os.path.join(ch._change_dir(target, change_id), "spec.yaml")
        if not os.path.isfile(spec_path):
            return {"status": "BLOCKED_SPEC_GATE", "change_id": change_id, "error": "spec.yaml missing"}
        spec = _load_yaml(spec_path)
        schema_spec = _load_yaml(os.path.join(ae_root, "schemas", "spec.schema.json"))
        jsonschema.validate(spec, schema_spec)
        plan = _load_yaml(plan_path)
        schema_plan = _load_yaml(os.path.join(ae_root, "schemas", "test-plan.schema.json"))
        jsonschema.validate(plan, schema_plan)
        existing = _existing_plan(target, change_id)
        if existing:
            by_key = {_stable_test_key(t): t for t in existing.get("tests", [])}
            next_id = max([int(t["id"].split("-")[1]) for t in existing["tests"]] + [0]) + 1
            for t in plan["tests"]:
                k = _stable_test_key(t)
                if k in by_key:
                    t["id"] = by_key[k]["id"]
                else:
                    t["id"] = "TEST-%03d" % next_id
                    next_id += 1
        level = change.get("workflow", {}).get("level")
        status, missing = validate_coverage(spec, plan, level)
        if status is not None:
            return {"status": status, "change_id": change_id, "missing": missing}
        # 安装测试文件：dest 必须落在测试目录/测试文件模式内（bootstrap/grounding.yaml 规则）
        gr_rules = _load_yaml(os.path.join(ae_root, "bootstrap", "grounding.yaml"))
        allowed_dirs = tuple(gr_rules["test_dirs"])
        allowed_patterns = tuple(gr_rules["test_file_patterns"])
        for tf in plan.get("test_files", []):
            dest = tf["dest"]
            rel = os.path.normpath(dest)
            from fnmatch import fnmatch
            in_test_dir = any(rel == d or rel.startswith(d + os.sep) for d in allowed_dirs)
            matches_pattern = any(fnmatch(os.path.basename(rel), p) for p in allowed_patterns)
            if not (in_test_dir or matches_pattern):
                return {"status": "BLOCKED_TEST_LOCATION", "change_id": change_id, "dest": dest}
            src = os.path.join(test_src, tf["src"]) if test_src else None
            if not src or not os.path.isfile(src):
                return {"status": "BLOCKED_TEST_LOCATION", "change_id": change_id,
                        "error": "test source missing: " + tf["src"]}
            target_dest = _resolve_within(target, rel)
            if target_dest is None:
                return {"status": "BLOCKED_TEST_LOCATION", "change_id": change_id, "dest": dest}
            os.makedirs(os.path.dirname(target_dest), exist_ok=True)
            shutil.copyfile(src, target_dest)
        plan["generated_at"] = datetime.now(timezone.utc).isoformat()
        cdir = ch._change_dir(target, change_id)
        with open(os.path.join(cdir, "test-plan.yaml"), "w", encoding="utf-8") as f:
            f.write(_dump_yaml(plan))
        change["gates"] = dict(change.get("gates") or {})
        change["gates"]["test_design"] = "PASS"
        ch.save_change(target, change)
        if change["state"]["current"] == "SPEC":
            tr = ch.change_transition(target, change_id, "TEST_DESIGN")
            if tr["status"] != "TRANSITION_OK":
                return {"status": "TEST_DESIGN_COMPLETE_BUT_TRANSITION_FAILED", "change_id": change_id,
                        "transition": tr}
        return {"status": "TEST_DESIGN_COMPLETE", "change_id": change_id,
                "test_count": len(plan["tests"]), "gate": "PASS", "state": "TEST_DESIGN"}
    except (TestDesignError, ch.ChangeError, jsonschema.ValidationError) as e:
        return {"status": "TEST_DESIGN_FAILED", "change_id": change_id, "error": str(e)}
