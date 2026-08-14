# AEH TRUSTED HUMAN APPROVAL PATH (Phase 13)
# 人工批准的唯一写入路径：aeh change approve CLI -> record_approval。
# AEH 是 Validator 不是 Coding Agent；Runtime 模块永远不写 APPROVED。
# 诚实人工证词：actor.type 恒为 human，actor.id 为证词人身份；无签名即无批准。
import os
import yaml
import jsonschema
from datetime import datetime, timezone

from ..doctor import doctor as doc
from . import change as ch


class ApprovalError(ValueError):
    pass


# SPEC_REVIEW/RED_GATE/MERGE_GATE 来自 core/gates.yaml human_approval_gates（P-17）；
# 取值域与 core 严格一致（contract test 冻结该不变量）。
ALLOWED_GATES = ("SPEC_REVIEW", "RED_GATE", "MERGE_GATE")
APPROVED_STATUSES = ("APPROVED", "REJECTED")


def _default_root():
    # src/aeh/runtime/approval.py -> 4 层到项目根
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def load_approvals(target, change_id):
    p = os.path.join(ch._change_dir(target, change_id), "approvals.yaml")
    if not os.path.isfile(p):
        return {}
    doc = _load_yaml(p)
    out = {}
    for e in doc.get("approvals", []):
        out[e["gate"]] = e
    return out


def record_approval(target, change_id, gate, status, actor_id, evidence_ref=None, ae_root=None):
    ae_root = ae_root or _default_root()
    try:
        if gate not in ALLOWED_GATES:
            return {"status": "BLOCKED_UNKNOWN_GATE", "change_id": change_id, "gate": gate}
        if status not in APPROVED_STATUSES:
            return {"status": "BLOCKED_BAD_STATUS", "change_id": change_id, "status_given": status}
        if not actor_id or not isinstance(actor_id, str) or not actor_id.strip():
            return {"status": "BLOCKED_MISSING_ACTOR", "change_id": change_id,
                    "error": "trusted human approval requires actor identity (honest attestation)"}
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        change = ch.load_change(target, change_id)
        cdir = ch._change_dir(target, change_id)
        entry = {"gate": gate, "status": status,
                 "actor": {"type": "human", "id": actor_id.strip()},
                 "decided_at": datetime.now(timezone.utc).isoformat()}
        if evidence_ref:
            entry["evidence_ref"] = evidence_ref
        docp = os.path.join(cdir, "approvals.yaml")
        if os.path.isfile(docp):
            body = _load_yaml(docp)
            others = [e for e in body.get("approvals", []) if e.get("gate") != gate]
        else:
            body = {}
            others = []
        body["approvals"] = others + [entry]
        schema = _load_yaml(os.path.join(ae_root, "schemas", "approvals.schema.json"))
        jsonschema.validate(body, schema)
        with open(docp, "w", encoding="utf-8") as f:
            f.write(_dump_yaml(body))
        return {"status": "APPROVAL_RECORDED", "change_id": change_id, "gate": gate,
                "decision": status, "actor_id": entry["actor"]["id"]}
    except (ApprovalError, ch.ChangeError, jsonschema.ValidationError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "APPROVAL_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}