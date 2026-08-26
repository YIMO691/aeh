import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeh import transaction as tx  # noqa: E402
from aeh import upgrade  # noqa: E402
from aeh.bootstrap import pipeline as bp  # noqa: E402
from aeh.doctor import doctor as doc  # noqa: E402


POST_V01_SCHEMAS = (
    "repair-plan.schema.json",
    "repair-rule.schema.json",
    "transaction-journal.schema.json",
    "upgrade-plan.schema.json",
    "upgrade-policy.schema.json",
)


def file_hash(path):
    with open(path, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def tree_hashes(root):
    result = {}
    if not os.path.exists(root):
        return result
    for directory, _, names in os.walk(root):
        for name in names:
            path = os.path.join(directory, name)
            result[os.path.relpath(path, root).replace("\\", "/")] = file_hash(path)
    return result


class UpgradeBase(unittest.TestCase):
    def make_current(self):
        target = tempfile.mkdtemp(prefix="aeh-m3-upgrade-")
        Path(target, "AGENTS.md").write_text("# user agent rules\nkeep-agent\n", encoding="utf-8")
        Path(target, "CLAUDE.md").write_text("# user claude rules\nkeep-claude\n", encoding="utf-8")
        Path(target, ".gitignore").write_text("dist/\n", encoding="utf-8")
        installed = bp.bootstrap(target, dry_run=False, source_revision="m3-current")
        self.assertEqual(installed["status"], "BOOTSTRAP_COMPLETE", installed)
        private = Path(target, ".aeh", "private", "secret.bin")
        private.write_bytes(b"PRIVATE-UPGRADE-SECRET")
        change = Path(target, ".aeh", "changes", "CHG-2026-0099")
        change.mkdir(parents=True)
        Path(change, "change.yaml").write_text("state: VERIFY\n", encoding="utf-8")
        Path(change, "approvals.yaml").write_text("approvals: [owner-approved]\n", encoding="utf-8")
        return target

    def make_v01(self, *, legacy_extra=False):
        target = self.make_current()
        runtime_schemas = Path(target, ".aeh", "runtime", "schemas")
        for name in POST_V01_SCHEMAS:
            path = runtime_schemas / name
            if path.exists():
                path.unlink()
        shutil.copyfile(
            ROOT / "tests" / "fixtures" / "upgrade-v0.1" / "manifest.schema.json",
            runtime_schemas / "manifest.schema.json",
        )
        if legacy_extra:
            Path(runtime_schemas, "legacy-only.schema.json").write_text("{}\n", encoding="utf-8")
        transactions = Path(target, ".aeh", "transactions")
        if transactions.exists():
            shutil.rmtree(transactions)
        manifest_path = Path(target, ".aeh", "manifest.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["harness"]["version"] = "0.1.0"
        manifest["harness"]["source_revision"] = "v0.1-custom" if legacy_extra else "6513102"
        manifest["owner_extension"] = {"preserve": True}
        manifest.pop("upgrade_history", None)
        manifest["source_hashes"]["runtime"] = bp.runtime_digest_at(target)
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        return target

    def protected_snapshot(self, target):
        paths = (
            ".aeh/profile.yaml",
            ".aeh/effective-workflow.yaml",
            ".aeh/bootstrap",
            ".aeh/private",
            ".aeh/changes",
            "AGENTS.md",
            "CLAUDE.md",
            ".gitignore",
        )
        snapshot = {}
        for relative in paths:
            path = os.path.join(target, *relative.split("/"))
            if os.path.isfile(path):
                snapshot[relative] = file_hash(path)
            elif os.path.isdir(path):
                snapshot[relative] = tree_hashes(path)
        return snapshot

    def managed_snapshot(self, target):
        return {
            "manifest": file_hash(os.path.join(target, ".aeh", "manifest.yaml")),
            "runtime": tree_hashes(os.path.join(target, ".aeh", "runtime")),
        }


class TestUpgradeFlow(UpgradeBase):
    def test_v01_dry_run_apply_preserves_project_data(self):
        target = self.make_v01()
        protected = self.protected_snapshot(target)
        before_all = tree_hashes(target)
        before_manifest = yaml.safe_load(Path(target, ".aeh", "manifest.yaml").read_text(encoding="utf-8"))

        planned = upgrade.run_upgrade(target, source_revision="m3-candidate")
        self.assertEqual(planned["status"], "UPGRADE_PLAN_READY", planned)
        self.assertTrue(planned["plan"]["dry_run"])
        self.assertEqual(tree_hashes(target), before_all)
        actions = {item["action"] for item in planned["plan"]["operations"]}
        self.assertTrue({"INSTALL_RUNTIME", "REPLACE_RUNTIME", "MERGE_MANIFEST"} <= actions)
        self.assertNotIn("PRIVATE-UPGRADE-SECRET", json.dumps(planned))

        applied = upgrade.run_upgrade(target, apply=True, source_revision="m3-candidate")
        self.assertEqual(applied["status"], "UPGRADE_APPLIED", applied)
        self.assertRegex(applied["transaction_id"], r"^UPG-\d{4}-\d{4}$")
        self.assertNotEqual(applied["doctor"]["overall"], "BLOCKED", applied["doctor"])
        self.assertEqual(self.protected_snapshot(target), protected)

        manifest = yaml.safe_load(Path(target, ".aeh", "manifest.yaml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["harness"]["version"], "0.2.1")
        self.assertEqual(manifest["harness"]["source_revision"], "m3-candidate")
        self.assertEqual(manifest["installed_at"], before_manifest["installed_at"])
        self.assertEqual(manifest["owner_extension"], {"preserve": True})
        self.assertEqual(manifest["source_hashes"]["runtime"], bp.compute_digests(str(ROOT))["runtime"])
        self.assertEqual(manifest["upgrade_history"][-1]["from"]["harness_version"], "0.1.0")
        self.assertEqual(manifest["upgrade_history"][-1]["to"]["harness_version"], "0.2.1")

    def test_v020_manifest_upgrades_to_v021_without_runtime_rewrite(self):
        target = self.make_current()
        protected = self.protected_snapshot(target)
        manifest_path = Path(target, ".aeh", "manifest.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["harness"]["version"] = "0.2.0"
        manifest["harness"]["source_revision"] = "v0.2.0"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")

        planned = upgrade.run_upgrade(target, source_revision="v0.2.1-candidate")
        self.assertEqual(planned["status"], "UPGRADE_PLAN_READY", planned)
        self.assertEqual(
            {item["action"] for item in planned["plan"]["operations"]},
            {"MERGE_MANIFEST"},
        )

        applied = upgrade.run_upgrade(
            target, apply=True, source_revision="v0.2.1-candidate")
        self.assertEqual(applied["status"], "UPGRADE_APPLIED", applied)
        self.assertEqual(self.protected_snapshot(target), protected)
        upgraded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(upgraded["harness"]["version"], "0.2.1")
        self.assertEqual(upgraded["upgrade_history"][-1]["from"]["harness_version"], "0.2.0")
        self.assertEqual(upgraded["upgrade_history"][-1]["to"]["harness_version"], "0.2.1")

    def test_obsolete_runtime_file_is_removed(self):
        target = self.make_v01(legacy_extra=True)
        applied = upgrade.run_upgrade(target, apply=True)
        self.assertEqual(applied["status"], "UPGRADE_APPLIED", applied)
        self.assertIn("REMOVE_RUNTIME", {item["action"] for item in applied["plan"]["operations"]})
        self.assertFalse(Path(target, ".aeh", "runtime", "schemas", "legacy-only.schema.json").exists())

    def test_applied_upgrade_can_be_rolled_back(self):
        target = self.make_v01()
        before = self.managed_snapshot(target)
        applied = upgrade.run_upgrade(target, apply=True, source_revision="m3-candidate")
        self.assertEqual(applied["status"], "UPGRADE_APPLIED", applied)
        rolled = upgrade.rollback(target, applied["transaction_id"])
        self.assertEqual(rolled["status"], "UPGRADE_ROLLED_BACK", rolled)
        self.assertEqual(self.managed_snapshot(target), before)
        self.assertEqual(rolled["doctor"]["overall"], "BLOCKED")

    def test_current_install_is_noop(self):
        target = self.make_current()
        before = tree_hashes(target)
        result = upgrade.run_upgrade(target, source_revision="m3-current")
        self.assertEqual(result["status"], "UPGRADE_NOOP", result)
        self.assertEqual(tree_hashes(target), before)

    def test_cli_plan_apply_and_rollback(self):
        target = self.make_v01(legacy_extra=False)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        planned = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "upgrade", target,
             "--source-revision", "cli-candidate"],
            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["status"], "UPGRADE_PLAN_READY")
        applied = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "upgrade", target, "--apply",
             "--source-revision", "cli-candidate"],
            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        applied_result = json.loads(applied.stdout)
        rolled = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "upgrade", target, "--rollback",
             applied_result["transaction_id"]],
            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(rolled.returncode, 0, rolled.stderr)
        self.assertEqual(json.loads(rolled.stdout)["status"], "UPGRADE_ROLLED_BACK")


class TestUpgradeSafety(UpgradeBase):
    def test_source_integrity_mismatch_blocks_without_write(self):
        target = self.make_v01()
        Path(target, ".aeh", "runtime", "core", "workflow.yaml").write_text("tampered\n", encoding="utf-8")
        before = tree_hashes(target)
        result = upgrade.run_upgrade(target, apply=True)
        self.assertEqual(result["status"], "BLOCKED_UPGRADE_SOURCE_INTEGRITY", result)
        self.assertEqual(tree_hashes(target), before)

    def test_newer_source_blocks_downgrade(self):
        target = self.make_current()
        manifest_path = Path(target, ".aeh", "manifest.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["harness"]["version"] = "9.0.0"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        result = upgrade.run_upgrade(target, apply=True)
        self.assertEqual(result["status"], "BLOCKED_UPGRADE_DOWNGRADE", result)

    def test_same_version_different_runtime_blocks_collision(self):
        target = self.make_v01()
        manifest_path = Path(target, ".aeh", "manifest.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["harness"]["version"] = "0.2.1"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        before = tree_hashes(target)
        result = upgrade.run_upgrade(target, apply=True)
        self.assertEqual(result["status"], "BLOCKED_UPGRADE_VERSION_COLLISION", result)
        self.assertEqual(tree_hashes(target), before)

    def test_unsupported_version_and_foreign_harness_block(self):
        for field, value, expected in (
            ("version", "v1", "BLOCKED_UPGRADE_UNSUPPORTED_VERSION"),
            ("name", "foreign-harness", "BLOCKED_UPGRADE_FOREIGN_HARNESS"),
        ):
            with self.subTest(field=field):
                target = self.make_v01()
                manifest_path = Path(target, ".aeh", "manifest.yaml")
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                manifest["harness"][field] = value
                manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
                self.assertEqual(upgrade.run_upgrade(target)["status"], expected)

    def test_empty_destination_revision_blocks(self):
        target = self.make_v01()
        before = tree_hashes(target)
        result = upgrade.run_upgrade(target, apply=True, source_revision="  ")
        self.assertEqual(result["status"], "BLOCKED_UPGRADE_DESTINATION_REVISION", result)
        self.assertEqual(tree_hashes(target), before)

    def test_injected_failure_restores_old_managed_state(self):
        target = self.make_v01()
        before = self.managed_snapshot(target)
        result = upgrade.run_upgrade(target, apply=True, _fail_after=1)
        self.assertEqual(result["status"], "UPGRADE_FAILED", result)
        self.assertEqual(self.managed_snapshot(target), before)
        journal_path = next(Path(target, ".aeh", "transactions").glob("UPG-*/journal.yaml"))
        journal = yaml.safe_load(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "APPLY_FAILED_ROLLED_BACK")

    def test_rollback_drift_does_not_overwrite_later_change(self):
        target = self.make_v01()
        applied = upgrade.run_upgrade(target, apply=True)
        self.assertEqual(applied["status"], "UPGRADE_APPLIED", applied)
        path = Path(target, ".aeh", "runtime", "schemas", "upgrade-plan.schema.json")
        path.write_text("outside-change\n", encoding="utf-8")
        result = upgrade.rollback(target, applied["transaction_id"])
        self.assertEqual(result["status"], "BLOCKED_ROLLBACK_DRIFT", result)
        self.assertEqual(path.read_text(encoding="utf-8"), "outside-change\n")

    def test_runtime_symlink_is_rejected_when_supported(self):
        target = self.make_v01()
        link = Path(target, ".aeh", "runtime", "core", "linked.yaml")
        try:
            os.symlink(Path(target, ".aeh", "runtime", "core", "workflow.yaml"), link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        result = upgrade.run_upgrade(target)
        self.assertEqual(result["status"], "BLOCKED_UPGRADE_UNSAFE_PATH", result)


class TestUpgradeContracts(UpgradeBase):
    def test_plan_policy_manifest_and_journal_schemas(self):
        target = self.make_v01()
        result = upgrade.run_upgrade(target, apply=True, source_revision="schema-test")
        self.assertEqual(result["status"], "UPGRADE_APPLIED", result)
        for name, value in (
            ("upgrade-plan.schema.json", result["plan"]),
            ("manifest.schema.json", yaml.safe_load(Path(target, ".aeh", "manifest.yaml").read_text(encoding="utf-8"))),
            ("transaction-journal.schema.json", result["doctor"] and result),
        ):
            if name == "transaction-journal.schema.json":
                journal, _, _ = tx.load_journal(target, result["transaction_id"], str(ROOT))
                value = journal
            schema = json.loads(Path(ROOT, "schemas", name).read_text(encoding="utf-8"))
            jsonschema.validate(value, schema)
        policy = yaml.safe_load(Path(ROOT, "bootstrap", "upgrade", "policy.yaml").read_text(encoding="utf-8"))
        policy_schema = json.loads(Path(ROOT, "schemas", "upgrade-policy.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(policy, policy_schema)


if __name__ == "__main__":
    unittest.main(verbosity=2)
