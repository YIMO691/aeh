"""AEH Phase 11 — Test Design + RED 测试

覆盖 spec 27 项（合理合并）。
"""
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp
from aeh.runtime import change as ch
from aeh.runtime import grounding as gr
from aeh.runtime import specification as sp
from aeh.runtime import test_design as td
from aeh.runtime import red as rmod

TDD_REPO = os.path.join(ROOT, "tests", "fixtures", "tdd-repo")
TDD_SRC = os.path.join(ROOT, "tests", "fixtures", "tdd-src")


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-r-answers-")
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


def make_target(src=TDD_REPO):
    target = tempfile.mkdtemp(prefix="aeh-r-target-")
    if src:
        shutil.copytree(src, target, dirs_exist_ok=True)
    report = bp.bootstrap(target, answers_path(), dry_run=False)
    assert report["status"] == "BOOTSTRAP_COMPLETE", report
    return target


def write_yaml(tmpdir, name, body):
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(body, f, sort_keys=True, allow_unicode=True)
    return p


def reqs_body(ac_type="invariant"):
    return {"requirements": [{"behavior": "重复请求最多产生一次奖励副作用",
                               "acceptance": [{"type": ac_type, "statement": "相同请求执行两次，奖励副作用最多一次"}]}]}


def plan_body(src="claim_test.py", signature="duplicate_reward", extra=None, verify="AC-001-01", required=True):
    t = {"id": "TEST-001", "verifies": [verify], "kind": "integration",
         "intent": "重复执行同一领取请求，验证奖励副作用最多一次",
         "command": "python tests/test_claim.py",
         "expected_before_fix": {"type": "behavior_failure", "signature": signature},
         "required": required}
    if extra:
        t.update(extra)
    return {"tests": [t], "test_files": [{"src": src, "dest": "tests/test_claim.py"}]}


def run_full(target, title="修复重复领取逻辑", reqs=None, plan=None, test_src=TDD_SRC):
    tmp = tempfile.mkdtemp(prefix="aeh-r-files-")
    r = ch.change_new(target, title, suggested_level="STANDARD")
    assert r["status"] == "CHANGE_CREATED", r
    cid = r["change_id"]
    g = gr.change_ground(target, cid)
    assert g["status"] == "GROUNDING_COMPLETE", g
    reqs_p = write_yaml(tmp, "reqs.yaml", reqs or reqs_body())
    s = sp.build_spec(target, cid, reqs_path=reqs_p)
    assert s["status"] == "SPEC_COMPLETE", s
    plan_p = write_yaml(tmp, "plan.yaml", plan or plan_body())
    td_rep = td.change_test_design(target, cid, plan_p, test_src=test_src)
    return cid, td_rep


class TestDesignTests(unittest.TestCase):
    def test_spec_gate_block(self):
        target = make_target()
        r = ch.change_new(target, "修复重复领取逻辑", suggested_level="STANDARD")
        gr.change_ground(target, r["change_id"])
        rep = td.change_test_design(target, r["change_id"], write_yaml(tempfile.mkdtemp(), "p.yaml", plan_body()))
        self.assertIn(rep["status"], ("BLOCKED_CHANGE_STATE", "BLOCKED_SPEC_GATE"))

    def test_standard_test_design_pass(self):
        target = make_target()
        cid, rep = run_full(target)
        self.assertEqual(rep["status"], "TEST_DESIGN_COMPLETE", rep)
        change = ch.load_change(target, cid)
        self.assertEqual(change["gates"].get("test_design"), "PASS")
        self.assertEqual(change["state"]["current"], "TEST_DESIGN")
        self.assertTrue(os.path.isfile(os.path.join(target, "tests", "test_claim.py")))

    def test_ac_coverage_missing_block(self):
        target = make_target()
        cid, _ = run_full(target, plan=plan_body(verify="AC-999-99"))
        # run_full 内 test-design 会返回 BLOCKED_INVALID_AC_REFERENCE
        rep = td.change_test_design(target, cid, write_yaml(tempfile.mkdtemp(), "p.yaml", plan_body(verify="AC-999-99")), test_src=TDD_SRC)
        self.assertEqual(rep["status"], "BLOCKED_INVALID_AC_REFERENCE")

    def test_manual_ac_not_forced(self):
        target = make_target()
        reqs = {"requirements": [{"behavior": "B", "failure_behavior": "由人工检查保障", "acceptance": [{"type": "manual", "statement": "人工检查"}]}]}
        cid, rep = run_full(target, reqs=reqs)
        self.assertEqual(rep["status"], "TEST_DESIGN_COMPLETE")

    def test_critical_invariant_uncovered_block(self):
        target = make_target()
        r = ch.change_new(target, "修复重复领取奖励")
        cid = r["change_id"]
        gr.change_ground(target, cid)
        sp.build_spec(target, cid, reqs_path=write_yaml(tempfile.mkdtemp(), "r.yaml", reqs_body("automated")))
        # CRITICAL：automated AC 被覆盖，但 critical invariant 要求… 此处用 automated AC 的 spec 无法满足 CRITICAL spec 规则，改用 invariant AC + 无测试覆盖
        sp.build_spec(target, cid, reqs_path=write_yaml(tempfile.mkdtemp(), "r2.yaml", reqs_body("invariant")))
        uncovered_plan = {"tests": [{"id": "TEST-001", "kind": "unit", "intent": "x", "command": "python tests/test_claim.py", "expected_before_fix": {"type": "behavior_failure", "signature": "duplicate_reward"}, "required": True}], "test_files": [{"src": "claim_test.py", "dest": "tests/test_claim.py"}]}
        rep = td.change_test_design(target, cid, write_yaml(tempfile.mkdtemp(), "p.yaml", uncovered_plan), test_src=TDD_SRC)
        self.assertEqual(rep["status"], "TEST_DESIGN_INCOMPLETE")

    def test_stable_test_ids(self):
        target = make_target()
        cid, _ = run_full(target)
        rep2 = td.change_test_design(target, cid, write_yaml(tempfile.mkdtemp(), "p.yaml", plan_body()), test_src=TDD_SRC)
        self.assertEqual(rep2["status"], "TEST_DESIGN_COMPLETE")
        plan = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "test-plan.yaml"), encoding="utf-8"))
        self.assertEqual(plan["tests"][0]["id"], "TEST-001")

    def test_test_creation_not_modify_production(self):
        target = make_target()
        before = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        cid, _ = run_full(target)
        after = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        self.assertEqual(before, after)

    def test_plan_schema_pass(self):
        target = make_target()
        cid, _ = run_full(target)
        plan = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "test-plan.yaml"), encoding="utf-8"))
        schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", "test-plan.schema.json"), encoding="utf-8"))
        jsonschema.validate(plan, schema)


class TestRed(unittest.TestCase):
    def _to_red(self, plan=None, test_src=TDD_SRC, reqs=None):
        target = make_target()
        cid, td_rep = run_full(target, reqs=reqs)
        if td_rep["status"] != "TEST_DESIGN_COMPLETE":
            return target, cid, td_rep
        if plan:
            td.change_test_design(target, cid, write_yaml(tempfile.mkdtemp(), "p.yaml", plan), test_src=test_src)
        return target, cid, td_rep

    def test_valid_red_and_lock(self):
        target, cid, _ = self._to_red()
        rep = rmod.change_red(target, cid)
        self.assertEqual(rep["status"], "RED_COMPLETE", rep)
        self.assertEqual(rep["verdicts"], ["VALID_RED"])
        change = ch.load_change(target, cid)
        self.assertEqual(change["state"]["current"], "LOCK_TEST")
        self.assertEqual(change["gates"].get("red"), "PASS")
        self.assertNotEqual(change["state"]["current"], "GREEN")
        red_rec = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "red.yaml"), encoding="utf-8"))
        self.assertTrue(red_rec["tests"][0]["output_ref"])
        self.assertRegex(red_rec["tests"][0]["output_hash"], "^[0-9a-fA-F]{64}$")
        lock = yaml.safe_load(open(os.path.join(target, ".aeh", "changes", cid, "test-lock.yaml"), encoding="utf-8"))
        self.assertGreater(len(lock["files"]), 0)

    def test_crash_is_unexpected_failure(self):
        target, cid, _ = self._to_red(plan=plan_body(src="crash_test.py"))
        rep = rmod.change_red(target, cid)
        self.assertEqual(rep["status"], "RED_INVALID")
        self.assertIn("INVALID_RED_UNEXPECTED_FAILURE", rep["routes"])
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", cid, "test-lock.yaml")))

    def test_fixture_route(self):
        target, cid, _ = self._to_red(plan=plan_body(src="fixture_test.py", extra={"fixture_signatures": ["fixture_missing"]}))
        rep = rmod.change_red(target, cid)
        self.assertIn("INVALID_RED_FIXTURE", rep["routes"])

    def test_environment_route(self):
        target, cid, _ = self._to_red(plan=plan_body(src="env_test.py"))
        rep = rmod.change_red(target, cid)
        self.assertIn("INVALID_RED_ENVIRONMENT", rep["routes"])

    def test_test_defect_route(self):
        target, cid, _ = self._to_red(plan=plan_body(src="defect_test.py", extra={"test_defect_signatures": ["test_defect_marker"]}))
        rep = rmod.change_red(target, cid)
        self.assertIn("INVALID_RED_TEST_DEFECT", rep["routes"])

    def test_spec_mismatch_route(self):
        target, cid, _ = self._to_red(plan=plan_body(src="specmismatch_test.py", extra={"spec_mismatch_signatures": ["spec_mismatch_marker"]}))
        rep = rmod.change_red(target, cid)
        self.assertIn("INVALID_RED_SPEC_MISMATCH", rep["routes"])

    def test_already_green(self):
        target, cid, _ = self._to_red(plan=plan_body(src="green_test.py"))
        rep = rmod.change_red(target, cid)
        self.assertEqual(rep["status"], "NO_RED_ALREADY_GREEN")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", cid, "test-lock.yaml")))

    def test_invalid_red_lock_unreachable(self):
        target, cid, _ = self._to_red(plan=plan_body(src="crash_test.py"))
        rep = rmod.change_red(target, cid)
        self.assertEqual(rep["status"], "RED_INVALID")
        change = ch.load_change(target, cid)
        self.assertEqual(change["state"]["current"], "RED")
        tr = ch.change_transition(target, cid, "LOCK_TEST", condition="VALID_RED")
        self.assertEqual(tr["status"], "BLOCKED_GATE_UNSATISFIED")

    def test_stale_blocks_red(self):
        target, cid, _ = self._to_red()
        with open(os.path.join(target, "src", "reward.py"), "a", encoding="utf-8") as f:
            f.write("# changed\n")
        rep = rmod.change_red(target, cid)
        self.assertEqual(rep["status"], "BLOCKED_STALE_EVIDENCE")

    def test_production_byte_for_byte(self):
        target, cid, _ = self._to_red()
        before = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        rmod.change_red(target, cid)
        after = hashlib.sha256(open(os.path.join(target, "src", "reward.py"), "rb").read()).hexdigest()
        self.assertEqual(before, after)

    def test_parallel_changes_isolated(self):
        target = make_target()
        cid1, _ = run_full(target)
        r2 = ch.change_new(target, "奖励领取流程优化")
        self.assertEqual(r2["status"], "CHANGE_CREATED")
        rep = rmod.change_red(target, cid1)
        self.assertEqual(rep["status"], "RED_COMPLETE")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", r2["change_id"], "test-plan.yaml")))


if __name__ == "__main__":
    unittest.main(verbosity=2)