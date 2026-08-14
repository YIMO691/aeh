"""AEH Phase 12 — GREEN + Refactor 测试

覆盖 spec 27 项（合理合并）。
"""
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr
from aeh.runtime import specification as sp
from aeh.runtime import test_design as td
from aeh.runtime import red as rmod
from aeh.runtime import green as gmod

TDD_REPO = os.path.join(ROOT, "tests", "fixtures", "tdd-repo")
TDD_SRC = os.path.join(ROOT, "tests", "fixtures", "tdd-src")


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-g12-a-")
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


def write_yaml(tmpdir, name, body):
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(body, f, sort_keys=True, allow_unicode=True)
    return p


def reqs_body():
    return {"requirements": [{"behavior": "重复请求最多产生一次奖励副作用",
                               "acceptance": [{"type": "invariant", "statement": "相同请求执行两次，奖励副作用最多一次"}]}]}


def plan_body():
    return {"tests": [{"id": "TEST-001", "verifies": ["AC-001-01"], "kind": "integration",
                        "intent": "重复执行同一领取请求，验证奖励副作用最多一次",
                        "command": "python tests/test_claim.py",
                        "expected_before_fix": {"type": "behavior_failure", "signature": "duplicate_reward"},
                        "required": True}],
            "test_files": [{"src": "claim_test.py", "dest": "tests/test_claim.py"}],
            "regression": []}


def to_lock(target, title="修复重复领取逻辑"):
    files_tmp = tempfile.mkdtemp(prefix="aeh-g12-f-")
    r = ch.change_new(target, title, suggested_level="STANDARD")
    assert r["status"] == "CHANGE_CREATED", r
    cid = r["change_id"]
    assert gr.change_ground(target, cid)["status"] == "GROUNDING_COMPLETE"
    assert sp.build_spec(target, cid, reqs_path=write_yaml(files_tmp, "reqs.yaml", reqs_body()))["status"] == "SPEC_COMPLETE"
    assert td.change_test_design(target, cid, write_yaml(files_tmp, "plan.yaml", plan_body()), test_src=TDD_SRC)["status"] == "TEST_DESIGN_COMPLETE"
    assert rmod.change_red(target, cid)["status"] == "RED_COMPLETE"
    return cid


def apply_fix(target):
    fixed = open(os.path.join(TDD_SRC, "reward_fixed.py"), encoding="utf-8").read()
    before = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
    with open(os.path.join(target, "src", "reward.py"), "w", encoding="utf-8") as f:
        f.write(fixed)
    after = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
    return before, after


def scope_manifest(tmpdir, changed_files, allowed_paths=None):
    body = {"changed_files": changed_files,
            "allowed_paths": allowed_paths or [cf["path"] for cf in changed_files]}
    return write_yaml(tmpdir, "scope.yaml", body)


def make_target(src=TDD_REPO):
    target = tempfile.mkdtemp(prefix="aeh-g12-t-")
    shutil.copytree(src, target, dirs_exist_ok=True)
    assert bp.bootstrap(target, answers_path(), dry_run=False)["status"] == "BOOTSTRAP_COMPLETE"
    return target


class TestGreen(unittest.TestCase):
    def test_green_full_flow(self):
        target = make_target()
        cid = to_lock(target)
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "GREEN_COMPLETE", rep)
        change = ch.load_change(target, cid)
        self.assertEqual(change["state"]["current"], "GREEN")
        ev = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "green.yaml"), encoding="utf-8"))
        self.assertEqual(ev["verdict"], "GREEN_PASS")
        self.assertGreater(len(ev["changed_files"]), 0)
        self.assertTrue(ev["changed_files"][0]["code_id"].startswith("CODE-"))

    def test_precondition_blocked_without_lock(self):
        target = make_target()
        r = ch.change_new(target, "修复重复领取逻辑", suggested_level="STANDARD")
        rep = gmod.change_green(target, r["change_id"])
        self.assertNotIn(rep["status"], ("GREEN_COMPLETE",))

    def test_test_changed_blocked(self):
        target = make_target()
        cid = to_lock(target)
        with open(os.path.join(target, "tests", "test_claim.py"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "BLOCKED_TEST_CHANGED")

    def test_spec_changed_blocked(self):
        target = make_target()
        cid = to_lock(target)
        with open(os.path.join(target, ".aeh", "changes", cid, "spec.yaml"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        rep = gmod.change_green(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_RUNTIME_CONTEXT_STALE")

    def test_runtime_tamper_blocked(self):
        target = make_target()
        cid = to_lock(target)
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# t\n")
        rep = gmod.change_green(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_DOCTOR")

    def test_scope_violation(self):
        target = make_target()
        cid = to_lock(target)
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/other.py", "before_hash": before, "after_hash": after}],
                                                    allowed_paths=["src/mail.py"]))
        self.assertEqual(rep["status"], "BLOCKED_SCOPE_VIOLATION")

    def test_red_green_pairing(self):
        target = make_target()
        cid = to_lock(target)
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "GREEN_COMPLETE")
        ev = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "green.yaml"), encoding="utf-8"))
        self.assertEqual(ev["tests"][0]["test_id"], "TEST-001")
        self.assertEqual(ev["tests"][0]["exit_code"], 0)

    def test_stale_external_mutation(self):
        target = make_target()
        cid = to_lock(target)
        with open(os.path.join(target, "src", "mail.py"), "a", encoding="utf-8") as f:
            f.write("# external\n")
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "BLOCKED_RUNTIME_CONTEXT_STALE")

    def test_own_mutation_not_stale(self):
        # src/reward.py 在 changed scope 内，不应误判 stale
        target = make_target()
        cid = to_lock(target)
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "GREEN_COMPLETE", rep)

    def test_cwd_escape_rejected(self):
        target = make_target()
        self.assertIsNone(gmod._resolve_cwd(target, ".."))
        self.assertIsNone(gmod._resolve_cwd(target, os.path.abspath(os.path.join(target, ".."))))

    def test_timeout_enforced(self):
        target = make_target()
        code, out, _ = gmod.run_execution(target, {"argv": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout_seconds": 1})
        self.assertEqual(code, 124)

    def test_refactor_flow(self):
        target = make_target()
        cid = to_lock(target)
        before, after = apply_fix(target)
        assert gmod.change_green(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))["status"] == "GREEN_COMPLETE"
        # refactor：再改一次同文件（结构等价）
        ref = "# 奖励领取逻辑\nrewards = {}\n\ndef claim(mail_id):\n    if mail_id not in rewards:\n        rewards[mail_id] = 100\n    return rewards[mail_id]\n\ndef side_effect_count():\n    return len(rewards)\n"
        b2 = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        with open(os.path.join(target, "src", "reward.py"), "w", encoding="utf-8") as f:
            f.write(ref)
        a2 = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        rep = gmod.change_refactor(target, cid, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": b2, "after_hash": a2}]))
        self.assertEqual(rep["status"], "REFACTOR_COMPLETE", rep)
        change = ch.load_change(target, cid)
        self.assertEqual(change["state"]["current"], "REFACTOR")

    def test_refactor_unreachable_before_green(self):
        target = make_target()
        cid = to_lock(target)
        rep = gmod.change_refactor(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_CHANGE_STATE")

    def test_parallel_changes_isolated(self):
        target = make_target()
        cid1 = to_lock(target)
        r2 = ch.change_new(target, "奖励领取流程优化")
        before, after = apply_fix(target)
        rep = gmod.change_green(target, cid1, scope_path=scope_manifest(tempfile.mkdtemp(),
                                                    [{"path": "src/reward.py", "before_hash": before, "after_hash": after}]))
        self.assertEqual(rep["status"], "GREEN_COMPLETE")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", r2["change_id"], "green.yaml")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
