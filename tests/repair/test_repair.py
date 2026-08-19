import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeh import repair  # noqa: E402
from aeh import transaction as tx  # noqa: E402
from aeh.bootstrap import pipeline as bp  # noqa: E402
from aeh.doctor import doctor as doc  # noqa: E402
from aeh.runtime import change as change_module  # noqa: E402


MANAGED_BEGIN = "<!-- AEH:BEGIN MANAGED -->"
PRIVATE_ENTRY = ".aeh/private/"


def snapshot(root):
    result = {}
    for directory, _, names in os.walk(root):
        for name in names:
            path = os.path.join(directory, name)
            with open(path, "rb") as stream:
                result[os.path.relpath(path, root)] = hashlib.sha256(stream.read()).hexdigest()
    return result


class RepairBase(unittest.TestCase):
    def make_healthy(self):
        target = tempfile.mkdtemp(prefix="aeh-m2-repair-")
        with open(os.path.join(target, "AGENTS.md"), "w", encoding="utf-8") as stream:
            stream.write("# user rules\nkeep me\n")
        with open(os.path.join(target, ".gitignore"), "w", encoding="utf-8") as stream:
            stream.write("__pycache__/\n")
        installed = bp.bootstrap(target, dry_run=False)
        self.assertEqual(installed["status"], "BOOTSTRAP_COMPLETE", installed)
        self.assertRegex(installed["transaction_id"], r"^BST-\d{4}-\d{4}$")
        return target

    def assert_ready(self, target):
        result = doc.run_doctor(target)
        self.assertNotEqual(result["overall"], "BLOCKED", result)
        return result

    def repair_apply(self, target):
        planned = repair.run_repair(target)
        self.assertEqual(planned["status"], "REPAIR_PLAN_READY", planned)
        self.assertTrue(planned["plan"]["dry_run"])
        applied = repair.run_repair(target, apply=True)
        self.assertEqual(applied["status"], "REPAIR_APPLIED", applied)
        self.assertRegex(applied["transaction_id"], r"^RPR-\d{4}-\d{4}$")
        self.assert_ready(target)
        return planned, applied


class TestRepairFaults(RepairBase):
    def test_missing_runtime_file_dry_run_apply_and_rollback(self):
        target = self.make_healthy()
        runtime_file = os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml")
        os.remove(runtime_file)
        self.assertEqual(doc.run_doctor(target)["overall"], "BLOCKED")
        before = snapshot(target)
        planned = repair.run_repair(target)
        self.assertEqual(planned["status"], "REPAIR_PLAN_READY")
        self.assertEqual(snapshot(target), before)
        self.assertIn("WRITE_CANONICAL_RUNTIME",
                      [operation["action"] for operation in planned["plan"]["operations"]])
        applied = repair.run_repair(target, apply=True)
        self.assertEqual(applied["status"], "REPAIR_APPLIED", applied)
        self.assertTrue(os.path.isfile(runtime_file))
        self.assert_ready(target)

        rolled_back = repair.rollback(target, applied["transaction_id"])
        self.assertEqual(rolled_back["status"], "REPAIR_ROLLED_BACK", rolled_back)
        self.assertFalse(os.path.exists(runtime_file))
        self.assertEqual(doc.run_doctor(target)["overall"], "BLOCKED")

    def test_runtime_digest_mismatch(self):
        target = self.make_healthy()
        path = os.path.join(target, ".aeh", "runtime", "core", "states.yaml")
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("# damaged\n")
        self.repair_apply(target)

    def test_managed_block_damage_preserves_exterior_text(self):
        target = self.make_healthy()
        path = os.path.join(target, "AGENTS.md")
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("\n" + MANAGED_BEGIN + "\ncorrupt tail that must be preserved\n")
        self.assertEqual(doc.run_doctor(target)["overall"], "BLOCKED")
        self.repair_apply(target)
        text = Path(path).read_text(encoding="utf-8")
        self.assertEqual(text.count(MANAGED_BEGIN), 1)
        self.assertIn("keep me", text)
        self.assertIn("corrupt tail that must be preserved", text)

    def test_partial_install_residue(self):
        target = self.make_healthy()
        residue = os.path.join(target, ".aeh", "manifest.yaml.aeh-tmp")
        Path(residue).write_text("partial", encoding="utf-8")
        self.repair_apply(target)
        self.assertFalse(os.path.exists(residue))

    def test_gitignore_missing_entry(self):
        target = self.make_healthy()
        path = os.path.join(target, ".gitignore")
        Path(path).write_text("dist/\n", encoding="utf-8")
        self.repair_apply(target)
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("dist/", text)
        self.assertEqual(text.count(PRIVATE_ENTRY), 1)

    def test_gitignore_absent_warn_is_repairable(self):
        target = self.make_healthy()
        os.remove(os.path.join(target, ".gitignore"))
        planned, _ = self.repair_apply(target)
        self.assertIn("private.gitignore", planned["plan"]["repairable_checks"])


class TestRepairSafety(RepairBase):
    def test_source_digest_mismatch_blocks_without_write(self):
        target = self.make_healthy()
        manifest_path = os.path.join(target, ".aeh", "manifest.yaml")
        manifest = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
        manifest["source_hashes"]["runtime"] = "0" * 64
        Path(manifest_path).write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        before = snapshot(target)
        result = repair.run_repair(target, apply=True)
        self.assertEqual(result["status"], "BLOCKED_REPAIR_SOURCE_MISMATCH", result)
        self.assertEqual(snapshot(target), before)

    def test_unbounded_managed_damage_blocks_without_write(self):
        target = self.make_healthy()
        path = os.path.join(target, "AGENTS.md")
        text = Path(path).read_text(encoding="utf-8").replace("<!-- AEH:END MANAGED -->", "")
        Path(path).write_text(text, encoding="utf-8")
        before = snapshot(target)
        result = repair.run_repair(target, apply=True)
        self.assertEqual(result["status"], "BLOCKED_REPAIR_UNSAFE_MANAGED", result)
        self.assertEqual(snapshot(target), before)

    def test_rollback_drift_blocks_without_overwrite(self):
        target = self.make_healthy()
        path = os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml")
        os.remove(path)
        applied = repair.run_repair(target, apply=True)
        self.assertEqual(applied["status"], "REPAIR_APPLIED")
        Path(path).write_text("new user state\n", encoding="utf-8")
        result = repair.rollback(target, applied["transaction_id"])
        self.assertEqual(result["status"], "BLOCKED_ROLLBACK_DRIFT", result)
        self.assertEqual(Path(path).read_text(encoding="utf-8"), "new user state\n")

    def test_private_residue_is_not_read_or_removed(self):
        target = self.make_healthy()
        secret = os.path.join(target, ".aeh", "private", "secret.aeh-tmp")
        Path(secret).write_text("SECRET-TOKEN-123", encoding="utf-8")
        doctor_result = doc.run_doctor(target)
        self.assertNotEqual(doctor_result["overall"], "BLOCKED")
        serialized = json.dumps(repair.run_repair(target), default=str)
        self.assertNotIn("SECRET-TOKEN-123", serialized)
        self.assertTrue(os.path.isfile(secret))

    def test_transaction_rejects_cross_platform_unsafe_paths(self):
        target = tempfile.mkdtemp(prefix="aeh-m2-path-")
        for relative in ("../escape.txt", "C:\\Windows\\win.ini"):
            with self.subTest(relative=relative):
                with self.assertRaises(tx.TransactionError):
                    tx.apply_mutations(target, "repair", "RPR", [{
                        "action": "WRITE", "path": relative, "kind": "file",
                        "content": b"x", "reason": "test",
                    }], {"test": relative})

    def test_injected_failure_automatically_rolls_back(self):
        target = tempfile.mkdtemp(prefix="aeh-m2-auto-rollback-")
        Path(target, "one.txt").write_text("one-before", encoding="utf-8")
        Path(target, "two.txt").write_text("two-before", encoding="utf-8")
        mutations = [
            {"action": "WRITE", "path": "one.txt", "kind": "file", "content": b"one-after", "reason": "test"},
            {"action": "WRITE", "path": "two.txt", "kind": "file", "content": b"two-after", "reason": "test"},
        ]
        with self.assertRaises(tx.TransactionError):
            tx.apply_mutations(target, "repair", "RPR", mutations, {"test": True}, fail_after=1)
        self.assertEqual(Path(target, "one.txt").read_text(encoding="utf-8"), "one-before")
        self.assertEqual(Path(target, "two.txt").read_text(encoding="utf-8"), "two-before")
        journals = list(Path(target, ".aeh", "transactions").glob("RPR-*/journal.yaml"))
        self.assertEqual(len(journals), 1)
        journal = yaml.safe_load(journals[0].read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "APPLY_FAILED_ROLLED_BACK")

    def test_apply_drift_is_not_overwritten_and_prior_write_is_rolled_back(self):
        target = tempfile.mkdtemp(prefix="aeh-m2-apply-drift-")
        one = Path(target, "one.txt")
        two = Path(target, "two.txt")
        one.write_text("one-before", encoding="utf-8")
        two.write_text("two-before", encoding="utf-8")
        mutations = [
            {"action": "WRITE", "path": "one.txt", "kind": "file", "content": b"one-after", "reason": "test"},
            {"action": "WRITE", "path": "two.txt", "kind": "file", "content": b"two-after", "reason": "test"},
        ]

        def drift(item, _operation):
            if item["path"] == "two.txt":
                two.write_text("outside-change", encoding="utf-8")

        with self.assertRaisesRegex(tx.TransactionError, "BLOCKED_APPLY_DRIFT"):
            tx.apply_mutations(target, "repair", "RPR", mutations, {"test": "drift"},
                               _before_operation=drift)
        self.assertEqual(one.read_text(encoding="utf-8"), "one-before")
        self.assertEqual(two.read_text(encoding="utf-8"), "outside-change")

    def test_interrupted_transaction_can_be_explicitly_rolled_back(self):
        target = tempfile.mkdtemp(prefix="aeh-m2-interrupted-")
        path = Path(target, "value.txt")
        path.write_text("before", encoding="utf-8")
        journal = tx.apply_mutations(target, "repair", "RPR", [{
            "action": "WRITE", "path": "value.txt", "kind": "file",
            "content": b"after", "reason": "test",
        }], {"test": "interrupted"})
        journal_path = Path(target, ".aeh", "transactions", journal["transaction_id"], "journal.yaml")
        interrupted = yaml.safe_load(journal_path.read_text(encoding="utf-8"))
        interrupted["status"] = "APPLYING"
        journal_path.write_text(yaml.safe_dump(interrupted, sort_keys=True), encoding="utf-8")

        diagnosis = doc.run_doctor(target)
        residue_check = next(item for item in diagnosis["checks"]
                             if item["check_id"] == "install.staging_residue")
        self.assertEqual(residue_check["status"], "BLOCKED")
        self.assertIn(journal["transaction_id"], residue_check["remediation"])

        result = repair.rollback(target, journal["transaction_id"])
        self.assertEqual(result["status"], "REPAIR_ROLLED_BACK", result)
        self.assertEqual(path.read_text(encoding="utf-8"), "before")
        recovered = yaml.safe_load(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(recovered["status"], "ROLLED_BACK")


class TestJournalsAndWorkflow(RepairBase):
    def test_bootstrap_journal_schema_and_idempotence(self):
        target = self.make_healthy()
        journals_before = list(Path(target, ".aeh", "transactions").glob("BST-*/journal.yaml"))
        self.assertEqual(len(journals_before), 1)
        journal = yaml.safe_load(journals_before[0].read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "schemas" / "transaction-journal.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(journal, schema)
        self.assertEqual(journal["status"], "APPLIED")
        second = bp.bootstrap(target, dry_run=False)
        self.assertEqual(second["status"], "BOOTSTRAP_COMPLETE")
        self.assertIsNone(second["transaction_id"])
        self.assertEqual(len(list(Path(target, ".aeh", "transactions").glob("BST-*/journal.yaml"))), 1)

    def test_bootstrap_transaction_can_be_rolled_back(self):
        target = self.make_healthy()
        journal_path = next(Path(target, ".aeh", "transactions").glob("BST-*/journal.yaml"))
        transaction_id = journal_path.parent.name
        result = repair.rollback(target, transaction_id)
        self.assertEqual(result["status"], "REPAIR_ROLLED_BACK", result)
        self.assertFalse(os.path.isfile(os.path.join(target, ".aeh", "manifest.yaml")))
        self.assertIn("keep me", Path(target, "AGENTS.md").read_text(encoding="utf-8"))

    def test_change_repair_shortcuts_use_frozen_conditions(self):
        for kind, expected in (("test", "TEST_REPAIR"), ("spec", "SPEC_REPAIR")):
            with self.subTest(kind=kind):
                target = self.make_healthy()
                created = change_module.change_new(target, "repair route", suggested_level="LIGHTWEIGHT")
                change = change_module.load_change(target, created["change_id"])
                change["state"] = {"current": "GREEN", "previous": "RED"}
                change_module.save_change(target, change)
                result = change_module.change_repair(target, created["change_id"], kind)
                self.assertEqual(result["status"], "TRANSITION_OK", result)
                self.assertEqual(result["to"], expected)

    def test_change_repair_does_not_bypass_illegal_state(self):
        target = self.make_healthy()
        created = change_module.change_new(target, "repair route", suggested_level="LIGHTWEIGHT")
        result = change_module.change_repair(target, created["change_id"], "test")
        self.assertEqual(result["status"], "BLOCKED_ILLEGAL_STATE_TRANSITION", result)

    def test_cli_default_plan_apply_and_rollback(self):
        target = self.make_healthy()
        runtime_file = os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml")
        os.remove(runtime_file)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        planned = subprocess.run([sys.executable, "-m", "aeh.cli", "repair", target],
                                 capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["status"], "REPAIR_PLAN_READY")
        self.assertFalse(os.path.isfile(runtime_file))
        applied = subprocess.run([sys.executable, "-m", "aeh.cli", "repair", target, "--apply"],
                                 capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        applied_result = json.loads(applied.stdout)
        rolled = subprocess.run([sys.executable, "-m", "aeh.cli", "repair", target,
                                 "--rollback", applied_result["transaction_id"]],
                                capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(rolled.returncode, 0, rolled.stderr)
        self.assertEqual(json.loads(rolled.stdout)["status"], "REPAIR_ROLLED_BACK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
