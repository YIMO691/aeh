"""AEH Phase 4 — Conflict Resolver + Profile/Workflow Compiler 测试

覆盖 spec 的 18 项：优先级覆盖、同级冲突、provenance 保留、private 最小披露、
FACT/PREFERENCE/PERMISSION 语义、非法 option 拒绝、两个 Schema PASS、
Task 不进入 Profile、确定性（顺序/scanned_at/answered_at）、Core workflow 不被修改。
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh import compiler as cm  # noqa: E402
from aeh import conflict as cf  # noqa: E402
from aeh import discovery as disc  # noqa: E402
from aeh import interview as iv  # noqa: E402

IV_RULES = os.path.join(ROOT, "bootstrap", "interview")
DISC_RULES = os.path.join(ROOT, "bootstrap", "discovery")
DISC_SCHEMA = os.path.join(ROOT, "schemas", "discovery-rule.schema.json")
PROFILE_SCHEMA = os.path.join(ROOT, "schemas", "profile.schema.json")
EWF_SCHEMA = os.path.join(ROOT, "schemas", "effective-workflow.schema.json")
CONFLICT_SCHEMA = os.path.join(ROOT, "schemas", "conflict.schema.json")
CORE_WORKFLOW = os.path.join(ROOT, "core", "workflow.yaml")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "repos")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_core_workflow():
    with open(CORE_WORKFLOW, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_question_file(dirpath, fname, scope, questions):
    with open(os.path.join(dirpath, fname), "w", encoding="utf-8") as f:
        f.write("contract: bootstrap.interview\nversion: 1\nscope: " + scope + "\nquestions:\n")
        for q in questions:
            f.write("  - question_id: " + q["qid"] + "\n")
            f.write("    type: " + q["type"] + "\n")
            f.write("    field: " + q["field"] + "\n")
            f.write('    question: "q?"\n')
            f.write("    required: true\n")
            f.write("    options:\n")
            for v in q["options"]:
                f.write("      - {value: " + json.dumps(v) + "}\n")


def ans(qid, value, source="user_answer", **extra):
    a = {"question_id": qid, "answer": value, "type": "POLICY",
         "source": source, "answered_at": "2026-08-14T00:00:00+00:00"}
    a.update(extra)
    return a


def answers_of(entries):
    return {"contract": "bootstrap.interview.answers", "version": 1, "answers": entries, "reset": []}


class TestConflictPrecedence(unittest.TestCase):
    def setUp(self):
        self.prec = cf.load_precedence()

    def _compile(self, specs, answer_entries, discovery=None):
        with tempfile.TemporaryDirectory() as tmp:
            by_scope = {}
            for (scope, q) in specs:
                by_scope.setdefault(scope, []).extend(q)
            for i, (scope, qs) in enumerate(by_scope.items()):
                make_question_file(tmp, "r%d.yaml" % i, scope, qs)
            questions, _ = iv.load_questions(tmp)
            discv = discovery or {"repository_root": ".", "facts": [], "unknowns": []}
            return cm.compile_profile(questions, answers_of(dict(answer_entries)), discv, self.prec)

    def test_organization_overrides_developer(self):
        specs = [
            ("organization", [{"qid": "q-org-x", "type": "POLICY", "field": "review.human_required_for", "options": ["critical", "all"]}]),
            ("developer", [{"qid": "q-dev-x", "type": "PREFERENCE", "field": "review.human_required_for", "options": ["none", "all"]}]),
        ]
        profile = self._compile(specs, [
            ("q-org-x", ans("q-org-x", "critical")),
            ("q-dev-x", ans("q-dev-x", "none")),
        ])
        entry = profile["review"]["human_required_for"][0]
        self.assertEqual(entry["value"], "critical")
        self.assertEqual([s["ref"] for s in entry.get("shadowed", [])], ["q-dev-x"])

    def test_project_overrides_team(self):
        specs = [
            ("core", [{"qid": "q-prj-x", "type": "POLICY", "field": "testing.tdd", "options": ["always", "no"]}]),
            ("team", [{"qid": "q-team-x", "type": "POLICY", "field": "testing.tdd", "options": ["always", "no"]}]),
        ]
        profile = self._compile(specs, [
            ("q-prj-x", ans("q-prj-x", "always")),
            ("q-team-x", ans("q-team-x", "no")),
        ])
        self.assertEqual(profile["testing"]["tdd"]["value"], "always")
        self.assertEqual([s["ref"] for s in profile["testing"]["tdd"]["shadowed"]], ["q-team-x"])

    def test_team_overrides_developer(self):
        specs = [
            ("team", [{"qid": "q-team-y", "type": "POLICY", "field": "developer.preferred_report", "options": ["detailed", "concise"]}]),
            ("developer", [{"qid": "q-dev-y", "type": "PREFERENCE", "field": "developer.preferred_report", "options": ["detailed", "concise"]}]),
        ]
        profile = self._compile(specs, [
            ("q-team-y", ans("q-team-y", "detailed")),
            ("q-dev-y", ans("q-dev-y", "concise")),
        ])
        self.assertEqual(profile["developer"]["preferred_report"]["value"], "detailed")

    def test_same_level_different_values_blocked(self):
        specs = [
            ("team", [
                {"qid": "q-t1", "type": "POLICY", "field": "team.policy_x", "options": ["a", "b"]},
                {"qid": "q-t2", "type": "POLICY", "field": "team.policy_x", "options": ["a", "b"]},
            ]),
        ]
        profile = self._compile(specs, [
            ("q-t1", ans("q-t1", "a")),
            ("q-t2", ans("q-t2", "b")),
        ])
        self.assertEqual(profile["status"], "BLOCKED")
        self.assertEqual(len(profile["conflicts"]), 1)
        c = profile["conflicts"][0]
        self.assertEqual(c["status"], "BLOCKED_POLICY_CONFLICT")
        self.assertEqual(c["level"], "team")
        jsonschema.validate(c, load_json(CONFLICT_SCHEMA))
        self.assertNotIn("policy_x", profile.get("team", {}))

    def test_same_level_same_value_no_conflict(self):
        specs = [
            ("team", [
                {"qid": "q-t1", "type": "POLICY", "field": "team.policy_y", "options": ["a", "b"]},
                {"qid": "q-t2", "type": "POLICY", "field": "team.policy_y", "options": ["a", "b"]},
            ]),
        ]
        profile = self._compile(specs, [
            ("q-t1", ans("q-t1", "a")),
            ("q-t2", ans("q-t2", "a")),
        ])
        self.assertEqual(profile["conflicts"], [])
        self.assertEqual(profile["team"]["policy_y"]["value"], "a")


class TestCompileSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prec = cf.load_precedence()
        cls.questions, _ = iv.load_questions(IV_RULES)
        cls.py_disc = disc.discover(os.path.join(FIXTURES, "minimal-py"), DISC_RULES, DISC_SCHEMA)

    def test_private_ref_only_no_body(self):
        a = ans("q-git-push", "deny")
        a["private_body"] = "SECRET-TOKEN-123"
        profile = cm.compile_profile(self.questions, answers_of({"q-git-push": a}), self.py_disc, self.prec)
        serialized = json.dumps(profile, default=str)
        self.assertNotIn("SECRET-TOKEN-123", serialized)
        self.assertEqual(profile["permissions"]["git_push"]["source"]["ref"], "q-git-push")

    def test_fact_not_compiled_as_policy(self):
        profile = cm.compile_profile(self.questions, answers_of({}), self.py_disc, self.prec)
        langs = profile["project"]["languages"]
        self.assertEqual([i["value"] for i in langs], ["python"])
        self.assertEqual(langs[0]["type"], "FACT")
        self.assertNotIn("repository.language", profile.get("organization", {}))
        self.assertNotIn("language", profile.get("organization", {}))

    def test_preference_enters_developer(self):
        profile = cm.compile_profile(self.questions, answers_of({"q-plan-before-code": ans("q-plan-before-code", "always")}), self.py_disc, self.prec)
        e = profile["developer"]["plan_before_code"]
        self.assertEqual(e["value"], "always")
        self.assertEqual(e["type"], "PREFERENCE")

    def test_permission_compiled(self):
        profile = cm.compile_profile(self.questions, answers_of({"q-git-push": ans("q-git-push", "deny")}), self.py_disc, self.prec)
        e = profile["permissions"]["git_push"]
        self.assertEqual(e["value"], "deny")
        self.assertEqual(e["type"], "PERMISSION")

    def test_illegal_option_rejected(self):
        with self.assertRaises(cf.CompilerError):
            cm.compile_profile(self.questions, answers_of({"q-modify-source": ans("q-modify-source", "banana")}), self.py_disc, self.prec)

    def test_profile_schema_pass(self):
        answers = answers_of({
            "q-plan-before-code": ans("q-plan-before-code", "always"),
            "q-testing-policy": ans("q-testing-policy", "risk_based"),
            "q-human-review": ans("q-human-review", "critical"),
            "q-modify-source": ans("q-modify-source", "ask"),
            "q-git-commit": ans("q-git-commit", "ask"),
            "q-git-push": ans("q-git-push", "deny"),
            "q-shell-access": ans("q-shell-access", "ask"),
            "q-web-access": ans("q-web-access", "ask"),
            "q-team-review-policy": ans("q-team-review-policy", "major"),
        })
        profile = cm.compile_profile(self.questions, answers, self.py_disc, self.prec)
        jsonschema.validate(profile, load_json(PROFILE_SCHEMA))

    def test_task_rule_not_in_profile(self):
        profile = cm.compile_profile(self.questions, answers_of({}), self.py_disc, self.prec)
        self.assertNotIn("task", profile)
        serialized = json.dumps(profile, default=str)
        self.assertNotIn("task_rule", serialized)

    def test_effective_workflow_schema_pass_and_core_untouched(self):
        before = hashlib.sha256(open(CORE_WORKFLOW, "rb").read()).hexdigest()
        core = load_core_workflow()
        profile = cm.compile_profile(self.questions, answers_of({}), self.py_disc, self.prec)
        effective = cm.compile_effective_workflow(core, profile)
        jsonschema.validate(effective, load_json(EWF_SCHEMA))
        self.assertEqual(effective["default_level"], "STANDARD")
        self.assertEqual(effective["levels"]["STANDARD"]["phases"], core["levels"][2]["phases"])
        after = hashlib.sha256(open(CORE_WORKFLOW, "rb").read()).hexdigest()
        self.assertEqual(before, after)
        self.assertNotEqual(effective, core)

    def test_default_level_reflects_profile(self):
        core = load_core_workflow()
        profile = cm.compile_profile(self.questions, answers_of({}), self.py_disc, self.prec)
        effective1 = cm.compile_effective_workflow(core, profile)
        profile2 = dict(profile)
        profile2["workflow"] = {"default_level": "CRITICAL"}
        effective2 = cm.compile_effective_workflow(core, profile2)
        self.assertEqual(effective1["default_level"], "STANDARD")
        self.assertEqual(effective2["default_level"], "CRITICAL")


class TestDeterminism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prec = cf.load_precedence()
        cls.questions, _ = iv.load_questions(IV_RULES)
        cls.py_disc = disc.discover(os.path.join(FIXTURES, "minimal-py"), DISC_RULES, DISC_SCHEMA)

    def _profile(self, answers):
        return json.dumps(cm.compile_profile(self.questions, answers, self.py_disc, self.prec), sort_keys=True, default=str)

    def test_input_order_independent(self):
        a1 = answers_of({"q-plan-before-code": ans("q-plan-before-code", "always"),
                         "q-git-push": ans("q-git-push", "deny")})
        a2 = answers_of({"q-git-push": ans("q-git-push", "deny"),
                         "q-plan-before-code": ans("q-plan-before-code", "always")})
        self.assertEqual(self._profile(a1), self._profile(a2))

    def test_scanned_at_irrelevant(self):
        d1 = dict(self.py_disc); d1["scanned_at"] = "2026-01-01T00:00:00+00:00"
        d2 = dict(self.py_disc); d2["scanned_at"] = "2030-01-01T00:00:00+00:00"
        p1 = json.dumps(cm.compile_profile(self.questions, answers_of({}), d1, self.prec), sort_keys=True, default=str)
        p2 = json.dumps(cm.compile_profile(self.questions, answers_of({}), d2, self.prec), sort_keys=True, default=str)
        self.assertEqual(p1, p2)

    def test_answered_at_irrelevant(self):
        a1 = answers_of({"q-git-push": ans("q-git-push", "deny")})
        a2 = answers_of({"q-git-push": ans("q-git-push", "deny")})
        a2["answers"]["q-git-push"]["answered_at"] = "2030-12-31T23:59:59+00:00"
        self.assertEqual(self._profile(a1), self._profile(a2))
        self.assertNotIn("answered_at", self._profile(a1))


class TestMultiFieldFold(unittest.TestCase):
    """release-fix 002：多值事实折叠（polyglot 仓库可 bootstrap；非 multi 字段仍 BLOCKED）。"""

    def test_multi_language_facts_fold_to_list(self):
        discovery = {"facts": [
            {"id": "F-001", "domain": "repository", "field": "language", "value": "python", "confidence": "DETECTED"},
            {"id": "F-002", "domain": "repository", "field": "language", "value": "javascript", "confidence": "DETECTED"},
            {"id": "F-003", "domain": "repository", "field": "language", "value": "csharp", "confidence": "DETECTED"},
        ]}
        records = cf.normalize([], {"answers": {}}, discovery,
                               ["default"], multi_fields=["repository.language"])
        lang = [r for r in records if r["field"] == "repository.language"]
        self.assertEqual(len(lang), 1)
        self.assertEqual(lang[0]["value"], ["csharp", "javascript", "python"])
        self.assertEqual(lang[0]["confidence"], "DETECTED")
        out = cf.resolve(records, ["default"])
        self.assertEqual(out["conflicts"], [])

    def test_multi_structure_facts_fold(self):
        discovery = {"facts": [
            {"id": "F-001", "domain": "architecture", "field": "structure", "value": "src_tests_separated", "confidence": "INFERRED"},
            {"id": "F-002", "domain": "architecture", "field": "structure", "value": "arch_docs", "confidence": "DETECTED"},
        ]}
        records = cf.normalize([], {"answers": {}}, discovery,
                               ["default"], multi_fields=["architecture.structure"])
        merged = [r for r in records if r["field"] == "architecture.structure"][0]
        self.assertEqual(merged["value"], ["arch_docs", "src_tests_separated"])
        self.assertEqual(merged["confidence"], "DETECTED")
        self.assertEqual(merged["origin_ref"], "merged:F-001,F-002")

    def test_non_multi_field_conflict_still_blocked(self):
        discovery = {"facts": [
            {"id": "F-001", "domain": "repository", "field": "package_manager", "value": "pip", "confidence": "DETECTED"},
            {"id": "F-002", "domain": "repository", "field": "package_manager", "value": "npm", "confidence": "DETECTED"},
        ]}
        records = cf.normalize([], {"answers": {}}, discovery, ["default"])
        out = cf.resolve(records, ["default"])
        self.assertEqual(len(out["conflicts"]), 1)
        self.assertEqual(out["conflicts"][0]["status"], "BLOCKED_POLICY_CONFLICT")

    def test_higher_precedence_overrides_folded_facts(self):
        discovery = {"facts": [
            {"id": "F-001", "domain": "repository", "field": "language", "value": "python", "confidence": "DETECTED"},
            {"id": "F-002", "domain": "repository", "field": "language", "value": "javascript", "confidence": "DETECTED"},
        ]}
        questions = [{"question_id": "q-lang", "type": "PREFERENCE", "field": "repository.language", "scope": "core"}]
        answers = {"answers": {"q-lang": {"answer": "python", "source": "user_answer", "type": "PREFERENCE"}}}
        records = cf.normalize(questions, answers, discovery,
                               ["project", "default"], multi_fields=["repository.language"])
        out = cf.resolve(records, ["project", "default"])
        self.assertEqual(out["conflicts"], [])
        self.assertEqual(out["resolved"]["repository.language"]["value"], "python")
        self.assertIn("repository.language", out["shadowed"])

    def test_rules_declare_multi_fields(self):
        mf = disc.collect_multi_fields(DISC_RULES)
        self.assertIn("repository.language", mf)
        self.assertIn("repository.documentation", mf)
        self.assertIn("architecture.structure", mf)


if __name__ == "__main__":
    unittest.main(verbosity=2)