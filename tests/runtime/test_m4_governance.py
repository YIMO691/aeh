"""M4 governance: manual verification gate and approval lifecycle."""
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.runtime import approval as amod
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr
from aeh.runtime import specification as sp
from aeh.runtime import test_design as td
from aeh.runtime import verify as vmod
from tests.runtime.test_verify import (
    NEUTRAL_REPO,
    TDD_REPO,
    TDD_SRC,
    make_target,
    plan_body,
    reqs_body,
    signed_approval,
    TEST_KEY_ID,
    to_green,
    write_yaml,
)


UTC = timezone.utc


def approval_doc(target, change_id):
    path = os.path.join(target, ".aeh", "changes", change_id, "approvals.yaml")
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class TestM4ApprovalLifecycle(unittest.TestCase):
    def test_ttl_approval_expires_deterministically(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        decided = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
        report = signed_approval(
            target, cid, "MERGE_GATE", "APPROVED", "owner",
            ttl_seconds=60, now=decided,
        )
        self.assertEqual(report["status"], "APPROVAL_RECORDED", report)
        entry = approval_doc(target, cid)["approvals"][0]
        self.assertEqual(entry["expires_at"], (decided + timedelta(seconds=60)).isoformat())
        state, warnings = amod.assess_approval(
            entry, now=decided + timedelta(seconds=61), target=target,
            change_id=cid, require_credential=True,
        )
        self.assertEqual(state, "EXPIRED")
        self.assertEqual(warnings, [])

    def test_legacy_approval_without_ttl_is_valid_with_warning(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        report = signed_approval(
            target, cid, "MERGE_GATE", "APPROVED", "owner"
        )
        self.assertEqual(report["status"], "APPROVAL_RECORDED", report)
        entry = approval_doc(target, cid)["approvals"][0]
        state, warnings = amod.assess_approval(
            entry, target=target, change_id=cid, require_credential=True)
        self.assertEqual(state, "APPROVED")
        self.assertTrue(any("no expiry" in warning for warning in warnings), warnings)

    def test_revocation_preserves_original_attestation(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        decided = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
        approved = signed_approval(
            target, cid, "MERGE_GATE", "APPROVED", "owner",
            ttl_seconds=3600, now=decided,
        )
        self.assertEqual(approved["status"], "APPROVAL_RECORDED", approved)
        revoked = signed_approval(
            target, cid, "MERGE_GATE", "REVOKED", "security-reviewer",
            evidence_ref="INC-001", now=decided + timedelta(seconds=30),
        )
        self.assertEqual(revoked["status"], "APPROVAL_REVOKED", revoked)
        entry = approval_doc(target, cid)["approvals"][0]
        self.assertEqual(entry["status"], "REVOKED")
        self.assertEqual(entry["actor"]["id"], "owner")
        self.assertEqual(entry["decided_at"], decided.isoformat())
        self.assertEqual(entry["revoked_by"]["id"], "security-reviewer")
        self.assertEqual(entry["revocation_evidence_ref"], "INC-001")
        self.assertEqual(amod.assess_approval(
            entry, target=target, change_id=cid,
            require_credential=True)[0], "REVOKED")

    def test_revoke_requires_existing_approved_record(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        report = signed_approval(
            target, cid, "MERGE_GATE", "REVOKED", "owner"
        )
        self.assertEqual(report["status"], "BLOCKED_APPROVAL_NOT_REVOCABLE")

    def test_ttl_rejected_for_non_approval_and_out_of_range(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        self.assertEqual(
            signed_approval(
                target, cid, "MERGE_GATE", "REJECTED", "owner", ttl_seconds=60
            )["status"],
            "BLOCKED_TTL_NOT_ALLOWED",
        )
        self.assertEqual(
            signed_approval(
                target, cid, "MERGE_GATE", "APPROVED", "owner", ttl_seconds=0
            )["status"],
            "BLOCKED_BAD_TTL",
        )


class TestM4ManualVerification(unittest.TestCase):
    def manual_change(self, **kwargs):
        target = make_target(NEUTRAL_REPO)
        verification = [{
            "id": "MANUAL-001",
            "type": "manual",
            "verifies": ["AC-001-01"],
        }]
        verification.extend(kwargs.pop("extra_verification", []))
        cid = to_green(target, verification=verification, **kwargs)
        return target, cid

    def test_manual_verification_waits_for_dedicated_gate(self):
        target, cid = self.manual_change()
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_WAITING_MANUAL", report)
        self.assertEqual(report["approval_state"], "MISSING")

    def test_manual_verification_approval_is_explicit_not_automated(self):
        target, cid = self.manual_change()
        self.assertEqual(vmod.change_verify(target, cid)["status"], "BLOCKED_WAITING_MANUAL")
        approved = signed_approval(
            target, cid, "VERIFY_MANUAL", "APPROVED", "reviewer", ttl_seconds=3600
        )
        self.assertEqual(approved["status"], "APPROVAL_RECORDED", approved)
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "VERIFY_COMPLETE", report)
        path = os.path.join(target, ".aeh", "changes", cid, "verification.yaml")
        with open(path, "r", encoding="utf-8") as stream:
            body = yaml.safe_load(stream)
        manual = [item for item in body["results"] if item.get("type") == "manual"][0]
        self.assertEqual(manual["status"], "pass")
        self.assertEqual(manual["verdict"], "approved")
        self.assertEqual(manual["method"], "manual_runtime")

    def test_manual_legacy_no_expiry_surfaces_warning(self):
        target, cid = self.manual_change()
        signed_approval(target, cid, "VERIFY_MANUAL", "APPROVED", "reviewer")
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "VERIFY_COMPLETE", report)
        self.assertEqual(report["overall"], "READY_WITH_WARNINGS")
        path = os.path.join(target, ".aeh", "changes", cid, "verification.yaml")
        with open(path, "r", encoding="utf-8") as stream:
            body = yaml.safe_load(stream)
        self.assertTrue(any("no expiry" in warning for warning in body["warnings"]))

    def test_rejected_manual_verification_is_distinct(self):
        target, cid = self.manual_change()
        signed_approval(target, cid, "VERIFY_MANUAL", "REJECTED", "reviewer")
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_MANUAL_VERIFICATION_REJECTED", report)

    def test_revoked_manual_verification_fails_closed(self):
        target, cid = self.manual_change()
        signed_approval(target, cid, "VERIFY_MANUAL", "APPROVED", "reviewer")
        signed_approval(target, cid, "VERIFY_MANUAL", "REVOKED", "owner")
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_WAITING_MANUAL", report)
        self.assertEqual(report["approval_state"], "REVOKED")

    def test_expired_manual_verification_fails_closed(self):
        target, cid = self.manual_change()
        old = datetime(2020, 1, 1, tzinfo=UTC)
        signed_approval(
            target, cid, "VERIFY_MANUAL", "APPROVED", "reviewer",
            ttl_seconds=1, now=old,
        )
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_WAITING_MANUAL", report)
        self.assertEqual(report["approval_state"], "EXPIRED")

    def test_expired_critical_merge_approval_fails_closed(self):
        target = make_target(TDD_REPO)
        cid = to_green(
            target, title="修复奖励领取逻辑", neutral=False,
            verification=[{
                "id": "INTEG-001", "type": "integration",
                "verifies": ["AC-001-01"], "command": "python tests/test_claim.py",
            }],
        )
        old = datetime(2020, 1, 1, tzinfo=UTC)
        signed_approval(
            target, cid, "MERGE_GATE", "APPROVED", "owner",
            ttl_seconds=1, now=old,
        )
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_HUMAN_APPROVAL_EXPIRED", report)
        self.assertEqual(report["approval_state"], "EXPIRED")

    def test_technical_failure_precedes_manual_approval(self):
        target, cid = self.manual_change(extra_verification=[{
            "id": "BROKEN-001",
            "type": "integration",
            "verifies": ["AC-001-01"],
            "command": "python tests/does_not_exist_verify.py",
        }])
        signed_approval(target, cid, "VERIFY_MANUAL", "APPROVED", "reviewer")
        report = vmod.change_verify(target, cid)
        self.assertEqual(report["status"], "BLOCKED_VERIFICATION_FAILED", report)


class TestM4CriticalPlanGate(unittest.TestCase):
    def test_critical_plan_rejected_at_test_design(self):
        target = make_target(TDD_REPO)
        tmp = tempfile.mkdtemp(prefix="aeh-m4-critical-")
        created = ch.change_new(target, "修复奖励领取逻辑", suggested_level="STANDARD")
        self.assertEqual(created["status"], "CHANGE_CREATED", created)
        cid = created["change_id"]
        self.assertEqual(gr.change_ground(target, cid)["status"], "GROUNDING_COMPLETE")
        spec = sp.build_spec(
            target, cid,
            reqs_path=write_yaml(tmp, "reqs.yaml", reqs_body(neutral=False)),
        )
        self.assertEqual(spec["status"], "SPEC_COMPLETE", spec)
        report = td.change_test_design(
            target, cid,
            write_yaml(tmp, "plan.yaml", plan_body(neutral=False)),
            test_src=TDD_SRC,
        )
        self.assertEqual(report["status"], "BLOCKED_VERIFICATION_PLAN_INSUFFICIENT", report)
        self.assertFalse(os.path.exists(os.path.join(
            target, ".aeh", "changes", cid, "test-plan.yaml"
        )))
        self.assertFalse(os.path.exists(os.path.join(target, "tests", "test_claim.py")))


class TestM4ApprovalCLI(unittest.TestCase):
    def test_cli_accepts_ttl_and_revocation(self):
        target = make_target(NEUTRAL_REPO)
        cid = to_green(target)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src")
        approve = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "change", "approve", cid,
             "--gate", "MERGE_GATE", "--status", "APPROVED", "--actor", "owner",
             "--key-id", TEST_KEY_ID,
             "--ttl-seconds", "600", "--workdir", target],
            capture_output=True, text=True, env=env, cwd=ROOT,
        )
        self.assertEqual(approve.returncode, 0, approve.stdout + approve.stderr)
        self.assertEqual(json.loads(approve.stdout)["status"], "APPROVAL_RECORDED")
        revoke = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "change", "approve", cid,
             "--gate", "MERGE_GATE", "--status", "REVOKED", "--actor", "owner",
             "--key-id", TEST_KEY_ID,
             "--workdir", target],
            capture_output=True, text=True, env=env, cwd=ROOT,
        )
        self.assertEqual(revoke.returncode, 0, revoke.stdout + revoke.stderr)
        self.assertEqual(json.loads(revoke.stdout)["status"], "APPROVAL_REVOKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
