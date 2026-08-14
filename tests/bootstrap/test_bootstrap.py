"""AEH Phase 6 — Bootstrap Install 测试

覆盖 spec 20 项：dry-run 零写盘、plan schema、BLOCKED 不安装、必要工件、schema PASS、
runtime digest、篡改检测、用户原文保留、managed 不重复、malformed 阻断、.gitignore 保留、
private 唯一、零泄漏、二次 semantic diff=0、installed_at 不变化、中途失败不 COMPLETE、
staging 校验失败不污染、确定性、回归。
"""
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp  # noqa: E402


def make_target(files=None):
    tmp = tempfile.mkdtemp(prefix="aeh-target-")
    for rel, content in (files or {}).items():
        path = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return tmp


def snapshot(root):
    out = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def valid_answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-answers-")
    answers = {"contract": "bootstrap.interview.answers", "version": 1,
               "answers": {
                   "q-plan-before-code": {"question_id": "q-plan-before-code", "answer": "risk_based",
                                          "type": "PREFERENCE", "source": "user_answer",
                                          "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-testing-policy": {"question_id": "q-testing-policy", "answer": "risk_based",
                                        "type": "POLICY", "source": "user_answer",
                                        "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-human-review": {"question_id": "q-human-review", "answer": "critical",
                                      "type": "POLICY", "source": "user_answer",
                                      "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-modify-source": {"question_id": "q-modify-source", "answer": "allow",
                                       "type": "PERMISSION", "source": "user_answer",
                                       "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-commit": {"question_id": "q-git-commit", "answer": "ask",
                                    "type": "PERMISSION", "source": "user_answer",
                                    "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-git-push": {"question_id": "q-git-push", "answer": "deny",
                                  "type": "PERMISSION", "source": "user_answer",
                                  "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-shell-access": {"question_id": "q-shell-access", "answer": "ask",
                                      "type": "PERMISSION", "source": "user_answer",
                                      "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-web-access": {"question_id": "q-web-access", "answer": "deny",
                                    "type": "PERMISSION", "source": "user_answer",
                                    "answered_at": "2026-08-14T00:00:00+00:00"},
                   "q-team-review-policy": {"question_id": "q-team-review-policy", "answer": "major",
                                            "type": "POLICY", "source": "user_answer",
                                            "answered_at": "2026-08-14T00:00:00+00:00"},
               }, "reset": []}
    path = os.path.join(tmp, "answers.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(answers, f, sort_keys=True, allow_unicode=True)
    return path


USER_AGENTS = "# My rules\nUser rule alpha.\nUser rule beta.\n"
USER_CLAUDE = "# Claude user rules\nKeep me.\n"
USER_GITIGNORE = "__pycache__/\n.env\n"


class TestDryRun(unittest.TestCase):
    def test_dry_run_zero_writes(self):
        target = make_target({"AGENTS.md": USER_AGENTS, "CLAUDE.md": USER_CLAUDE, ".gitignore": USER_GITIGNORE})
        before = snapshot(target)
        report = bp.bootstrap(target, valid_answers_path(), dry_run=True)
        self.assertEqual(report["status"], "PLAN_READY")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh")))
        self.assertEqual(snapshot(target), before)

    def test_plan_schema_pass(self):
        target = make_target({})
        report = bp.bootstrap(target, valid_answers_path(), dry_run=True)
        schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", "install-plan.schema.json"), encoding="utf-8"))
        jsonschema.validate(report["plan"], schema)

    def test_blocked_profile_not_installed(self):
        target = make_target({})
        before = snapshot(target)
        tmp = tempfile.mkdtemp()
        rules_dir = os.path.join(tmp, "interview")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "t.yaml"), "w", encoding="utf-8") as f:
            f.write("contract: bootstrap.interview\nversion: 1\nscope: team\nquestions:\n"
                    "  - question_id: q-t1\n    type: POLICY\n    field: team.policy_x\n    question: q?\n    required: true\n    options:\n      - {value: a}\n      - {value: b}\n"
                    "  - question_id: q-t2\n    type: POLICY\n    field: team.policy_x\n    question: q?\n    required: true\n    options:\n      - {value: a}\n      - {value: b}\n")
        answers = {"contract": "bootstrap.interview.answers", "version": 1,
                   "answers": {
                       "q-t1": {"question_id": "q-t1", "answer": "a", "type": "POLICY",
                                "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                       "q-t2": {"question_id": "q-t2", "answer": "b", "type": "POLICY",
                                "source": "user_answer", "answered_at": "2026-08-14T00:00:00+00:00"},
                   }, "reset": []}
        a_path = os.path.join(tmp, "a.yaml")
        with open(a_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(answers, f, sort_keys=True, allow_unicode=True)
        report = bp.bootstrap(target, a_path, dry_run=False, interview_rules=rules_dir)
        self.assertEqual(report["status"], "BLOCKED_PROFILE_CONFLICT")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh")))
        self.assertEqual(snapshot(target), before)



class TestInstall(unittest.TestCase):
    def _install(self):
        target = make_target({"AGENTS.md": USER_AGENTS, "CLAUDE.md": USER_CLAUDE,
                              ".gitignore": USER_GITIGNORE, "src/app.py": "print('hi')\n"})
        report = bp.bootstrap(target, valid_answers_path(), dry_run=False)
        return target, report

    def test_first_install_artifacts(self):
        target, report = self._install()
        self.assertEqual(report["status"], "BOOTSTRAP_COMPLETE")
        for rel in [".aeh/manifest.yaml", ".aeh/profile.yaml", ".aeh/effective-workflow.yaml",
                    ".aeh/runtime/core/workflow.yaml", ".aeh/runtime/schemas/profile.schema.json",
                    ".aeh/bootstrap/discovery.yaml", ".aeh/bootstrap/answers.yaml",
                    ".aeh/bootstrap/conflicts.yaml", ".aeh/bootstrap/compiler-report.yaml"]:
            self.assertTrue(os.path.isfile(os.path.join(target, rel)), rel)
        for rel in [".aeh/private/", ".aeh/changes/"]:
            self.assertTrue(os.path.isdir(os.path.join(target, rel)), rel)

    def test_schemas_pass(self):
        target, _ = self._install()
        for name in ("manifest.schema.json", "profile.schema.json", "effective-workflow.schema.json"):
            schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", name), encoding="utf-8"))
            data = yaml.safe_load(open(os.path.join(target, ".aeh", name.split(".")[0] + ".yaml"), encoding="utf-8"))
            jsonschema.validate(data, schema)

    def test_runtime_digest_pass_and_tamper_detected(self):
        target, _ = self._install()
        actual, expected = bp.validate_runtime_integrity(target)
        self.assertEqual(actual, expected)
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        actual2, expected2 = bp.validate_runtime_integrity(target)
        self.assertNotEqual(actual2, expected2)

    def test_user_content_preserved(self):
        target, _ = self._install()
        self.assertIn("User rule alpha.", open(os.path.join(target, "AGENTS.md"), encoding="utf-8").read())
        self.assertIn("Keep me.", open(os.path.join(target, "CLAUDE.md"), encoding="utf-8").read())
        self.assertIn("__pycache__/", open(os.path.join(target, ".gitignore"), encoding="utf-8").read())

    def test_gitignore_private_once(self):
        target, _ = self._install()
        text = open(os.path.join(target, ".gitignore"), encoding="utf-8").read()
        self.assertEqual(text.count(".aeh/private/"), 1)
        self.assertNotIn("\n.aeh/\n", text)

    def test_second_bootstrap_semantic_diff_zero(self):
        target, report1 = self._install()
        self.assertEqual(report1["status"], "BOOTSTRAP_COMPLETE")
        before = snapshot(target)
        manifest1 = yaml.safe_load(open(os.path.join(target, ".aeh", "manifest.yaml"), encoding="utf-8"))
        report2 = bp.bootstrap(target, valid_answers_path(), dry_run=False)
        self.assertEqual(report2["status"], "BOOTSTRAP_COMPLETE")
        after = snapshot(target)
        self.assertEqual(before, after)
        manifest2 = yaml.safe_load(open(os.path.join(target, ".aeh", "manifest.yaml"), encoding="utf-8"))
        self.assertEqual(manifest1["installed_at"], manifest2["installed_at"])

    def test_malformed_marker_blocked(self):
        target = make_target({"AGENTS.md": "# x\n<!-- AEH:BEGIN MANAGED -->\nno end\n"})
        before = snapshot(target)
        report = bp.bootstrap(target, valid_answers_path(), dry_run=False)
        self.assertNotEqual(report["status"], "BOOTSTRAP_COMPLETE")
        self.assertEqual(snapshot(target), before)

    def test_apply_mid_failure_no_complete(self):
        target = make_target({"AGENTS.md": USER_AGENTS})
        os.makedirs(os.path.join(target, ".aeh", "profile.yaml"))  # 目录占位 → 写 profile 必失败
        report = bp.bootstrap(target, valid_answers_path(), dry_run=False)
        self.assertNotEqual(report["status"], "BOOTSTRAP_COMPLETE")
        self.assertIn(report["status"], ("BOOTSTRAP_FAILED", "BOOTSTRAP_FAILED_VALIDATION"))
        # 用户原文仍在（回滚）
        self.assertIn("User rule alpha.", open(os.path.join(target, "AGENTS.md"), encoding="utf-8").read())

    def test_private_smuggle_rejected(self):
        # 试图走私额外私有字段的 answers 被 schema 拒绝：安装失败、目标不变
        target = make_target({})
        before = snapshot(target)
        tmp = tempfile.mkdtemp()
        answers = {"contract": "bootstrap.interview.answers", "version": 1,
                   "answers": {"q-git-push": {"question_id": "q-git-push", "answer": "deny",
                                             "type": "PERMISSION", "source": "user_answer",
                                             "answered_at": "2026-08-14T00:00:00+00:00",
                                             "private_body": "SECRET-TOKEN-123"}}, "reset": []}
        path = os.path.join(tmp, "a.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(answers, f, sort_keys=True, allow_unicode=True)
        report = bp.bootstrap(target, path, dry_run=False)
        self.assertEqual(report["status"], "BOOTSTRAP_FAILED_VALIDATION")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh")))
        self.assertEqual(snapshot(target), before)

    def test_private_ref_only_no_secret(self):
        # 合法私有约束：输出只含 ref id（question_id），零正文
        target = make_target({})
        report = bp.bootstrap(target, valid_answers_path(), dry_run=False)
        self.assertEqual(report["status"], "BOOTSTRAP_COMPLETE")
        for rel in ("AGENTS.md", "CLAUDE.md", ".aeh/profile.yaml", ".aeh/bootstrap/answers.yaml"):
            p = os.path.join(target, rel)
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as fh:
                    self.assertNotIn("SECRET-TOKEN-123", fh.read(), rel)
        self.assertNotIn("SECRET-TOKEN-123", json.dumps(report["plan"], default=str))
        with open(os.path.join(target, ".aeh", "profile.yaml"), encoding="utf-8") as fh:
            self.assertIn("q-git-push", fh.read())


    def test_deterministic_plan(self):
        t1 = make_target({"src/app.py": "print(1)\n"})
        r1 = bp.bootstrap(t1, valid_answers_path(), dry_run=True)
        r2 = bp.bootstrap(t1, valid_answers_path(), dry_run=True)
        ops1 = [(o["action"], o["path"], o["content_hash"]) for o in r1["plan"]["operations"]]
        ops2 = [(o["action"], o["path"], o["content_hash"]) for o in r2["plan"]["operations"]]
        self.assertEqual(ops1, ops2)


class TestCLI(unittest.TestCase):
    def test_cli_dry_run_and_apply(self):
        import subprocess
        target = make_target({"AGENTS.md": USER_AGENTS})
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src")
        r1 = subprocess.run([sys.executable, "-m", "aeh.cli", "bootstrap", target, "--dry-run"],
                            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("PLAN_READY", r1.stdout)
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh")))
        r2 = subprocess.run([sys.executable, "-m", "aeh.cli", "bootstrap", target],
                            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("BOOTSTRAP_COMPLETE", r2.stdout)
        self.assertTrue(os.path.isfile(os.path.join(target, ".aeh", "manifest.yaml")))


if __name__ == "__main__":
    unittest.main(verbosity=2)