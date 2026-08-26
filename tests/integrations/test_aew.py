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

from aeh.bootstrap import pipeline as bootstrap  # noqa: E402
from aeh.integrations import aew  # noqa: E402
from aeh.runtime import change as change_module  # noqa: E402


def snapshot(root):
    result = {}
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            path = os.path.join(directory, name)
            with open(path, "rb") as stream:
                result[os.path.relpath(path, root)] = hashlib.sha256(stream.read()).hexdigest()
    return result


class TestScmInspection(unittest.TestCase):
    def test_svn_root_and_nested_git_are_detected_without_writes(self):
        target = tempfile.mkdtemp(prefix="aeh-scm-")
        Path(target, ".svn").mkdir()
        nested = Path(target, "project", "nested")
        nested.mkdir(parents=True)
        Path(nested, ".git").mkdir()
        Path(target, "keep.txt").write_text("keep", encoding="utf-8")
        before = snapshot(target)

        report = aew.inspect_scm(target)

        self.assertEqual(report["root_repository"]["type"], "SVN")
        self.assertEqual(report["nested_repositories"], [{"path": "project/nested", "type": "GIT"}])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["network_used"])
        self.assertEqual(snapshot(target), before)

    def test_git_identity_and_dirty_state(self):
        target = tempfile.mkdtemp(prefix="aeh-git-")
        subprocess.run(["git", "init", target], check=True, capture_output=True)
        report = aew.inspect_scm(target, max_depth=1)
        self.assertEqual(report["root_repository"]["type"], "GIT")
        self.assertFalse(report["root_repository"]["identity"]["dirty"])

    def test_none_and_limits(self):
        target = tempfile.mkdtemp(prefix="aeh-none-")
        self.assertEqual(aew.inspect_scm(target)["root_repository"]["type"], "NONE")
        with self.assertRaises(aew.IntegrationError):
            aew.inspect_scm(target, max_depth=17)


class TestAewExport(unittest.TestCase):
    def make_change(self):
        target = tempfile.mkdtemp(prefix="aeh-aew-")
        installed = bootstrap.bootstrap(target, dry_run=False, source_revision="aew-test")
        self.assertEqual(installed["status"], "BOOTSTRAP_COMPLETE")
        created = change_module.change_new(target, "bounded integration export", suggested_level="STANDARD")
        self.assertEqual(created["status"], "CHANGE_CREATED", created)
        return target, created["change_id"]

    def write_verification(self, target, change_id, *, overall, result_status="pass"):
        path = Path(target, ".aeh", "changes", change_id, "verification.yaml")
        body = {
            "results": [{"id": "VER-001", "type": "target_test", "status": result_status}],
            "overall": overall,
        }
        path.write_text(yaml.safe_dump(body, sort_keys=True), encoding="utf-8")
        return path

    def test_export_is_deterministic_read_only_and_schema_valid(self):
        target, change_id = self.make_change()
        self.write_verification(target, change_id, overall="MERGE_READY")
        evidence = Path(target, ".aeh", "changes", change_id, "evidence", "verify.log")
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text("PRIVATE-CONTENT-MUST-NOT-BE-EXPORTED", encoding="utf-8")
        before = snapshot(target)

        first = aew.export_change(
            target, change_id, project_id="PRJ-1", task_id="TASK-1", run_id="RUN-1")
        second = aew.export_change(
            target, change_id, project_id="PRJ-1", task_id="TASK-1", run_id="RUN-1")

        self.assertEqual(first, second)
        self.assertEqual(first["governance"]["portable_verdict"], "VERIFIED")
        self.assertEqual(first["external_refs"]["task_id"], "TASK-1")
        self.assertEqual(set(first["metadata"]),
                         {"scope", "ownership", "authority", "lifecycle", "provenance", "cost"})
        self.assertNotIn("PRIVATE-CONTENT", json.dumps(first))
        self.assertEqual(snapshot(target), before)
        schema = json.loads((ROOT / "schemas" / "aew-governance-adapter.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(first, schema)

    def test_portable_verdict_mapping(self):
        target, change_id = self.make_change()
        not_verified = aew.export_change(target, change_id, task_id="T", run_id="R")
        self.assertEqual(not_verified["governance"]["portable_verdict"], "NOT_VERIFIED")

        path = self.write_verification(target, change_id, overall="BLOCKED", result_status="blocked")
        inconclusive = aew.export_change(target, change_id, task_id="T", run_id="R")
        self.assertEqual(inconclusive["governance"]["portable_verdict"], "INCONCLUSIVE")

        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        body["results"][0]["status"] = "fail"
        path.write_text(yaml.safe_dump(body, sort_keys=True), encoding="utf-8")
        failed = aew.export_change(target, change_id, task_id="T", run_id="R")
        self.assertEqual(failed["governance"]["portable_verdict"], "FAILED")

    def test_external_task_and_run_are_required(self):
        target, change_id = self.make_change()
        with self.assertRaises(aew.IntegrationError):
            aew.export_change(target, change_id, task_id="", run_id="R")

    def test_export_rejects_symlink_evidence(self):
        target, change_id = self.make_change()
        outside = Path(tempfile.mkdtemp(prefix="aeh-outside-"), "outside.log")
        outside.write_text("outside", encoding="utf-8")
        evidence = Path(target, ".aeh", "changes", change_id, "evidence")
        evidence.mkdir(exist_ok=True)
        try:
            (evidence / "escape.log").symlink_to(outside)
        except OSError as exc:
            self.skipTest("symlink creation unavailable: " + str(exc))
        with self.assertRaises(aew.IntegrationError):
            aew.export_change(target, change_id, task_id="T", run_id="R")


class TestIntegrationCli(unittest.TestCase):
    def test_inspect_cli_emits_json(self):
        target = tempfile.mkdtemp(prefix="aeh-cli-inspect-")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "integration", "inspect", target, "--max-depth", "1"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "INSPECTION_COMPLETE")

    def test_inspect_cli_failure_is_json(self):
        missing = os.path.join(tempfile.gettempdir(), "aeh-missing-integration-target")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "aeh.cli", "integration", "inspect", missing],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "INTEGRATION_FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
