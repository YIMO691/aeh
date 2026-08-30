"""M6.1 real-flow and adversarial tests for read-only CI replay."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh import ci
from aeh import cli
from aeh.bootstrap import pipeline as bp
from aeh.runtime import approval as amod
from aeh.runtime import verify as vmod
from tests.runtime import test_verify as flow


OBSERVED_AT = "2026-08-27T12:00:00+08:00"


def git(target, *args):
    result = subprocess.run(["git", "-C", target, *args], capture_output=True,
                            text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def tree_digest(root):
    values = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def commit_all(target, message):
    git(target, "add", "-A")
    git(target, "commit", "-m", message)
    return git(target, "rev-parse", "HEAD")


class TestCiReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = tempfile.mkdtemp(prefix="aeh-ci-seed-")
        shutil.copytree(flow.NEUTRAL_REPO, cls.seed, dirs_exist_ok=True)
        git(cls.seed, "init")
        git(cls.seed, "config", "user.email", "aeh-test@example.invalid")
        git(cls.seed, "config", "user.name", "AEH Test")
        git(cls.seed, "remote", "add", "origin", "https://example.invalid/example/project.git")
        cls.base = commit_all(cls.seed, "base")
        assert bp.bootstrap(cls.seed, flow.answers_path(), dry_run=False,
                            source_revision="m6-test")["status"] == "BOOTSTRAP_COMPLETE"
        flow.provision_test_key(cls.seed)
        cls.change_id = flow.to_green(cls.seed)
        assert vmod.change_verify(cls.seed, cls.change_id)["status"] == "VERIFY_COMPLETE"
        assert amod.record_approval(
            cls.seed, cls.change_id, "MERGE_GATE", "APPROVED", "reviewer",
            key_id=flow.TEST_KEY_ID)["status"] == "APPROVAL_RECORDED"
        cls.external_key = tempfile.mktemp(prefix="aeh-ci-key-", suffix=".key")
        Path(cls.external_key).write_bytes(flow.TEST_KEY)
        cls.head = commit_all(cls.seed, "verified change")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.seed, ignore_errors=True)
        try:
            os.unlink(cls.external_key)
        except OSError:
            pass

    def make_copy(self):
        parent = tempfile.mkdtemp(prefix="aeh-ci-case-")
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        target = os.path.join(parent, "repo")
        result = subprocess.run(
            ["git", "clone", "--quiet", "--no-local", self.seed, target],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        shutil.copytree(
            self.seed, target, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git"),
        )
        git(target, "add", "--renormalize", ".")
        git(target, "remote", "set-url", "origin",
            "https://example.invalid/example/project.git")
        git(target, "config", "user.email", "aeh-test@example.invalid")
        git(target, "config", "user.name", "AEH Test")
        return target

    def replay(self, target, **overrides):
        arguments = {
            "target": target, "change_id": self.change_id,
            "repository_id": "example.invalid/example/project", "base_sha": self.base,
            "head_sha": self.head, "observed_at": OBSERVED_AT,
            "credential_files": {flow.TEST_KEY_ID: self.external_key},
        }
        arguments.update(overrides)
        return ci.verify(**arguments)

    def test_pass_is_deterministic_schema_valid_and_zero_write(self):
        target = self.make_copy()
        before = tree_digest(target)
        first = self.replay(target)
        second = self.replay(target)
        self.assertEqual(first["verdict"], "PASS", first)
        self.assertEqual(first, second)
        self.assertEqual(before, tree_digest(target))
        schema = json.loads(Path(ROOT, "schemas", "ci-report.schema.json").read_text(encoding="utf-8"))
        import jsonschema
        jsonschema.validate(first, schema)
        unsigned = dict(first)
        digest = unsigned.pop("canonical_digest")
        self.assertEqual(digest, hashlib.sha256(ci._canonical(unsigned)).hexdigest())

    def test_replay_never_invokes_project_execution(self):
        target = self.make_copy()
        with mock.patch("aeh.runtime.green.run_execution",
                        side_effect=AssertionError("project command executed")):
            self.assertEqual(self.replay(target)["verdict"], "PASS")

    def test_cli_emits_pass_and_external_report(self):
        target = self.make_copy()
        report_path = tempfile.mktemp(prefix="aeh-ci-cli-", suffix=".json")
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main([
                "ci", "verify", self.change_id, "--workdir", target,
                "--repository-id", "example.invalid/example/project",
                "--base-sha", self.base, "--head-sha", self.head,
                "--observed-at", OBSERVED_AT,
                "--approval-key", flow.TEST_KEY_ID + "=" + self.external_key,
                "--report", report_path,
            ])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["verdict"], "PASS")
        self.assertEqual(json.loads(Path(report_path).read_text(encoding="utf-8"))["verdict"], "PASS")

    def test_wrong_head_and_base_are_not_pass(self):
        target = self.make_copy()
        wrong = "0" * 40
        self.assertEqual(self.replay(target, head_sha=wrong)["verdict"], "INVALID")
        self.assertNotEqual(self.replay(target, base_sha=wrong)["verdict"], "PASS")

    def test_wrong_repository_identity_is_invalid(self):
        target = self.make_copy()
        report = self.replay(target, repository_id="example.invalid/other/project")
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "scm.repository")

    def test_dirty_or_untracked_checkout_is_invalid(self):
        target = self.make_copy()
        Path(target, "untracked.txt").write_text("attack", encoding="utf-8")
        report = self.replay(target)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "scm.clean")

    def test_missing_protected_approval_key_fails_closed(self):
        target = self.make_copy()
        report = self.replay(target, credential_files={})
        self.assertEqual(report["verdict"], "BLOCKED", report)
        self.assertEqual(report["checks"][-1]["id"], "approvals.credentials")

    def test_scm_merge_delegation_is_provider_scoped(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "changes", self.change_id, "approvals.yaml")
        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        entry = next(item for item in body["approvals"] if item["gate"] == "MERGE_GATE")
        entry.pop("credential", None)
        entry["trust_mode"] = amod.SCM_AUTHENTICATED_MERGE
        entry["evidence_ref"] = "owner-decision:T-1"
        path.write_text(yaml.safe_dump(body, sort_keys=True, allow_unicode=True), encoding="utf-8")
        head = commit_all(target, "delegate merge approval to SCM")
        blocked = self.replay(target, head_sha=head, credential_files={})
        self.assertEqual(blocked["verdict"], "BLOCKED", blocked)
        self.assertEqual(blocked["checks"][-1]["id"], "approvals.credentials")
        accepted = self.replay(
            target, head_sha=head, credential_files={},
            accepted_approval_trust_modes={amod.SCM_AUTHENTICATED_MERGE})
        self.assertEqual(accepted["verdict"], "PASS", accepted)

    def test_committed_forged_output_hash_is_invalid(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "changes", self.change_id, "verification.yaml")
        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        body["results"][0]["output_hash"] = "0" * 64
        path.write_text(yaml.safe_dump(body, sort_keys=True, allow_unicode=True), encoding="utf-8")
        forged_head = commit_all(target, "forge output hash")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "evidence.hashes")

    def test_committed_runtime_tamper_is_invalid(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "runtime", "core", "ci-policy.yaml")
        path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        forged_head = commit_all(target, "tamper runtime")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "runtime.integrity")

    def test_committed_test_lock_tamper_is_invalid(self):
        target = self.make_copy()
        path = Path(target, "tests", "test_order.py")
        path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        forged_head = commit_all(target, "tamper locked test")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "test.lock")

    def test_committed_production_preimage_forgery_is_invalid(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "changes", self.change_id, "green.yaml")
        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        body["changed_files"][0]["before_hash"] = "0" * 64
        before_parts = sorted(item["before_hash"] + "\0" + item["path"]
                              for item in body["changed_files"])
        body["production_before_hash"] = hashlib.sha256(
            "\n".join(before_parts).encode("utf-8")).hexdigest()
        path.write_text(yaml.safe_dump(body, sort_keys=True, allow_unicode=True), encoding="utf-8")
        forged_head = commit_all(target, "forge production preimage")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "implementation.hashes")

    def test_base_preimage_accepts_safe_line_ending_materialization(self):
        target = tempfile.mkdtemp(prefix="aeh-ci-filter-")
        git(target, "init")
        git(target, "config", "user.email", "aeh-test@example.invalid")
        git(target, "config", "user.name", "AEH Test")
        git(target, "config", "core.autocrlf", "true")
        sample = Path(target, "sample.txt")
        sample.write_bytes(b"first\r\nsecond\r\n")
        revision = commit_all(target, "filtered base")
        raw = subprocess.run(
            ["git", "-C", target, "show", revision + ":sample.txt"],
            capture_output=True, check=True,
        ).stdout
        self.assertEqual(raw, b"first\nsecond\n")
        self.assertIn(hashlib.sha256(sample.read_bytes()).hexdigest(),
                      ci._portable_content_hashes(
                          ci._git_blob(target, revision, "sample.txt")))

    def test_committed_path_escape_is_rejected_before_lock_replay(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "changes", self.change_id, "test-plan.yaml")
        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        body["test_files"][0]["dest"] = "../outside.py"
        path.write_text(yaml.safe_dump(body, sort_keys=True, allow_unicode=True), encoding="utf-8")
        forged_head = commit_all(target, "forge escaping test path")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "artifacts.schema")

    def test_committed_traceability_forgery_is_invalid(self):
        target = self.make_copy()
        path = Path(target, ".aeh", "changes", self.change_id, "traceability.yaml")
        body = yaml.safe_load(path.read_text(encoding="utf-8"))
        body["requirements"][0]["verification"] = []
        path.write_text(yaml.safe_dump(body, sort_keys=True, allow_unicode=True), encoding="utf-8")
        forged_head = commit_all(target, "forge trace")
        report = self.replay(target, head_sha=forged_head)
        self.assertEqual(report["verdict"], "INVALID", report)
        self.assertEqual(report["checks"][-1]["id"], "traceability.complete")

    def test_report_output_must_be_outside_target(self):
        target = self.make_copy()
        report = self.replay(target)
        outside = tempfile.mktemp(prefix="aeh-ci-report-", suffix=".json")
        ci.write_report(report, outside, target)
        self.assertEqual(json.loads(Path(outside).read_text(encoding="utf-8")), report)
        with self.assertRaises(ci.ReplayFailure):
            ci.write_report(report, os.path.join(target, "report.json"), target)


if __name__ == "__main__":
    unittest.main()
