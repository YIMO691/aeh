"""Concise Agent-facing decision layer over existing AEH Change truth.

This module advises; it does not transition a Change, execute implementation,
or create approvals. Human Gates remain governed by approvals.yaml.
"""
import os
from datetime import datetime, timezone

import jsonschema
import yaml

from .. import paths as aeh_paths
from . import approval
from . import change as ch


OUTCOMES = ("CONTINUE", "WAITING_FOR_AUTHORITY", "BLOCKED", "COMPLETE")
TERMINAL_PHASES = {"DONE", "ARCHIVE", "DISCARD"}
BLOCKED_PHASES = {"BLOCKED_ENVIRONMENT", "INVESTIGATE", "TEST_SETUP", "SPEC_REPAIR", "TEST_REPAIR"}
HUMAN_PHASES = {
    "HUMAN_SPEC_APPROVAL": "SPEC_REVIEW",
    "HUMAN_CI_RED_GATE": "RED_GATE",
    "HUMAN_MANUAL_VERIFICATION": "VERIFY_MANUAL",
    "HUMAN_MERGE_APPROVAL": "MERGE_GATE",
}
PHASE_ACTIONS = {
    "CLASSIFY": ("classify_change", "modify_change"),
    "IMPLEMENT": ("implement", "modify_source"),
    "BASIC_VERIFY": ("run_basic_verification", "run_tests"),
    "DONE": ("finish_change", "modify_change"),
    "TARGETED_GROUND": ("ground_change", "read_repository"),
    "BUG_CONTRACT": ("compile_bug_contract", "modify_change"),
    "REGRESSION_TEST": ("design_regression_test", "modify_tests"),
    "GROUND": ("ground_change", "read_repository"),
    "SPEC": ("compile_spec", "modify_change"),
    "DESIGN": ("prepare_design", "modify_change"),
    "TEST_DESIGN": ("design_tests", "modify_tests"),
    "RED": ("run_red", "run_tests"),
    "VALIDATE_RED": ("validate_red", "run_tests"),
    "LOCK_TEST": ("lock_tests", "modify_change"),
    "GREEN": ("make_tests_green", "modify_source"),
    "REFACTOR": ("refactor_with_locked_tests", "modify_source"),
    "INTEGRATION": ("run_integration_verification", "run_tests"),
    "RUNTIME_PLATFORM_VERIFY": ("run_platform_verification", "run_tests"),
    "REGRESSION": ("run_regression", "run_tests"),
    "VERIFY": ("verify_traceability", "run_tests"),
    "REVIEW": ("review_change", "read_repository"),
    "DRIFT_CHECK": ("check_drift", "read_repository"),
    "ARCHIVE": ("archive_change", "modify_change"),
    "EXPERIMENT": ("run_experiment", "read_repository"),
    "EVIDENCE": ("collect_experiment_evidence", "read_repository"),
    "DECISION": ("decide_experiment", "modify_change"),
}


def _load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _load_authority(path, change_id, ae_root):
    if not path:
        return None, None
    if not os.path.isfile(path):
        return None, "authority envelope not found"
    value = _load_yaml(path)
    schema = _load_yaml(os.path.join(ae_root, "schemas", "authority-envelope.schema.json"))
    try:
        jsonschema.validate(value, schema)
    except jsonschema.ValidationError as exc:
        return None, "invalid authority envelope: " + exc.message
    if value["change_id"] != change_id:
        return None, "authority envelope is bound to a different Change"
    return value, None


def _recorded_approval(target, change_id, gate, now=None):
    entry = approval.load_approvals(target, change_id).get(gate)
    if not entry or entry.get("status") != "APPROVED":
        return False
    expires_at = entry.get("expires_at")
    if not expires_at:
        return True
    try:
        expires = approval._parse_datetime(expires_at)
        observed = approval._now_utc(now or datetime.now(timezone.utc))
    except (ValueError, approval.ApprovalError):
        return False
    return observed < expires


def _human_gate_for(change, current):
    phases = list(change.get("workflow", {}).get("phases", []))
    if current in HUMAN_PHASES:
        return HUMAN_PHASES[current], current
    if current in phases:
        position = phases.index(current)
        if position + 1 < len(phases):
            following = phases[position + 1]
            if following in HUMAN_PHASES:
                return HUMAN_PHASES[following], following
    return None, None


def _next_phase(change, current):
    phases = list(change.get("workflow", {}).get("phases", []))
    if current not in phases:
        return None
    position = phases.index(current)
    return phases[position + 1] if position + 1 < len(phases) else None


def continue_change(target, change_id, authority_path=None, ae_root=None, now=None):
    """Return one bounded next-action decision without mutating Change truth."""
    ae_root = ae_root or aeh_paths.ae_root()
    try:
        change = ch.load_change(target, change_id)
        current = change.get("state", {}).get("current")
        base = {
            "change_id": change_id,
            "phase": current,
            "workflow_level": change.get("workflow", {}).get("level"),
        }
        if current in TERMINAL_PHASES:
            return {**base, "status": "COMPLETE", "next_action": None}
        if current in BLOCKED_PHASES:
            return {
                **base,
                "status": "BLOCKED",
                "reason": "change requires repair or investigation",
                "next_action": {"id": "resolve_" + current.lower(), "capability": None},
            }

        gate, gate_phase = _human_gate_for(change, current)
        if gate and not _recorded_approval(target, change_id, gate, now=now):
            return {
                **base,
                "status": "WAITING_FOR_AUTHORITY",
                "required_gate": gate,
                "next_action": {"id": "obtain_" + gate.lower(), "phase": gate_phase,
                                "capability": None},
                "reason": "human Gate cannot be satisfied by an authority envelope",
            }

        authority, authority_error = _load_authority(authority_path, change_id, ae_root)
        if authority_error:
            return {**base, "status": "BLOCKED", "reason": authority_error,
                    "next_action": None}

        if gate:
            action, capability = "advance_after_" + gate.lower(), "modify_change"
        else:
            next_phase = _next_phase(change, current)
            action, capability = PHASE_ACTIONS.get(
                next_phase, ("inspect_current_phase", "read_repository"))
        next_action = {"id": action, "capability": capability}
        if not gate and next_phase is not None:
            next_action["phase"] = next_phase
        if authority is None or capability not in set(authority.get("allow", [])):
            return {
                **base,
                "status": "WAITING_FOR_AUTHORITY",
                "missing_capability": capability,
                "next_action": next_action,
                "reason": "task authority does not include the next action",
            }
        report = {**base, "status": "CONTINUE", "next_action": next_action}
        if gate:
            report["recorded_gate"] = gate
            report["final_credential_verification_required"] = True
        return report
    except (ch.ChangeError, OSError, ValueError) as exc:
        return {"change_id": change_id, "phase": None, "workflow_level": None,
                "status": "BLOCKED", "reason": str(exc), "next_action": None}
