"""M5 threat-model regressions for execution and approval credentials."""
from datetime import datetime, timezone
import os
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.runtime import approval as amod
from aeh.runtime import credentials as credmod
from aeh.runtime import execution as xmod


def make_key(target, key_id="reviewer", value=None):
    value = value or b"aeh-m5-credential-material-for-tests-0001"
    directory = os.path.join(target, ".aeh", "private", "approval-keys")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, key_id + ".key")
    with open(path, "wb") as stream:
        stream.write(value)
    return path


def approval_entry():
    return {
        "gate": "MERGE_GATE",
        "status": "APPROVED",
        "actor": {"type": "human", "id": "reviewer"},
        "decided_at": datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc).isoformat(),
        "expires_at": datetime(2026, 8, 28, 6, 0, tzinfo=timezone.utc).isoformat(),
        "evidence_ref": "REVIEW-001",
    }


class TestConstrainedExecution(unittest.TestCase):
    def setUp(self):
        self.target = tempfile.mkdtemp(prefix="aeh-m5-exec-")

    def test_argv_executes_without_shell(self):
        code, output, receipt = xmod.run_execution(
            self.target, {"argv": [sys.executable, "-c", "print('safe')"]})
        self.assertEqual(code, 0, output)
        self.assertIn("safe", output)
        self.assertIn("shell=false", receipt)

    def test_legacy_command_is_parsed_without_shell(self):
        code, output, receipt = xmod.run_execution(
            self.target, {"command": "python -c \"print('compat')\""})
        self.assertEqual(code, 0, output)
        self.assertIn("compat", output)
        self.assertIn("compatibility-argv", receipt)

    def test_quoted_executable_path_remains_portable(self):
        command = '"' + sys.executable + '" -c "print(\'quoted\')"'
        code, output, _ = xmod.run_execution(
            self.target, {"command": command})
        self.assertEqual(code, 0, output)
        self.assertIn("quoted", output)

    def test_shell_injection_syntax_is_blocked_by_default(self):
        marker = os.path.join(self.target, "injected.txt")
        command = "python -c \"print('safe')\" ; python -c \"open('injected.txt','w').write('x')\""
        with self.assertRaisesRegex(xmod.ExecutionPolicyError, "BLOCKED_SHELL_SYNTAX"):
            xmod.run_execution(self.target, {"command": command})
        self.assertFalse(os.path.exists(marker))

    def test_shell_requires_plan_and_invocation_authorization(self):
        spec = {"command": "echo first && echo second", "shell": True}
        with self.assertRaisesRegex(
                xmod.ExecutionPolicyError, "BLOCKED_SHELL_AUTHORIZATION_REQUIRED"):
            xmod.run_execution(self.target, spec)
        code, output, receipt = xmod.run_execution(
            self.target, spec, allow_shell=True)
        self.assertEqual(code, 0, output)
        self.assertIn("second", output)
        self.assertIn("authorized-shell", receipt)

    def test_cwd_symlink_or_parent_escape_is_blocked(self):
        with self.assertRaisesRegex(xmod.ExecutionPolicyError, "BLOCKED_CWD_ESCAPE"):
            xmod.run_execution(
                self.target, {"argv": [sys.executable, "-c", "print(1)"], "cwd": ".."})

    def test_timeout_above_policy_cap_is_blocked(self):
        with self.assertRaisesRegex(xmod.ExecutionPolicyError, "BLOCKED_EXECUTION_TIMEOUT"):
            xmod.run_execution(
                self.target,
                {"argv": [sys.executable, "-c", "print(1)"], "timeout_seconds": 901},
            )

    def test_non_allowlisted_environment_is_not_inherited_or_injected(self):
        old = os.environ.get("AEH_M5_SECRET")
        os.environ["AEH_M5_SECRET"] = "must-not-leak"
        try:
            code, output, _ = xmod.run_execution(
                self.target,
                {"argv": [sys.executable, "-c",
                          "import os; print(os.getenv('AEH_M5_SECRET', 'absent'))"]},
            )
            self.assertEqual(code, 0, output)
            self.assertIn("absent", output)
            with self.assertRaisesRegex(xmod.ExecutionPolicyError, "BLOCKED_EXECUTION_ENV"):
                xmod.run_execution(
                    self.target,
                    {"argv": [sys.executable, "-c", "print(1)"],
                     "env": {"AEH_M5_SECRET": "inject"}},
                )
        finally:
            if old is None:
                os.environ.pop("AEH_M5_SECRET", None)
            else:
                os.environ["AEH_M5_SECRET"] = old


class TestApprovalCredentials(unittest.TestCase):
    def setUp(self):
        self.target = tempfile.mkdtemp(prefix="aeh-m5-credential-")
        self.key_path = make_key(self.target)
        self.entry = approval_entry()
        self.entry["credential"] = credmod.sign(
            self.target, "reviewer", self.entry, "CHG-2026-0001", "APPROVED")

    def test_signed_approval_verifies_and_matches_schema(self):
        valid, message = credmod.verify(
            self.target, self.entry["credential"], self.entry,
            "CHG-2026-0001", "APPROVED")
        self.assertTrue(valid, message)
        schema_path = os.path.join(ROOT, "schemas", "approvals.schema.json")
        with open(schema_path, encoding="utf-8") as stream:
            schema = yaml.safe_load(stream)
        jsonschema.validate({"approvals": [self.entry]}, schema)

    def test_payload_tamper_and_cross_change_replay_fail(self):
        tampered = dict(self.entry)
        tampered["actor"] = {"type": "human", "id": "attacker"}
        self.assertFalse(credmod.verify(
            self.target, tampered["credential"], tampered,
            "CHG-2026-0001", "APPROVED")[0])
        self.assertFalse(credmod.verify(
            self.target, self.entry["credential"], self.entry,
            "CHG-2026-9999", "APPROVED")[0])

    def test_wrong_key_and_unknown_key_fail(self):
        wrong = make_key(
            self.target, key_id="wrong",
            value=b"different-m5-credential-material-000000")
        valid, _ = credmod.verify(
            self.target, self.entry["credential"], self.entry,
            "CHG-2026-0001", "APPROVED",
            key_files={"reviewer": wrong})
        self.assertFalse(valid)
        os.remove(self.key_path)
        self.assertFalse(credmod.verify(
            self.target, self.entry["credential"], self.entry,
            "CHG-2026-0001", "APPROVED")[0])

    def test_legacy_unsigned_positive_gate_cannot_unlock_m5(self):
        unsigned = approval_entry()
        state, warnings = amod.assess_approval(
            unsigned, target=self.target, change_id="CHG-2026-0001",
            require_credential=True)
        self.assertEqual(state, "UNVERIFIED")
        self.assertTrue(any("no credential" in item for item in warnings))

    def test_revocation_preserves_original_signature(self):
        original = dict(self.entry["credential"])
        self.entry["status"] = "REVOKED"
        self.entry["revoked_at"] = datetime(
            2026, 8, 27, 7, 0, tzinfo=timezone.utc).isoformat()
        self.entry["revoked_by"] = {"type": "human", "id": "security-reviewer"}
        self.entry["revocation_evidence_ref"] = "INC-001"
        self.entry["revocation_credential"] = credmod.sign(
            self.target, "reviewer", self.entry, "CHG-2026-0001", "REVOKED")
        self.assertEqual(self.entry["credential"], original)
        self.assertTrue(credmod.verify(
            self.target, self.entry["revocation_credential"], self.entry,
            "CHG-2026-0001", "REVOKED")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
