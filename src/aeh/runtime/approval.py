# AEH TRUSTED HUMAN APPROVAL PATH (Phase 13)
# 人工批准的唯一写入路径：aeh change approve CLI -> record_approval。
# AEH 是 Validator 不是 Coding Agent；Runtime 模块永远不写 APPROVED。
# 诚实人工证词：actor.type 恒为 human，actor.id 为证词人身份；无签名即无批准。
import os
import yaml
import jsonschema
from datetime import datetime, timedelta, timezone

from .. import paths as aeh_paths
from ..doctor import doctor as doc
from . import change as ch
from . import ownership as omod


class ApprovalError(ValueError):
    pass


# SPEC_REVIEW/RED_GATE/VERIFY_MANUAL/MERGE_GATE 来自 core/gates.yaml
# human_approval_gates（P-17）；
# 取值域与 core 严格一致（contract test 冻结该不变量）。
ALLOWED_GATES = ("SPEC_REVIEW", "RED_GATE", "VERIFY_MANUAL", "MERGE_GATE")
DECISION_STATUSES = ("APPROVED", "REJECTED", "REVOKED")
MAX_TTL_SECONDS = 31 * 24 * 60 * 60


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=True, allow_unicode=True)


def _now_utc(now=None):
    value = now or datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ApprovalError("BLOCKED_BAD_APPROVAL_TIME: timezone-aware datetime required")
    return value.astimezone(timezone.utc)


def _parse_datetime(value):
    if not isinstance(value, str) or not value:
        raise ApprovalError("BLOCKED_BAD_APPROVAL_TIME: missing timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ApprovalError("BLOCKED_BAD_APPROVAL_TIME: timezone required")
    return parsed.astimezone(timezone.utc)


def assess_approval(entry, now=None):
    """Return effective state and compatibility warnings for one approval."""
    if not entry:
        return "MISSING", []
    status = entry.get("status")
    if status != "APPROVED":
        return status or "INVALID", []
    expires_at = entry.get("expires_at")
    if not expires_at:
        return "APPROVED", [entry.get("gate", "approval") + " approval has no expiry"]
    try:
        expires = _parse_datetime(expires_at)
    except (ApprovalError, ValueError):
        return "INVALID", []
    if _now_utc(now) >= expires:
        return "EXPIRED", []
    return "APPROVED", []


def load_approvals(target, change_id):
    p = os.path.join(ch._change_dir(target, change_id), "approvals.yaml")
    if not os.path.isfile(p):
        return {}
    doc = _load_yaml(p)
    out = {}
    for e in doc.get("approvals", []):
        out[e["gate"]] = e
    return out


def record_approval(target, change_id, gate, status, actor_id, evidence_ref=None,
                    ttl_seconds=None, ae_root=None, now=None):
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        if gate not in ALLOWED_GATES:
            return {"status": "BLOCKED_UNKNOWN_GATE", "change_id": change_id, "gate": gate}
        if status not in DECISION_STATUSES:
            return {"status": "BLOCKED_BAD_STATUS", "change_id": change_id, "status_given": status}
        if not actor_id or not isinstance(actor_id, str) or not actor_id.strip():
            return {"status": "BLOCKED_MISSING_ACTOR", "change_id": change_id,
                    "error": "trusted human approval requires actor identity (honest attestation)"}
        if ttl_seconds is not None and status != "APPROVED":
            return {"status": "BLOCKED_TTL_NOT_ALLOWED", "change_id": change_id,
                    "error": "ttl_seconds is valid only for APPROVED"}
        if ttl_seconds is not None and (
                isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or
                ttl_seconds < 1 or ttl_seconds > MAX_TTL_SECONDS):
            return {"status": "BLOCKED_BAD_TTL", "change_id": change_id,
                    "error": "ttl_seconds must be between 1 and %d" % MAX_TTL_SECONDS}
        decided_at = _now_utc(now)
        d = doc.run_doctor(target, ae_root)
        if d["overall"] == "BLOCKED":
            return {"status": "BLOCKED_DOCTOR", "change_id": change_id,
                    "blocking": [c["check_id"] for c in d["checks"] if c["status"] == "BLOCKED"]}
        change = ch.load_change(target, change_id)
        # RED/LOCK_TEST establishes the Controller checkpoint. Later approvals
        # may only extend an intact state and must advance the checkpoint.
        if omod.checkpoint_exists(target, change_id):
            omod.assert_checkpoint(target, change_id)
            omod.ensure_state_available(target, change_id)
        cdir = ch._change_dir(target, change_id)
        docp = os.path.join(cdir, "approvals.yaml")
        if os.path.isfile(docp):
            body = _load_yaml(docp)
            others = [e for e in body.get("approvals", []) if e.get("gate") != gate]
            existing = next((e for e in body.get("approvals", []) if e.get("gate") == gate), None)
        else:
            body = {}
            others = []
            existing = None
        if status == "REVOKED":
            if not existing or existing.get("status") != "APPROVED":
                return {"status": "BLOCKED_APPROVAL_NOT_REVOCABLE", "change_id": change_id,
                        "gate": gate}
            entry = dict(existing)
            entry["status"] = "REVOKED"
            entry["revoked_at"] = decided_at.isoformat()
            entry["revoked_by"] = {"type": "human", "id": actor_id.strip()}
            if evidence_ref:
                entry["revocation_evidence_ref"] = evidence_ref
            result_status = "APPROVAL_REVOKED"
        else:
            entry = {"gate": gate, "status": status,
                     "actor": {"type": "human", "id": actor_id.strip()},
                     "decided_at": decided_at.isoformat()}
            if status == "APPROVED" and ttl_seconds is not None:
                entry["expires_at"] = (decided_at + timedelta(seconds=ttl_seconds)).isoformat()
            if evidence_ref:
                entry["evidence_ref"] = evidence_ref
            result_status = "APPROVAL_RECORDED"
        body["approvals"] = others + [entry]
        schema = _load_yaml(os.path.join(ae_root, "schemas", "approvals.schema.json"))
        jsonschema.validate(body, schema)
        with open(docp, "w", encoding="utf-8") as f:
            f.write(_dump_yaml(body))
        if omod.checkpoint_exists(target, change_id):
            omod.record_checkpoint(target, change_id)
        return {"status": result_status, "change_id": change_id, "gate": gate,
                "decision": status, "actor_id": actor_id.strip()}
    except (ApprovalError, omod.OwnershipError, ch.ChangeError, jsonschema.ValidationError, FileNotFoundError) as e:
        code = str(e).split(":")[0] if str(e).startswith("BLOCKED") else "APPROVAL_FAILED"
        return {"status": code, "change_id": change_id, "error": str(e)}
