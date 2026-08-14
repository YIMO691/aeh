"""AEH Phase 3 — Progressive Interview Minimal 测试

覆盖 spec 全部要求：DETECTED 跳过、UNKNOWN+required 过滤、已答跳过、reset 重问、
四类问题保存、非法规则拒绝、自定义问题零代码生效、确定性、scanned_at 非语义。
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh import discovery as disc  # noqa: E402
from aeh import interview as iv  # noqa: E402

IV_RULES = os.path.join(ROOT, "bootstrap", "interview")
DISC_RULES = os.path.join(ROOT, "bootstrap", "discovery")
DISC_SCHEMA = os.path.join(ROOT, "schemas", "discovery-rule.schema.json")
ANSWERS_SCHEMA = os.path.join(ROOT, "schemas", "answers.schema.json")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "repos")


def load_answers_schema():
    with open(ANSWERS_SCHEMA, "r", encoding="utf-8") as f:
        return json.load(f)


class TestInterview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions, _ = iv.load_questions(IV_RULES)
        cls.py_disc = disc.discover(os.path.join(FIXTURES, "minimal-py"), DISC_RULES, DISC_SCHEMA)
        cls.empty_disc = disc.discover(os.path.join(FIXTURES, "empty"), DISC_RULES, DISC_SCHEMA)

    @staticmethod
    def decision(decisions, qid):
        return [d for d in decisions if d["question_id"] == qid][0]

    def test_detected_fact_skipped(self):
        decisions = iv.plan(self.questions, self.py_disc, {})
        d = self.decision(decisions, "q-repo-language")
        self.assertEqual(d["decision"], "SKIP")
        self.assertEqual(d["reason"], "discovery_detected")

    def test_unknown_required_true_asks(self):
        decisions = iv.plan(self.questions, self.empty_disc, {})
        self.assertEqual(self.decision(decisions, "q-plan-before-code")["decision"], "ASK")
        self.assertEqual(self.decision(decisions, "q-repo-language")["decision"], "ASK")

    def test_unknown_required_false_skips(self):
        decisions = iv.plan(self.questions, self.empty_disc, {})
        d = self.decision(decisions, "q-org-policies-exist")
        self.assertEqual(d["decision"], "SKIP")
        self.assertEqual(d["reason"], "optional")

    def test_answered_skips_second_run(self):
        first = iv.plan(self.questions, self.empty_disc, {})
        asked = [d for d in first if d["decision"] == "ASK"]
        self.assertGreater(len(asked), 0)
        answers = {}
        for d in asked:
            q = [q for q in self.questions if q["question_id"] == d["question_id"]][0]
            answers = iv.record_answer(answers, q, "test-value")
        second = iv.plan(self.questions, self.empty_disc, answers)
        for d in asked:
            d2 = self.decision(second, d["question_id"])
            self.assertEqual(d2["decision"], "SKIP")
            self.assertEqual(d2["reason"], "already_answered")

    def test_reset_reasks_single_question(self):
        answers = {}
        q = [q for q in self.questions if q["question_id"] == "q-plan-before-code"][0]
        answers = iv.record_answer(answers, q, "always")
        other = [q2 for q2 in self.questions if q2["question_id"] == "q-git-push"][0]
        answers = iv.record_answer(answers, other, "deny")
        answers = iv.reset_answer(answers, "q-plan-before-code")
        decisions = iv.plan(self.questions, self.empty_disc, answers)
        self.assertEqual(self.decision(decisions, "q-plan-before-code")["decision"], "ASK")
        self.assertEqual(self.decision(decisions, "q-git-push")["decision"], "SKIP")

    def test_types_saved_correctly(self):
        answers = {}
        for qid, answer in [("q-plan-before-code", "always"), ("q-testing-policy", "risk_based"), ("q-modify-source", "ask")]:
            q = [q for q in self.questions if q["question_id"] == qid][0]
            answers = iv.record_answer(answers, q, answer)
        self.assertEqual(answers["answers"]["q-plan-before-code"]["type"], "PREFERENCE")
        self.assertEqual(answers["answers"]["q-testing-policy"]["type"], "POLICY")
        self.assertEqual(answers["answers"]["q-modify-source"]["type"], "PERMISSION")
        for a in answers["answers"].values():
            self.assertEqual(a["source"], "user_answer")
            self.assertIn("answered_at", a)
        jsonschema.validate(answers, load_answers_schema())

    def test_invalid_rule_rejected(self):
        bads = [
            ("contract: bootstrap.interview\nversion: 1\nscope: core\nquestions:\n"
             "  - {question_id: q1, type: QUIZ, field: f.x, question: q?, required: true}\n"),
            ("contract: bootstrap.interview\nversion: 1\nscope: core\nquestions:\n"
             "  - {type: FACT, field: f.x, question: q?, required: true}\n"),
            ("contract: bootstrap.interview\nversion: 1\nscope: unknown_scope\nquestions:\n"
             "  - {question_id: q1, type: FACT, field: f.x, question: q?, required: true}\n"),
        ]
        for i, content in enumerate(bads):
            with tempfile.TemporaryDirectory() as tmp:
                with open(os.path.join(tmp, "bad.yaml"), "w", encoding="utf-8") as f:
                    f.write(content)
                with self.assertRaises(iv.InterviewError, msg="case " + str(i)):
                    iv.load_questions(tmp)

    def test_custom_question_no_code_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(IV_RULES, tmp, dirs_exist_ok=True)
            with open(os.path.join(tmp, "custom.yaml"), "w", encoding="utf-8") as f:
                f.write("contract: bootstrap.interview\nversion: 1\nscope: team\nquestions:\n"
                        "  - question_id: q-custom-foo\n"
                        "    type: PREFERENCE\n"
                        "    field: team.custom_foo\n"
                        "    question: \"自定义问题：foo 怎么处理？\"\n"
                        "    required: true\n")
            questions, _ = iv.load_questions(tmp)
            decisions = iv.plan(questions, self.empty_disc, {})
            self.assertEqual(self.decision(decisions, "q-custom-foo")["decision"], "ASK")

    def test_deterministic_plan(self):
        d1 = iv.plan(self.questions, self.py_disc, {})
        d2 = iv.plan(self.questions, self.py_disc, {})
        self.assertEqual(d1, d2)

    def test_scanned_at_is_non_semantic(self):
        disc_a = dict(self.empty_disc)
        disc_a["scanned_at"] = "2026-01-01T00:00:00+00:00"
        disc_b = dict(self.empty_disc)
        disc_b["scanned_at"] = "2030-12-31T23:59:59+00:00"
        self.assertEqual(iv.plan(self.questions, disc_a, {}), iv.plan(self.questions, disc_b, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
