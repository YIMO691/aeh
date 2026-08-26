"""AEH Phase 1 契约测试（Contract Tests）

覆盖：Schema 合法性、合法/非法 fixtures、core/schemas 自引用一致性、
状态迁移与 LOCK_TEST 时序、优先级、Critical 硬升级、RED Evidence 字段、
approvals 人工批准约束、Trusted Mutation 字段覆盖、core 零硬编码。

运行：python tests/contract/test_contracts.py
"""
import json
import os
import sys
import unittest

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE = os.path.join(ROOT, "core")
SCHEMAS = os.path.join(ROOT, "schemas")
FIXTURES = os.path.join(ROOT, "tests", "contract", "fixtures")

DRAFT_07 = "http://json-schema.org/draft-07/schema#"
SHA64 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

FIXTURE_SCHEMA = {
    "manifest": "manifest.schema.json",
    "profile": "profile.schema.json",
    "effective-workflow": "effective-workflow.schema.json",
    "change": "change.schema.json",
    "bugfix": "bugfix.schema.json",
    "spec": "spec.schema.json",
    "test-plan": "test-plan.schema.json",
    "tasks": "tasks.schema.json",
    "traceability": "traceability.schema.json",
    "verification": "verification.schema.json",
    "approvals": "approvals.schema.json",
    "aew-governance-adapter": "aew-governance-adapter.schema.json",
    "scm-inspection": "scm-inspection.schema.json",
}


def load_core(name):
    with open(os.path.join(CORE, name), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema(name):
    with open(os.path.join(SCHEMAS, name), "r", encoding="utf-8") as f:
        return json.load(f)


def load_fixture(kind, name):
    with open(os.path.join(FIXTURES, kind, name), "r", encoding="utf-8") as f:
        return json.load(f)


class TestSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_core("workflow.yaml")
        cls.states = load_core("states.yaml")
        cls.gates = load_core("gates.yaml")
        cls.precedence = load_core("precedence.yaml")
        cls.classifications = load_core("classifications.yaml")
        cls.evidence = load_core("evidence.yaml")

    def test_all_schemas_parse_and_use_draft07(self):
        for name in FIXTURE_SCHEMA.values():
            s = load_schema(name)
            self.assertEqual(s["$schema"], DRAFT_07, name)

    def test_legal_fixtures_validate(self):
        for fname in os.listdir(os.path.join(FIXTURES, "legal")):
            if not fname.endswith(".json"):
                continue
            key = fname.split(".")[0]
            schema = load_schema(FIXTURE_SCHEMA[key])
            instance = load_fixture("legal", fname)
            jsonschema.validate(instance, schema)  # 抛异常即失败
            self.assertTrue(True, fname)

    def test_illegal_fixtures_rejected(self):
        rejected = 0
        for fname in os.listdir(os.path.join(FIXTURES, "illegal")):
            if not fname.endswith(".json"):
                continue
            key = fname.split(".")[0]
            schema = load_schema(FIXTURE_SCHEMA[key])
            instance = load_fixture("illegal", fname)
            with self.assertRaises(jsonschema.ValidationError, msg=fname):
                jsonschema.validate(instance, schema)
            rejected += 1
        self.assertGreaterEqual(rejected, 10)


class TestConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_core("workflow.yaml")
        cls.states = load_core("states.yaml")
        cls.gates = load_core("gates.yaml")
        cls.precedence = load_core("precedence.yaml")
        cls.classifications = load_core("classifications.yaml")
        cls.evidence = load_core("evidence.yaml")
        cls.change_schema = load_schema("change.schema.json")
        cls.approvals_schema = load_schema("approvals.schema.json")
        cls.verification_schema = load_schema("verification.schema.json")
        cls.ewf_schema = load_schema("effective-workflow.schema.json")

    def test_workflow_phases_are_known_states(self):
        states = set(self.states["states"])
        for level in self.workflow["levels"]:
            for p in level["phases"]:
                self.assertIn(p, states, level["id"] + ":" + p)

    def test_lock_test_order_in_standard_critical(self):
        for level in self.workflow["levels"]:
            if level["id"] in ("STANDARD", "CRITICAL"):
                phases = level["phases"]
                self.assertLess(phases.index("RED"), phases.index("LOCK_TEST"), level["id"])
                self.assertLess(phases.index("LOCK_TEST"), phases.index("GREEN"), level["id"])
        self.assertEqual(self.evidence["test_lock_order"], ["VALID_RED", "LOCK_TEST", "GREEN"])

    def test_illegal_transitions_are_not_legal(self):
        legal = set((t["from"], t["to"]) for t in self.states["transitions"])
        for t in self.states["illegal_transitions"]:
            self.assertNotIn((t["from"], t["to"]), legal, str(t))

    def test_invalid_red_routing_matches_verdicts(self):
        verdicts = set(self.evidence["red_verdicts"])
        routing = self.evidence["invalid_red_routing"]
        self.assertEqual(set(routing.keys()), verdicts)
        self.assertIn("VALID_RED", routing)
        self.assertEqual(routing["VALID_RED"], "LOCK_TEST")

    def test_red_schema_field_coverage(self):
        red_schema = self.verification_schema["properties"]["red"]
        for f in self.evidence["red_required_fields"]:
            self.assertIn(f, red_schema["required"], f)
        self.assertEqual(
            red_schema["properties"]["verdict"]["enum"],
            self.evidence["red_verdicts"],
        )
        self.assertIn("commit", red_schema["properties"])

    def test_approvals_gate_enum_matches_gates_yaml(self):
        enum = self.approvals_schema["properties"]["approvals"]["items"]["properties"]["gate"]["enum"]
        self.assertEqual(sorted(enum), sorted(self.gates["human_approval_gates"]))

    def test_change_state_enum_matches_states_yaml(self):
        enum = self.change_schema["properties"]["state"]["properties"]["current"]["enum"]
        self.assertEqual(sorted(enum), sorted(self.states["states"]))

    def test_change_gate_props_are_known_gates(self):
        gate_ids = set(g["id"] for g in self.gates["gates"])
        props = set(self.change_schema["properties"]["gates"]["properties"].keys())
        mapping = {"classification": "CLASSIFICATION", "grounding": "GROUNDING", "spec": "SPEC",
                   "test_design": "TEST_DESIGN", "red": "RED", "lock_test": "LOCK_TEST",
                   "verify": "VERIFY", "review": "REVIEW"}
        for k, v in mapping.items():
            self.assertIn(k, props)
            self.assertIn(v, gate_ids)

    def test_level_sets_are_consistent(self):
        wf_levels = [l["id"] for l in self.workflow["levels"]]
        self.assertEqual(wf_levels, self.classifications["levels"])
        self.assertEqual(sorted(wf_levels), sorted(self.ewf_schema["properties"]["levels"]["required"]))

    def test_precedence_frozen_order(self):
        self.assertEqual(self.precedence["order"],
                         ["system", "organization", "project", "team", "task", "developer", "default"])
        self.assertEqual(self.precedence["same_level_conflict"]["verdict"], "BLOCKED_POLICY_CONFLICT")
        self.assertIn("agent_silent_choice", self.precedence["same_level_conflict"]["forbidden"])
        self.assertEqual(self.precedence["scope_rules"]["task_rules_back_propagation"], "forbidden")

    def test_hard_escalation_domains(self):
        he = self.classifications["hard_escalation"]
        self.assertEqual(he["to"], "CRITICAL")
        self.assertEqual(len(he["domains"]), 8)
        self.assertEqual(self.classifications["prohibited_sole_criteria"], ["file_count", "line_count"])

    def test_lightweight_artifact_set(self):
        lw = [l for l in self.workflow["levels"] if l["id"] == "LIGHTWEIGHT"][0]
        self.assertEqual(lw["required_artifacts"],
                         ["change.yaml", "bugfix.yaml", "test-plan.yaml", "verification.yaml"])
        self.assertNotIn("spec.yaml", lw["required_artifacts"])


class TestTrustedMutationCoverage(unittest.TestCase):
    """P-21 Trusted Mutation Boundary 的字段覆盖自检（Schema 层可表达的钩子）。"""

    @classmethod
    def setUpClass(cls):
        cls.manifest = load_schema("manifest.schema.json")
        cls.verification = load_schema("verification.schema.json")
        cls.approvals = load_schema("approvals.schema.json")
        cls.change = load_schema("change.schema.json")
        cls.profile = load_schema("profile.schema.json")

    def test_manifest_digest_fields(self):
        sh = self.manifest["properties"]["source_hashes"]
        self.assertEqual(sorted(sh["required"]),
                         sorted(["runtime", "compiler", "bootstrap_contract", "adapters"]))

    def test_red_output_integrity_fields(self):
        red = self.verification["properties"]["red"]
        for f in ("output_ref", "output_hash", "exit_code"):
            self.assertIn(f, red["required"])

    def test_approvals_approved_requires_human(self):
        items = self.approvals["properties"]["approvals"]["items"]
        self.assertIn("allOf", items)
        then = items["allOf"][0]["then"]
        self.assertEqual(then["properties"]["actor"]["properties"]["type"]["const"], "human")

    def test_change_state_provenance_hooks(self):
        state = self.change["properties"]["state"]
        self.assertIn("current", state["required"])
        self.assertIn("previous", state["properties"])

    def test_profile_provenance_definition_required_fields(self):
        prov = self.profile["definitions"]["provenance"]
        self.assertEqual(sorted(prov["required"]), sorted(["value", "source", "confidence"]))


class TestZeroHardcode(unittest.TestCase):
    def test_core_and_schemas_zero_project_hardcode(self):
        forbidden = ["Unity", "ET6", "Ares", "Speciesboom", "Aresvirus"]
        for dirpath, _, files in ((CORE, "core", None), (SCHEMAS, "schemas", None)):
            for fname in os.listdir(dirpath):
                with open(os.path.join(dirpath, fname), "r", encoding="utf-8") as f:
                    text = f.read()
                for token in forbidden:
                    self.assertNotIn(token, text, fname)


if __name__ == "__main__":
    unittest.main(verbosity=2)
