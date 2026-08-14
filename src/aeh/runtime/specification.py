"""AEH Specification Runtime（Phase 10）

把已过 Grounding Gate 的 Change，从 Repository Evidence + 用户目标编译成机器可验证的 spec.yaml：
稳定 REQ-*/AC-*、Evidence 到 Requirement 到 AC 可追溯、CURRENT/DESIRED/CONSTRAINT 语义分离、
SPEC Gate PASS 才允许进入 TEST_DESIGN。本阶段不实现 Test Design / RED / GREEN。
"""
import json
import os
from datetime import datetime, timezone

import jsonschema
import yaml

from ..doctor import doctor as doc
from . import change as ch
from . import grounding as gr


class SpecError(ValueError):
    pass


def _default_root():
    # src/aeh/runtime/specification.py -> 4 层到项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def load_reqs(path):
    if not path or not os.path.isfile(path):
        return {}
    return _load_yaml(path) or {}


def _stable_key(kind, source_type, behavior):
    return json.dumps([kind, source_type, behavior], sort_keys=True, ensure_ascii=False)


def _existing_spec(target, change_id):
    p = os.path.join(ch._change_dir(target, change_id), "spec.yaml")
    if not os.path.isfile(p):
        return None
    return _load_yaml(p)


def compile_spec_requirements(existing, user_reqs):
    by_key = {}
    next_req = 1
    if existing:
        for r in existing.get("requirements", []):
            k = _stable_key(r.get("kind", "DESIRED"), r.get("source", {}).get("type", "USER_REQUIREMENT"), r["behavior"])
            by_key[k] = r
            n = int(r["id"].split("-")[1])
            next_req = max(next_req, n + 1)
    rows = []
    for kind, source_type, entries in (
        ("CURRENT", "EVIDENCE_DERIVED", user_reqs.get("current_facts", [])),
        ("DESIRED", "USER_REQUIREMENT", user_reqs.get("requirements", [])),
        ("CONSTRAINT", "POLICY_CONSTRAINT", user_reqs.get("constraints", [])),
    ):
        for e in entries:
            rows.append((kind, source_type, e))
    rows.sort(key=lambda r: _stable_key(r[0], r[1], r[2].get("behavior", "")))
    out = []
    for kind, source_type, e in rows:
        behavior = e.get("behavior", "")
        k = _stable_key(kind, source_type, behavior)
        if k in by_key:
            req = dict(by_key[k])
            ac_map = {a["statement"]: a["id"] for a in req.get("acceptance", [])}
            req.update({"behavior": behavior, "kind": kind,
                        "source": {"type": source_type, "refs": list(e.get("refs", []))}})
            if e.get("supported_by"):
                req["supported_by"] = list(e["supported_by"])
            req["acceptance"] = []
            for a in e.get("acceptance", []):
                stmt = a.get("statement", "")
                aid = ac_map.get(stmt) or ("AC-%03d-%02d" % (int(req["id"].split("-")[1]), len(ac_map) + 1))
                ac_map[stmt] = aid
                req["acceptance"].append({"id": aid, "type": a.get("type", "automated"), "statement": stmt})
            out.append(req)
        else:
            rid = "REQ-%03d" % next_req
            next_req += 1
            req = {"id": rid, "behavior": behavior, "kind": kind,
                   "source": {"type": source_type, "refs": list(e.get("refs", []))}}
            if e.get("supported_by"):
                req["supported_by"] = list(e["supported_by"])
            if e.get("failure_behavior"):
                req["failure_behavior"] = e["failure_behavior"]
            if e.get("scope_tags"):
                req["scope_tags"] = list(e["scope_tags"])
            if e.get("invariants"):
                req["invariants"] = list(e["invariants"])
            req["acceptance"] = []
            for i, a in enumerate(e.get("acceptance", [])):
                req["acceptance"].append({"id": "AC-%03d-%02d" % (next_req - 1, i + 1),
                                          "type": a.get("type", "automated"),
                                          "statement": a.get("statement", "")})
            out.append(req)
    return out

def validate_spec(requirements, evidence_ids, level, scope, unknowns):
    seen_req, seen_ac = set(), set()
    for r in requirements:
        if r["id"] in seen_req:
            return "SPEC_INVALID", ["duplicate REQ id: " + r["id"]]
        seen_req.add(r["id"])
        if not r.get("acceptance"):
            return "SPEC_INCOMPLETE", ["REQ " + r["id"] + " missing acceptance"]
        for a in r["acceptance"]:
            if a["id"] in seen_ac:
                return "SPEC_INVALID", ["duplicate AC id: " + a["id"]]
            seen_ac.add(a["id"])
        src_type = (r.get("source") or {}).get("type", "USER_REQUIREMENT")
        if src_type == "EVIDENCE_DERIVED":
            if not r.get("supported_by"):
                return "BLOCKED_UNSUPPORTED_REQUIREMENT", [r["id"]]
            missing = [ev for ev in r["supported_by"] if ev not in evidence_ids]
            if missing:
                return "BLOCKED_INVALID_EVIDENCE_REFERENCE", sorted(missing)
        if r.get("supported_by"):
            missing = [ev for ev in r["supported_by"] if ev not in evidence_ids]
            if missing:
                return "BLOCKED_INVALID_EVIDENCE_REFERENCE", sorted(missing)
        if scope and scope.get("out"):
            hits = [t for t in r.get("scope_tags", []) if t in scope["out"]]
            if hits:
                return "UNSCOPED_REQUIREMENT", [r["id"] + " tags=" + ",".join(hits)]
        if level == "CRITICAL":
            has_invariant_ac = any(a.get("type") == "invariant" for a in r["acceptance"])
            if not has_invariant_ac and not r.get("failure_behavior"):
                return "SPEC_INCOMPLETE", ["CRITICAL REQ " + r["id"] + " needs invariant AC or failure_behavior"]
    if level == "CRITICAL":
        critical_unknowns = [u for u in unknowns if u.get("critical")]
        if critical_unknowns:
            return "SPEC_INCOMPLETE", ["critical unknown: " + u["field"] for u in critical_unknowns]
    return None, []

def build_spec(target, change_id, reqs_path=None, ae_root=None):
    ae_root = ae_root or _default_root()
    try:
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        change = ch.load_change(target, change_id)
        if change["state"]["current"] not in ("GROUND", "SPEC"):
            return {"status": "BLOCKED_CHANGE_STATE", "change_id": change_id,
                    "state": change["state"]["current"]}
        if change.get("gates", {}).get("grounding") != "PASS":
            return {"status": "BLOCKED_GROUNDING_GATE", "change_id": change_id}
        ev_path = os.path.join(ch._change_dir(target, change_id), "evidence.yaml")
        if not os.path.isfile(ev_path):
            return {"status": "BLOCKED_GROUNDING_GATE", "change_id": change_id,
                    "error": "evidence.yaml missing"}
        index = _load_yaml(ev_path)
        schema_ev = _load_yaml(os.path.join(ae_root, "schemas", "evidence-index.schema.json"))
        jsonschema.validate(index, schema_ev)
        stale = gr.check_stale(target, change_id)["stale"]
        if stale:
            return {"status": "BLOCKED_STALE_EVIDENCE", "change_id": change_id, "stale": stale}
        evidence_ids = {e["id"] for e in index.get("evidence", [])}
        user_reqs = load_reqs(reqs_path)
        existing = _existing_spec(target, change_id)
        requirements = compile_spec_requirements(existing, user_reqs)
        if not requirements:
            return {"status": "SPEC_INCOMPLETE", "change_id": change_id,
                    "missing": ["requirements"], "gate": "PENDING"}
        level = change.get("workflow", {}).get("level")
        scope = user_reqs.get("scope")
        unknowns = list(user_reqs.get("unknowns", []))
        status, missing = validate_spec(requirements, evidence_ids, level, scope, unknowns)
        if status is not None:
            return {"status": status, "change_id": change_id, "missing": missing, "gate": "PENDING"}
        spec = {"requirements": requirements,
                "scope": scope if scope else None,
                "unknowns": unknowns if unknowns else None,
                "assumptions": user_reqs.get("assumptions") or None,
                "generated_at": datetime.now(timezone.utc).isoformat()}
        spec = {k: v for k, v in spec.items() if v is not None}
        schema = _load_yaml(os.path.join(ae_root, "schemas", "spec.schema.json"))
        jsonschema.validate(spec, schema)
        cdir = ch._change_dir(target, change_id)
        with open(os.path.join(cdir, "spec.yaml"), "w", encoding="utf-8") as f:
            f.write(_dump_yaml(spec))
        md_lines = ["# Spec", "", "machine truth in spec.yaml", ""]
        for r in requirements:
            md_lines.append("## " + r["id"] + " [" + r.get("kind", "?") + "] " + r["behavior"])
            for a in r.get("acceptance", []):
                md_lines.append("- " + a["id"] + " (" + a["type"] + ") " + a["statement"])
        with open(os.path.join(cdir, "spec.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
        change["gates"] = dict(change.get("gates") or {})
        change["gates"]["spec"] = "PASS"
        ch.save_change(target, change)
        if change["state"]["current"] == "GROUND":
            tr = ch.change_transition(target, change_id, "SPEC")
            if tr["status"] != "TRANSITION_OK":
                return {"status": "SPEC_COMPLETE_BUT_TRANSITION_FAILED", "change_id": change_id, "transition": tr}
        return {"status": "SPEC_COMPLETE", "change_id": change_id,
                "requirement_count": len(requirements), "gate": "PASS", "state": "SPEC"}
    except (SpecError, ch.ChangeError, jsonschema.ValidationError) as e:
        return {"status": "SPEC_FAILED", "change_id": change_id, "error": str(e)}
