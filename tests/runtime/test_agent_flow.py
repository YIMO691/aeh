import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]

from aeh.runtime import change as ch
from aeh.runtime import classify as cls
from tests.runtime.test_change import make_healthy


def require_agent_flow(testcase):
    try:
        from aeh.runtime import agent_flow
    except ImportError as exc:
        testcase.fail("AGENT_FLOW_CONTRACT: missing Agent decision layer: " + str(exc))
    return agent_flow


class ScopedClassificationTests(unittest.TestCase):
    def safe_facts(self):
        return {
            "paths": ["docs/permissions.md"],
            "sensitive_domains": [],
            "reversible": True,
            "evidence": ["task scope is documentation only"],
        }

    def test_scoped_facts_make_ambient_keywords_advisory(self):
        hits = cls.detect_hits("Document permission behavior")
        try:
            result = cls.classify(
                "Document permission behavior",
                suggested_level="LIGHTWEIGHT",
                hits=hits,
                facts=self.safe_facts(),
            )
        except TypeError as exc:
            self.fail("AGENT_FLOW_CONTRACT: classification facts unsupported: " + str(exc))
        self.assertEqual("LIGHTWEIGHT", result["level"])
        self.assertIn("authentication_authorization", result["keyword_hints"])

    def test_actual_sensitive_fact_escalates_and_reassessment_never_downgrades(self):
        risky = self.safe_facts()
        risky["sensitive_domains"] = ["authentication_authorization"]
        result = cls.classify(
            "Update access rules", suggested_level="LIGHTWEIGHT", hits=[], facts=risky
        )
        self.assertEqual("CRITICAL", result["level"])

        current = cls.classify(
            "Normal feature", suggested_level="STANDARD", hits=[], facts=self.safe_facts()
        )
        reassessed = cls.reassess(
            current,
            "Normal feature",
            suggested_level="DIRECT",
            hits=[],
            facts=self.safe_facts(),
        )
        self.assertEqual("STANDARD", reassessed["level"])
        self.assertTrue(reassessed["downgrade_blocked"])

    def test_grounding_does_not_escalate_from_unrelated_repository_markers(self):
        target = make_healthy()
        docs = Path(target, "docs")
        docs.mkdir()
        Path(docs, "permissions.md").write_text(
            "This guide documents permission wording only.\n", encoding="utf-8"
        )
        try:
            created = ch.change_new(
                target,
                "Document permission behavior",
                suggested_level="LIGHTWEIGHT",
                facts=self.safe_facts(),
            )
        except TypeError as exc:
            self.fail("AGENT_FLOW_CONTRACT: change facts unsupported: " + str(exc))
        from aeh.runtime import grounding

        report = grounding.change_ground(target, created["change_id"])
        self.assertEqual("GROUNDING_COMPLETE", report["status"])
        self.assertEqual("LIGHTWEIGHT", ch.load_change(target, created["change_id"])["classification"]["level"])


class AgentContinueTests(unittest.TestCase):
    def write_authority(self, change_id, allow):
        directory = tempfile.mkdtemp(prefix="aeh-agent-authority-")
        path = os.path.join(directory, "authority.yaml")
        with open(path, "w", encoding="utf-8") as stream:
            yaml.safe_dump(
                {"schema_version": 1, "change_id": change_id, "allow": allow},
                stream,
                sort_keys=True,
            )
        return path

    def test_continue_distinguishes_authority_human_gate_block_and_completion(self):
        agent_flow = require_agent_flow(self)
        target = make_healthy()
        created = ch.change_new(target, "Small reversible edit", suggested_level="DIRECT")
        change_id = created["change_id"]

        allowed = self.write_authority(change_id, ["modify_change"])
        decision = agent_flow.continue_change(target, change_id, authority_path=allowed)
        self.assertEqual("CONTINUE", decision["status"])
        self.assertEqual("modify_change", decision["next_action"]["capability"])

        denied = self.write_authority(change_id, [])
        decision = agent_flow.continue_change(target, change_id, authority_path=denied)
        self.assertEqual("WAITING_FOR_AUTHORITY", decision["status"])
        self.assertEqual("modify_change", decision["missing_capability"])

        change = ch.load_change(target, change_id)
        change["workflow"] = {
            "level": "CRITICAL",
            "phases": ["SPEC", "HUMAN_SPEC_APPROVAL", "DESIGN"],
        }
        change["state"] = {"current": "HUMAN_SPEC_APPROVAL", "previous": "SPEC"}
        ch.save_change(target, change)
        decision = agent_flow.continue_change(target, change_id, authority_path=allowed)
        self.assertEqual("WAITING_FOR_AUTHORITY", decision["status"])
        self.assertEqual("SPEC_REVIEW", decision["required_gate"])

        change["state"] = {"current": "BLOCKED_ENVIRONMENT", "previous": "RED"}
        ch.save_change(target, change)
        self.assertEqual(
            "BLOCKED",
            agent_flow.continue_change(target, change_id, authority_path=allowed)["status"],
        )

        change["state"] = {"current": "DONE", "previous": "BASIC_VERIFY"}
        ch.save_change(target, change)
        self.assertEqual(
            "COMPLETE",
            agent_flow.continue_change(target, change_id, authority_path=allowed)["status"],
        )

    def test_cli_exposes_continue(self):
        require_agent_flow(self)
        from aeh.cli import main

        target = make_healthy()
        created = ch.change_new(target, "Small reversible edit", suggested_level="DIRECT")
        authority = self.write_authority(created["change_id"], ["modify_change"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(
                [
                    "change",
                    "continue",
                    created["change_id"],
                    "--authority",
                    authority,
                    "--workdir",
                    target,
                ]
            )
        self.assertEqual(0, code)
        self.assertIn('"status": "CONTINUE"', output.getvalue())


class ProgressiveDisclosureContractTests(unittest.TestCase):
    def test_codex_guidance_and_ci_trigger_contract(self):
        template = Path(ROOT, "adapters", "codex", "AGENTS.template.md").read_text(encoding="utf-8")
        guide = Path(ROOT, "docs", "codex-usage.md").read_text(encoding="utf-8")
        for marker in (
            "change continue",
            "Do not ask the user to choose a workflow level",
            "authority envelope",
        ):
            self.assertIn(marker, template, "AGENT_FLOW_CONTRACT: Codex template missing " + marker)
            self.assertIn(marker, guide, "AGENT_FLOW_CONTRACT: Codex guide missing " + marker)

        workflow = yaml.safe_load(Path(ROOT, ".github", "workflows", "regression.yml").read_text(encoding="utf-8"))
        triggers = workflow["on"]
        self.assertEqual({"branches": ["main"]}, triggers["push"])
        self.assertIn("pull_request", triggers)
        self.assertIn("workflow_dispatch", triggers)


if __name__ == "__main__":
    unittest.main()

