"""AEH Phase 8 — Change Workflow Shell 测试

覆盖 spec 17 项：preflight 前置、ID 不覆盖、五级分类、hard escalation、reasons/evidence、
每 Change 独立、合法/非法迁移、gate 阻断、digest 篡改阻断、warnings 继承、
无 global current-change、schema PASS、CLI 只读、关键词检测。
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.bootstrap import pipeline as bp
from aeh.doctor import doctor as doc
from aeh.runtime import change as ch
from aeh.runtime import classify as cls
from aeh.runtime import coordination as coord


def answers_path():
    tmp = tempfile.mkdtemp(prefix="aeh-ch-answers-")
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


def make_healthy():
    target = tempfile.mkdtemp(prefix="aeh-ch-target-")
    with open(os.path.join(target, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("__pycache__/\n")
    report = bp.bootstrap(target, answers_path(), dry_run=False)
    assert report["status"] == "BOOTSTRAP_COMPLETE", report
    return target


class TestChangeCreate(unittest.TestCase):
    def test_create_healthy(self):
        target = make_healthy()
        report = ch.change_new(target, "添加一个普通注释", suggested_level="DIRECT")
        self.assertEqual(report["status"], "CHANGE_CREATED")
        self.assertTrue(os.path.isfile(os.path.join(target, ".aeh", "changes", report["change_id"], "change.yaml")))

    def test_blocked_preflight_no_change(self):
        target = make_healthy()
        os.remove(os.path.join(target, ".aeh", "manifest.yaml"))
        before = set(os.listdir(os.path.join(target, ".aeh", "changes")))
        report = ch.change_new(target, "任务")
        self.assertEqual(report["status"], "BLOCKED_PREFLIGHT")
        self.assertEqual(set(os.listdir(os.path.join(target, ".aeh", "changes"))), before)

    def test_id_allocation_no_overwrite(self):
        target = make_healthy()
        r1 = ch.change_new(target, "任务A", suggested_level="DIRECT")
        r2 = ch.change_new(target, "任务B", suggested_level="DIRECT")
        self.assertEqual(r1["change_id"], "CHG-2026-0003")
        self.assertEqual(r2["change_id"], "CHG-2026-0004")
        os.makedirs(os.path.join(target, ".aeh", "changes", "CHG-2026-0009"), exist_ok=True)
        r3 = ch.change_new(target, "任务C", suggested_level="DIRECT")
        self.assertEqual(r3["change_id"], "CHG-2026-0010")

    def test_warnings_inherited(self):
        target = make_healthy()
        report = ch.change_new(target, "任务", suggested_level="DIRECT")
        change = ch.load_change(target, report["change_id"])
        self.assertGreater(len(change.get("preflight_warnings", [])), 0)

    def test_no_global_current_change(self):
        target = make_healthy()
        ch.change_new(target, "任务", suggested_level="DIRECT")
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "current-change.yaml")))
        self.assertFalse(os.path.exists(os.path.join(target, ".aeh", "changes", "current")))

    def test_change_schema_pass(self):
        target = make_healthy()
        report = ch.change_new(target, "任务", suggested_level="DIRECT")
        change = ch.load_change(target, report["change_id"])
        schema = yaml.safe_load(open(os.path.join(ROOT, "schemas", "change.schema.json"), encoding="utf-8"))
        jsonschema.validate(change, schema)


class TestClassification(unittest.TestCase):
    def test_five_levels(self):
        for level in ("DIRECT", "LIGHTWEIGHT", "STANDARD", "CRITICAL", "EXPLORE"):
            c = cls.classify("t", suggested_level=level, hits=[])
            self.assertEqual(c["level"], level)

    def test_hard_escalation_overrides_suggestion(self):
        c = cls.classify("t", suggested_level="LIGHTWEIGHT", hits=["money_economy"])
        self.assertEqual(c["level"], "CRITICAL")
        self.assertTrue(c["escalated"])

    def test_all_eight_domains(self):
        contract = cls.load_classification_contract()
        for domain in contract["hard_escalation"]["domains"]:
            c = cls.classify("t", suggested_level="DIRECT", hits=[domain])
            self.assertEqual(c["level"], "CRITICAL", domain)

    def test_reasons_evidence_saved(self):
        target = make_healthy()
        report = ch.change_new(target, "修复重复领取奖励", suggested_level="LIGHTWEIGHT")
        self.assertEqual(report["classification"]["level"], "CRITICAL")
        self.assertTrue(report["classification"]["reasons"])
        self.assertTrue(report["classification"]["evidence"])

    def test_keyword_detection(self):
        hits = cls.detect_hits("修复重复领取奖励")
        self.assertIn("money_economy", hits)
        self.assertEqual(cls.classify("修复重复领取奖励", suggested_level="STANDARD", hits=hits)["level"], "CRITICAL")


class TestStateMachine(unittest.TestCase):
    def test_activated_change_requires_lease_for_direct_transition(self):
        target = make_healthy()
        report = ch.change_new(target, "普通文案修改", suggested_level="DIRECT")
        token_root = tempfile.mkdtemp(prefix="aeh-ch-token-")
        token = os.path.join(token_root, "worker.token")
        acquired = coord.acquire_lease(
            target, report["change_id"], holder_ref="test-worker",
            token_file=token, ttl_seconds=900)
        with self.assertRaises(coord.CoordinationError) as blocked:
            ch.change_transition(target, report["change_id"], "CLASSIFY")
        self.assertIn("BLOCKED_WRITE_LEASE_REQUIRED", str(blocked.exception))
        transitioned = ch.change_transition(
            target, report["change_id"], "CLASSIFY",
            lease_token_file=token,
            expected_lease_revision=acquired["lease_revision"])
        self.assertEqual(transitioned["status"], "TRANSITION_OK")
        self.assertEqual(
            transitioned["coordination"]["status"], "MUTATION_FINALIZED")

    def test_legal_transitions_direct(self):
        target = make_healthy()
        r = ch.change_new(target, "普通文案修改", suggested_level="DIRECT")
        cid = r["change_id"]
        for to in ("CLASSIFY", "IMPLEMENT", "BASIC_VERIFY", "DONE"):
            rep = ch.change_transition(target, cid, to)
            self.assertEqual(rep["status"], "TRANSITION_OK", rep)

    def test_per_change_state_independent(self):
        target = make_healthy()
        r1 = ch.change_new(target, "任务A", suggested_level="DIRECT")
        r2 = ch.change_new(target, "任务B", suggested_level="DIRECT")
        self.assertEqual(ch.change_transition(target, r1["change_id"], "CLASSIFY")["status"], "TRANSITION_OK")
        c2 = ch.load_change(target, r2["change_id"])
        self.assertEqual(c2["state"]["current"], "INTAKE")

    def test_illegal_transition_blocked(self):
        target = make_healthy()
        r = ch.change_new(target, "功能开发", suggested_level="STANDARD")
        ch.change_transition(target, r["change_id"], "CLASSIFY")
        ch.change_transition(target, r["change_id"], "GROUND")
        rep = ch.change_transition(target, r["change_id"], "GREEN")
        self.assertEqual(rep["status"], "BLOCKED_ILLEGAL_STATE_TRANSITION")

    def test_gate_unsatisfied_blocked(self):
        target = make_healthy()
        r = ch.change_new(target, "功能开发", suggested_level="STANDARD")
        ch.change_transition(target, r["change_id"], "CLASSIFY")
        ch.change_transition(target, r["change_id"], "GROUND")
        rep = ch.change_transition(target, r["change_id"], "SPEC")
        self.assertEqual(rep["status"], "BLOCKED_GATE_UNSATISFIED")
        self.assertEqual(rep["gate"], "GROUNDING")

    def test_tampered_runtime_blocks_transition(self):
        target = make_healthy()
        r = ch.change_new(target, "任务", suggested_level="DIRECT")
        with open(os.path.join(target, ".aeh", "runtime", "core", "workflow.yaml"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        rep = ch.change_transition(target, r["change_id"], "CLASSIFY")
        self.assertEqual(rep["status"], "BLOCKED_DOCTOR")

    def test_repair_can_restart_from_refactor_evidence(self):
        target = make_healthy()
        report = ch.change_new(target, "功能开发", suggested_level="STANDARD")
        change = ch.load_change(target, report["change_id"])
        change["state"] = {"current": "REFACTOR", "previous": "GREEN"}
        ch.save_change(target, change)
        repaired = ch.change_repair(target, report["change_id"], "spec")
        self.assertEqual(repaired["status"], "TRANSITION_OK", repaired)
        self.assertEqual(repaired["to"], "SPEC_REPAIR")

    def test_stale_grounding_can_restart_without_manual_state_edit(self):
        for current in ("SPEC", "TEST_DESIGN", "HUMAN_MERGE_APPROVAL"):
            with self.subTest(current=current):
                target = make_healthy()
                report = ch.change_new(target, "功能开发", suggested_level="STANDARD")
                change = ch.load_change(target, report["change_id"])
                change["state"] = {"current": current, "previous": "GROUND"}
                ch.save_change(target, change)
                if current == "HUMAN_MERGE_APPROVAL":
                    blocked = ch.change_transition(target, report["change_id"], "GROUND")
                    self.assertEqual(blocked["status"], "BLOCKED_CONDITION_REQUIRED", blocked)
                    self.assertEqual(blocked["required"], "GROUNDING_STALE")
                repaired = ch.change_repair(target, report["change_id"], "ground")
                self.assertEqual(repaired["status"], "TRANSITION_OK", repaired)
                self.assertEqual(repaired["to"], "GROUND")

    def test_traceability_gap_can_reenter_test_repair_only_with_condition(self):
        target = make_healthy()
        report = ch.change_new(target, "功能开发", suggested_level="STANDARD")
        change = ch.load_change(target, report["change_id"])
        change["state"] = {"current": "REGRESSION", "previous": "RUNTIME_PLATFORM_VERIFY"}
        ch.save_change(target, change)
        blocked = ch.change_transition(target, report["change_id"], "TEST_REPAIR")
        self.assertEqual(blocked["status"], "BLOCKED_CONDITION_REQUIRED", blocked)
        self.assertEqual(blocked["required"], "TRACEABILITY_INCOMPLETE")
        repaired = ch.change_transition(
            target, report["change_id"], "TEST_REPAIR",
            condition="TRACEABILITY_INCOMPLETE")
        self.assertEqual(repaired["status"], "TRANSITION_OK", repaired)

    def test_locked_tests_can_reenter_test_design_explicitly(self):
        target = make_healthy()
        report = ch.change_new(target, "功能开发", suggested_level="STANDARD")
        change = ch.load_change(target, report["change_id"])
        change["state"] = {"current": "LOCK_TEST", "previous": "RED"}
        ch.save_change(target, change)
        repaired = ch.change_repair(target, report["change_id"], "test")
        self.assertEqual(repaired["status"], "TRANSITION_OK", repaired)
        self.assertEqual(repaired["to"], "TEST_REPAIR")


class TestCLI(unittest.TestCase):
    def test_cli_new_status_transition(self):
        target = make_healthy()
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(ROOT, "src")
        r1 = subprocess.run([sys.executable, "-m", "aeh.cli", "change", "new", "普通注释任务", "--level", "DIRECT", "--workdir", target],
                            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("CHANGE_CREATED", r1.stdout)
        cid = json.loads(r1.stdout)["change_id"]
        before = hashlib.sha256(open(os.path.join(target, ".aeh", "changes", cid, "change.yaml"), "rb").read()).hexdigest()
        r2 = subprocess.run([sys.executable, "-m", "aeh.cli", "change", "status", cid, "--workdir", target],
                            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("INTAKE", r2.stdout)
        after = hashlib.sha256(open(os.path.join(target, ".aeh", "changes", cid, "change.yaml"), "rb").read()).hexdigest()
        self.assertEqual(before, after)
        r3 = subprocess.run([sys.executable, "-m", "aeh.cli", "change", "transition", cid, "--to", "CLASSIFY", "--workdir", target],
                            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(r3.returncode, 0, r3.stderr)
        self.assertIn("TRANSITION_OK", r3.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
