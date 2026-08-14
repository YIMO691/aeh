"""AEH Phase 7 — Doctor + Runtime Preflight 测试

覆盖 spec 20 项：healthy verdict、只读、各类 BLOCKED、篡改检测、malformed managed、
GUIDANCE_ONLY WARN、UNENFORCEABLE BLOCK、private gitignore、private 不回显、
staging 残留、git 不可用、确定性、时间无关、preflight 传播。
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp  # noqa: E402
from aeh.doctor import doctor as doc  # noqa: E402


def snapshot(root):
    out = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-doc-answers-")
    answers = {"contract": "bootstrap.interview.answers", "version": 1,
               "answers": {
                   "q-plan-before-code": {"question_id": "q-plan-before-code", "answer": "risk_based", "type": "PREFERENCE", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-testing-policy": {"question_id": "q-testing-policy", "answer": "risk_based", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-human-review": {"question_id": "q-human-review", "answer": "critical", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-modify-source": {"question_id": "q-modify-source", "answer": "allow", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-commit": {"question_id": "q-git-commit", "answer": "ask", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-push": {"question_id": "q-git-push", "answer": "deny", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-shell-access": {"question_id": "q-shell-access", "answer": "ask", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-web-access": {"question_id": "q-web-access", "answer": "deny", "type": "PERMISSION", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-team-review-policy": {"question_id": "q-team-review-policy", "answer": "major", "type": "POLICY", "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
               }, "reset": []}
    p = os.path.join(tmp, "answers.yaml")
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(answers, f, sort_keys=True, allow_unicode=True)
    return p


class DoctorBase(unittest.TestCase):
    def make_healthy(self):
        target = tempfile.mkdtemp(prefix="aeh-doc-target-")
        with open(os.path.join(target, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# user\nkeep me\n")
        with open(os.path.join(target, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("__pycache__/\n")
        report = bp.bootstrap(target, answers_path(), dry_run=False)
        self.assertEqual(report["status"], "BOOTSTRAP_COMPLETE")
        return target

    def check(self, result, check_id):
        return [c for c in result["checks"] if c["check_id"] == check_id][0]


class TestHealthyAndReadOnly(DoctorBase):
    def test_healthy_verdict(self):
        target = self.make_healthy()
        result = doc.run_doctor(target)
        self.assertIn(result["overall"], ("READY", "READY_WITH_WARNINGS"))
        with open(os.path.join(ROOT, "schemas", "doctor.schema.json"), encoding="utf-8") as fh:
            jsonschema_check = yaml.safe_load(fh)
        import jsonschema
        jsonschema.validate(result, jsonschema_check)

    def test_doctor_fully_read_only(self):
        target = self.make_healthy()
        before = snapshot(target)
        doc.run_doctor(target)
        self.assertEqual(snapshot(target), before)


class TestBlockedConditions(DoctorBase):
    def test_manifest_missing(self):
        target = self.make_healthy()
        os.remove(os.path.join(target, ".aeh", "manifest.yaml"))
        result = doc.run_doctor(target)
        self.assertEqual(result["overall"], "BLOCKED")
        self.assertEqual(self.check(result, "install.manifest")["status"], "BLOCKED")

    def test_profile_schema_error(self):
        target = self.make_healthy()
        with open(os.path.join(target, ".aeh", "profile.yaml"), "w", encoding="utf-8") as f:
            f.write("profile_version: [broken\n")
        result = doc.run_doctor(target)
        self.assertEqual(result["overall"], "BLOCKED")
        self.assertEqual(self.check(result, "profile.schema")["status"], "BLOCKED")

    def test_effective_workflow_error(self):
        target = self.make_healthy()
        with open(os.path.join(target, ".aeh", "effective-workflow.yaml"), "w", encoding="utf-8") as f:
            f.write("workflow_version: [broken\n")
        result = doc.run_doctor(target)
        self.assertEqual(result["overall"], "BLOCKED")
        self.assertEqual(self.check(result, "workflow.schema")["status"], "BLOCKED")

    def test_runtime_tamper(self):
        target = self.make_healthy()
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "contract.runtime_digest")["status"], "BLOCKED")
        self.assertIn("BLOCKED_RUNTIME_INTEGRITY", self.check(result, "contract.runtime_digest")["message"])

    def test_profile_status_blocked(self):
        target = self.make_healthy()
        profile = yaml.safe_load(open(os.path.join(target, ".aeh", "profile.yaml"), encoding="utf-8"))
        profile["status"] = "BLOCKED"
        with open(os.path.join(target, ".aeh", "profile.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(profile, f, sort_keys=True)
        result = doc.run_doctor(target)
        self.assertEqual(result["overall"], "BLOCKED")
        self.assertEqual(self.check(result, "profile.status")["status"], "BLOCKED")

    def test_unresolved_conflict(self):
        target = self.make_healthy()
        profile = yaml.safe_load(open(os.path.join(target, ".aeh", "profile.yaml"), encoding="utf-8"))
        profile["conflicts"] = [{"conflict_id": "CONF-001", "field": "team.policy_x", "level": "team",
                                 "candidates": [{"value": "a", "source": {"type": "x", "ref": "r1"}}],
                                 "resolution": None, "status": "BLOCKED_POLICY_CONFLICT"}]
        with open(os.path.join(target, ".aeh", "profile.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(profile, f, sort_keys=True)
        result = doc.run_doctor(target)
        self.assertEqual(result["overall"], "BLOCKED")
        self.assertEqual(self.check(result, "profile.conflicts")["status"], "BLOCKED")

    def test_malformed_agents_managed(self):
        target = self.make_healthy()
        with open(os.path.join(target, "AGENTS.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- AEH:BEGIN MANAGED -->\nduplicate\n")
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "adapter.agents_managed")["status"], "BLOCKED")

    def test_malformed_claude_managed(self):
        target = self.make_healthy()
        with open(os.path.join(target, "CLAUDE.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- AEH:END MANAGED -->\norphan end\n")
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "adapter.claude_managed")["status"], "BLOCKED")


class TestCapabilities(DoctorBase):
    def test_guidance_only_warns(self):
        target = self.make_healthy()
        result = doc.run_doctor(target)
        statuses = [self.check(result, "adapter.codex.capabilities")["status"],
                    self.check(result, "adapter.claude.capabilities")["status"]]
        self.assertIn("WARN", statuses)
        self.assertIn(result["overall"], ("READY_WITH_WARNINGS",))

    def test_unenforceable_blocks(self):
        target = self.make_healthy()
        overrides = {"codex": {"permissions.web_access": {"status": "UNENFORCEABLE"}}}
        result = doc.run_doctor(target, capability_overrides=overrides)
        self.assertEqual(self.check(result, "adapter.codex.capabilities")["status"], "BLOCKED")
        self.assertEqual(result["overall"], "BLOCKED")


class TestPrivateAndEnv(DoctorBase):
    def test_private_gitignore_missing_entry(self):
        target = self.make_healthy()
        with open(os.path.join(target, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("__pycache__/\n")
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "private.gitignore")["status"], "BLOCKED")

    def test_no_gitignore_warns(self):
        target = self.make_healthy()
        os.remove(os.path.join(target, ".gitignore"))
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "private.gitignore")["status"], "WARN")

    def test_private_content_not_in_evidence(self):
        target = self.make_healthy()
        os.makedirs(os.path.join(target, ".aeh", "private"), exist_ok=True)
        with open(os.path.join(target, ".aeh", "private", "secret.txt"), "w", encoding="utf-8") as f:
            f.write("SECRET-TOKEN-123")
        result = doc.run_doctor(target)
        serialized = json.dumps(result, default=str)
        self.assertNotIn("SECRET-TOKEN-123", serialized)

    def test_staging_residue_blocks(self):
        target = self.make_healthy()
        with open(os.path.join(target, ".aeh", "manifest.yaml.aeh-tmp"), "w", encoding="utf-8") as f:
            f.write("partial")
        result = doc.run_doctor(target)
        self.assertEqual(self.check(result, "install.staging_residue")["status"], "BLOCKED")
        self.assertIn("BLOCKED_INCOMPLETE_INSTALL", self.check(result, "install.staging_residue")["message"])

    def test_git_unavailable_honest(self):
        target = self.make_healthy()
        result = doc.run_doctor(target, which=lambda name: None)
        self.assertEqual(self.check(result, "env.git")["status"], "WARN")
        self.assertIn("UNKNOWN_ENVIRONMENT", self.check(result, "env.git")["message"])


class TestDeterminismAndPreflight(DoctorBase):
    def test_twice_semantic_deterministic(self):
        target = self.make_healthy()
        r1 = doc.run_doctor(target)
        r2 = doc.run_doctor(target)
        self.assertEqual(r1["checks"], r2["checks"])
        self.assertEqual(r1["overall"], r2["overall"])

    def test_scanned_at_irrelevant(self):
        target = self.make_healthy()
        r1 = doc.run_doctor(target, now=None)
        r2 = doc.run_doctor(target, now=None)
        r1["scanned_at"] = "2026-01-01T00:00:00+00:00"
        r2["scanned_at"] = "2030-01-01T00:00:00+00:00"
        self.assertEqual(r1["checks"], r2["checks"])
        self.assertEqual(r1["overall"], r2["overall"])

    def test_preflight_propagates(self):
        target = self.make_healthy()
        healthy = doc.run_doctor(target)
        pre = doc.runtime_preflight(healthy)
        self.assertIn(pre["verdict"], ("READY", "READY_WITH_WARNINGS"))
        if healthy["overall"] == "READY_WITH_WARNINGS":
            self.assertGreater(len(pre["warnings"]), 0)
        # 制造 BLOCKED 后 preflight 必须 BLOCKED 且携带 blocking checks
        os.remove(os.path.join(target, ".aeh", "manifest.yaml"))
        broken = doc.run_doctor(target)
        pre2 = doc.runtime_preflight(broken)
        self.assertEqual(pre2["verdict"], "BLOCKED")
        self.assertGreater(len(pre2["blocking_checks"]), 0)


class TestCLI(unittest.TestCase):
    def test_cli_doctor(self):
        import subprocess
        target = tempfile.mkdtemp(prefix="aeh-doc-cli-")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src")
        r = subprocess.run([sys.executable, "-m", "aeh.cli", "doctor", target],
                           capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r.returncode, 1)  # 未安装 → BLOCKED → exit 1
        self.assertIn("BLOCKED", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh")))


if __name__ == "__main__":
    unittest.main(verbosity=2)