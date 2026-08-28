"""M6.2 exact-diff, GitHub binding, renderer, and enforcement audit tests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh import ci, github_ci


def git(target, *args):
    result = subprocess.run(["git", "-C", target, *args], capture_output=True,
                            text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def commit(target, message):
    git(target, "add", "-A")
    git(target, "commit", "-m", message)
    return git(target, "rev-parse", "HEAD")


class GitRepositoryCase(unittest.TestCase):
    def setUp(self):
        self.target = tempfile.mkdtemp(prefix="aeh-github-")
        self.addCleanup(shutil.rmtree, self.target, ignore_errors=True)
        git(self.target, "init")
        git(self.target, "config", "user.email", "aeh@example.invalid")
        git(self.target, "config", "user.name", "AEH")
        Path(self.target, "README.md").write_text("base\n", encoding="utf-8")
        self.base = commit(self.target, "base")
        self.policy = github_ci.load_policy()

    def add_change(self, change_id="CHG-2026-0001", production=True):
        root = Path(self.target, ".aeh", "changes", change_id)
        root.mkdir(parents=True)
        (root / "change.yaml").write_text("change_id: " + change_id + "\n", encoding="utf-8")
        (root / "green.yaml").write_text(yaml.safe_dump({
            "change_id": change_id,
            "changed_files": ([{"path": "src/app.py"}] if production else []),
        }), encoding="utf-8")
        (root / "test-plan.yaml").write_text(yaml.safe_dump({
            "test_files": [{"dest": "tests/test_app.py"}],
        }), encoding="utf-8")
        (root / "test-lock.yaml").write_text(yaml.safe_dump({
            "files": [{"path": "tests/test_app.py"}],
        }), encoding="utf-8")
        Path(self.target, "tests").mkdir(exist_ok=True)
        Path(self.target, "tests", "test_app.py").write_text("assert True\n", encoding="utf-8")
        if production:
            Path(self.target, "src").mkdir(exist_ok=True)
            Path(self.target, "src", "app.py").write_text("VALUE = 1\n", encoding="utf-8")


class TestExactDiffClosure(GitRepositoryCase):
    def test_one_fresh_declared_change_passes_deterministically(self):
        self.add_change()
        head = commit(self.target, "change")
        first = github_ci.discover_change(self.target, self.base, head, self.policy)
        second = github_ci.discover_change(self.target, self.base, head, self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first["change_id"], "CHG-2026-0001")
        self.assertIn("src/app.py", first["allowed_paths"])

    def test_zero_multiple_stale_and_unrelated_are_invalid(self):
        Path(self.target, "README.md").write_text("changed\n", encoding="utf-8")
        zero_head = commit(self.target, "zero")
        with self.assertRaises(github_ci.AssuranceFailure) as zero:
            github_ci.discover_change(self.target, self.base, zero_head, self.policy)
        self.assertEqual(zero.exception.check_id, "diff.change_count")

        other = tempfile.mkdtemp(prefix="aeh-github-multiple-")
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        git(other, "init"); git(other, "config", "user.email", "aeh@example.invalid"); git(other, "config", "user.name", "AEH")
        Path(other, "README.md").write_text("base", encoding="utf-8")
        base = commit(other, "base")
        for change_id in ("CHG-2026-0001", "CHG-2026-0002"):
            root = Path(other, ".aeh", "changes", change_id); root.mkdir(parents=True)
            (root / "change.yaml").write_text("change_id: " + change_id, encoding="utf-8")
        head = commit(other, "multiple")
        with self.assertRaises(github_ci.AssuranceFailure) as multiple:
            github_ci.discover_change(other, base, head, self.policy)
        self.assertEqual(multiple.exception.check_id, "diff.change_count")

        stale = tempfile.mkdtemp(prefix="aeh-github-stale-")
        self.addCleanup(shutil.rmtree, stale, ignore_errors=True)
        shutil.copytree(self.target, stale, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
        git(stale, "init"); git(stale, "config", "user.email", "aeh@example.invalid"); git(stale, "config", "user.name", "AEH")
        root = Path(stale, ".aeh", "changes", "CHG-2026-0099"); root.mkdir(parents=True)
        (root / "change.yaml").write_text("change_id: CHG-2026-0099\n", encoding="utf-8")
        stale_base = commit(stale, "stale base")
        (root / "change.yaml").write_text("change_id: CHG-2026-0099\ntitle: reused\n", encoding="utf-8")
        stale_head = commit(stale, "reuse")
        with self.assertRaises(github_ci.AssuranceFailure) as reuse:
            github_ci.discover_change(stale, stale_base, stale_head, self.policy)
        self.assertEqual(reuse.exception.check_id, "diff.change_freshness")

    def test_unrelated_file_fails_closed(self):
        self.add_change()
        Path(self.target, "undeclared.txt").write_text("no", encoding="utf-8")
        head = commit(self.target, "undeclared")
        with self.assertRaises(github_ci.AssuranceFailure) as error:
            github_ci.discover_change(self.target, self.base, head, self.policy)
        self.assertEqual(error.exception.check_id, "diff.closure")


class TestGitHubBinding(GitRepositoryCase):
    def configured_policy(self):
        policy = json.loads(json.dumps(self.policy))
        policy["workflow"]["expected_sha256"] = "a" * 64
        return policy

    def unconfigured_policy(self):
        policy = json.loads(json.dumps(self.policy))
        policy["workflow"]["expected_sha256"] = None
        return policy

    def event_and_run(self, head):
        event = {"number": 7, "repository": {"id": 42, "full_name": "owner/repo"},
                 "pull_request": {"base": {"sha": self.base}, "head": {"sha": head}}}
        run = {"id": 9, "run_attempt": 1, "event": "pull_request", "head_sha": head,
               "created_at": "2026-08-27T12:00:00Z", "updated_at": "2026-08-27T12:01:00Z",
               "repository": {"id": 42, "full_name": "owner/repo"},
               "check_suite": {"id": 10, "app": {"id": 15368}},
               "check_run": {"id": 11, "name": "AEH assurance / verify",
                             "head_sha": head, "app": {"id": 15368}},
               "workflow": {"path": ".github/workflows/aeh-assurance.yml", "sha256": "a" * 64}}
        return event, run

    def test_event_binding_invokes_replay_with_exact_inputs(self):
        self.add_change()
        head = commit(self.target, "change")
        event, run = self.event_and_run(head)
        replay = {"verdict": "PASS", "canonical_digest": "b" * 64, "checks": []}
        with mock.patch("aeh.github_ci.ci.verify", return_value=replay) as verify:
            report = github_ci.verify_event(
                self.target, event, "pull_request", run, self.configured_policy())
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(verify.call_args.args[1], "CHG-2026-0001")
        self.assertEqual(verify.call_args.args[2], "github.com/owner/repo")
        self.assertEqual(verify.call_args.args[3:5], (self.base, head))
        self.assertEqual(verify.call_args.args[5], "2026-08-27T12:01:00Z")

    def test_wrong_run_head_and_unconfigured_digest_fail_closed(self):
        self.add_change(); head = commit(self.target, "change")
        event, run = self.event_and_run(head)
        run["head_sha"] = "0" * 40
        report = github_ci.verify_event(self.target, event, "pull_request", run, self.configured_policy())
        self.assertEqual(report["verdict"], "INVALID")
        event, run = self.event_and_run(head)
        report = github_ci.verify_event(
            self.target, event, "pull_request", run, self.unconfigured_policy())
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertEqual(report["checks"][-1]["id"], "run.workflow_digest")

    def test_repository_identity_is_case_insensitive(self):
        self.assertEqual(
            ci._remote_repository_id("https://github.com/YIMO691/aeh.git"),
            "github.com/yimo691/aeh",
        )

    def test_protected_credentials_require_external_channel(self):
        self.add_change(); head = commit(self.target, "change")
        event, run = self.event_and_run(head)
        replay = {"verdict": "BLOCKED", "checks": [{"id": "approvals.credentials"}]}
        with mock.patch("aeh.github_ci.ci.verify", return_value=replay):
            report = github_ci.verify_event(
                self.target, event, "pull_request", run, self.configured_policy())
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertEqual(report["checks"][-1]["message"], "TRUSTED_CREDENTIAL_CHANNEL_REQUIRED")


class TestWorkflowAndAudit(unittest.TestCase):
    def setUp(self):
        self.policy = github_ci.load_policy()

    def configured(self):
        value = json.loads(json.dumps(self.policy))
        value["workflow"]["artifact"] = {
            "url": "https://example.invalid/aeh-0.3.0-py3-none-any.whl",
            "filename": "adaptive_engineering_harness-0.3.0-py3-none-any.whl",
            "sha256": "1" * 64,
        }
        rendered = github_ci.render_workflow(value)
        value["workflow"]["expected_sha256"] = rendered["sha256"]
        return value, rendered

    def test_renderer_is_deterministic_pinned_and_not_pr_installable(self):
        unconfigured = json.loads(json.dumps(self.policy))
        unconfigured["workflow"]["artifact"] = None
        unconfigured["workflow"]["expected_sha256"] = None
        with self.assertRaises(github_ci.AssuranceFailure) as missing:
            github_ci.render_workflow(unconfigured)
        self.assertEqual(missing.exception.message, "IMMUTABLE_ARTIFACT_REQUIRED")
        policy, first = self.configured()
        second = github_ci.render_workflow(policy)
        self.assertEqual(first, second)
        text = first["content"]
        self.assertIn("pull_request:\n", text)
        self.assertIn("merge_group:\n", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("fetch-depth: 0", text)
        self.assertNotIn("pip install -e", text)
        self.assertNotIn("pip install --no-deps", text)
        self.assertIn("snapshot-run --policy core/ci-enforcement-policy.yaml", text)
        self.assertIn("--policy core/ci-enforcement-policy.yaml --report", text)
        self.assertNotIn("actions/checkout@v", text)
        self.assertEqual(first["sha256"], hashlib.sha256(text.encode()).hexdigest())

    def test_configure_transaction_binds_policy_workflow_runtime_and_manifest(self):
        target = tempfile.mkdtemp(prefix="aeh-github-configure-")
        self.addCleanup(shutil.rmtree, target, ignore_errors=True)
        shutil.copytree(os.path.join(ROOT, "core"), os.path.join(target, "core"))
        shutil.copytree(os.path.join(ROOT, ".aeh", "runtime"),
                        os.path.join(target, ".aeh", "runtime"))
        for relative in (".aeh/manifest.yaml", ".aeh/profile.yaml",
                         ".aeh/effective-workflow.yaml", "AGENTS.md", "CLAUDE.md", ".gitignore"):
            destination = os.path.join(target, *relative.split("/"))
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, *relative.split("/")), destination)
        report = github_ci.configure_repository(
            target,
            "https://example.invalid/adaptive_engineering_harness-0.3.0.dev1-py3-none-any.whl",
            "adaptive_engineering_harness-0.3.0.dev1-py3-none-any.whl",
            "2" * 64,
        )
        self.assertEqual(report["verdict"], "PASS", report)
        source = Path(target, "core", "ci-enforcement-policy.yaml").read_bytes()
        runtime = Path(target, ".aeh", "runtime", "core", "ci-enforcement-policy.yaml").read_bytes()
        workflow = Path(target, ".github", "workflows", "aeh-assurance.yml").read_bytes()
        manifest = yaml.safe_load(Path(target, ".aeh", "manifest.yaml").read_text(encoding="utf-8"))
        self.assertEqual(source, runtime)
        self.assertEqual(hashlib.sha256(workflow).hexdigest(), report["workflow_sha256"])
        self.assertEqual(manifest["source_hashes"]["runtime"], report["runtime_digest"])

    def snapshot(self, policy):
        return {
            "contract": "ci.provider-snapshot", "version": 1,
            "repository": {"id": 42, "full_name": "owner/repo", "default_branch": "main"},
            "branch": "main", "head_sha": "2" * 40,
            "branch_protection": {
                "required_status_checks": {"strict": True, "checks": [{
                    "context": policy["required_check"]["name"],
                    "app_id": policy["required_check"]["app_id"]}]},
                "allow_force_pushes": {"enabled": False}, "allow_deletions": {"enabled": False},
                "enforce_admins": {"enabled": True},
            }, "rulesets": [],
            "workflow": {"path": policy["workflow"]["path"],
                         "sha256": policy["workflow"]["expected_sha256"],
                         "events": ["pull_request", "merge_group"]},
            "check_runs": [{"name": policy["required_check"]["name"],
                            "app": {"id": policy["required_check"]["app_id"]},
                            "head_sha": "2" * 40, "conclusion": "success"}],
            "external_governance": {}, "api_errors": [],
        }

    def test_audit_distinguishes_observed_required_external_and_api_unknown(self):
        policy, _ = self.configured()
        snapshot = self.snapshot(policy)
        required = github_ci.audit_enforcement(policy, snapshot)
        self.assertEqual(required["verdict"], "PASS", required)
        self.assertEqual(required["achieved_trust_level"], "REQUIRED_REPOSITORY_WORKFLOW")
        snapshot["branch_protection"]["required_status_checks"]["checks"][0]["app_id"] = 1
        observed = github_ci.audit_enforcement(policy, snapshot)
        self.assertEqual(observed["verdict"], "BLOCKED")
        self.assertEqual(observed["achieved_trust_level"], "OBSERVED_WORKFLOW")
        snapshot = self.snapshot(policy)
        snapshot["external_governance"] = {
            "required_workflow": True, "immutable_policy_ref": "org-policy@" + "3" * 40,
            "workflow_path": policy["workflow"]["path"],
            "workflow_sha256": policy["workflow"]["expected_sha256"],
            "check_name": policy["required_check"]["name"],
            "app_id": policy["required_check"]["app_id"],
        }
        external = github_ci.audit_enforcement(policy, snapshot)
        self.assertEqual(external["achieved_trust_level"], "EXTERNALLY_GOVERNED_WORKFLOW")
        snapshot = self.snapshot(policy)
        snapshot["branch_protection"] = None
        snapshot["rulesets"] = [{
            "id": 1, "target": "branch", "enforcement": "active", "bypass_actors": [],
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [
                {"type": "required_status_checks", "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [{"context": policy["required_check"]["name"],
                                                "integration_id": policy["required_check"]["app_id"]}]}},
                {"type": "non_fast_forward"}, {"type": "deletion"},
            ],
        }]
        via_ruleset = github_ci.audit_enforcement(policy, snapshot)
        self.assertEqual(via_ruleset["verdict"], "PASS", via_ruleset)
        snapshot["api_errors"] = ["branch_protection:HTTPError"]
        unknown = github_ci.audit_enforcement(policy, snapshot)
        self.assertEqual(unknown["verdict"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
