import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DocumentationContractTests(unittest.TestCase):
    def test_current_claims_and_links_are_consistent(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_docs.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("DOCUMENTATION_CHECK_PASS", result.stdout)
        self.assertIn("roadmap=M1-M6_MERGED", result.stdout)

        stale_claims = (
            "M6.3 remains planned",
            "M6.3 PLANNED",
            "M6.3C candidate under final assurance",
            "M6 in progress",
            "M6 is planned",
            "five of six top-level",
        )
        for relative in ("README.md", "docs/status.md"):
            body = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("M1–M6", body)
            for stale in stale_claims:
                self.assertNotIn(stale, body)

    def test_codex_user_guide_contract(self) -> None:
        required_files = (
            "README.zh-CN.md",
            "docs/codex-usage.md",
        )
        for relative in required_files:
            self.assertTrue(
                (ROOT / relative).is_file(),
                f"AGENT_FLOW_DOC_ALIGNMENT: missing {relative}",
            )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "README.zh-CN.md",
            "docs/codex-usage.md",
            "DIRECT",
            "LIGHTWEIGHT",
            "STANDARD",
            "CRITICAL",
            "Codex",
            "Agent-driven flow",
            "418 tests",
            "414 passed",
        ):
            self.assertIn(marker, readme, f"AGENT_FLOW_DOC_ALIGNMENT: README missing {marker}")

        chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        for marker in ("Agent-driven flow", "418 个", "414 个通过"):
            self.assertIn(marker, chinese, f"AGENT_FLOW_DOC_ALIGNMENT: Chinese README missing {marker}")

        status = (ROOT / "docs" / "status.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for body, name in ((status, "status"), (changelog, "changelog")):
            for marker in (
                "PR #24",
                "d167b3ad899159cec809ef1819671b03b3838ffc",
                "34044290320",
                "418",
                "414",
            ):
                self.assertIn(marker, body, f"AGENT_FLOW_DOC_ALIGNMENT: {name} missing {marker}")

        architecture = (ROOT / "docs" / "architecture-current.md").read_text(encoding="utf-8")
        for marker in (
            "Agent decision layer",
            "scoped facts",
            "CONTINUE",
            "WAITING_FOR_AUTHORITY",
            "BLOCKED",
            "COMPLETE",
        ):
            self.assertIn(marker, architecture, f"AGENT_FLOW_DOC_ALIGNMENT: architecture missing {marker}")

        contract = (ROOT / "docs" / "documentation-contract.yaml").read_text(encoding="utf-8")
        for marker in (
            "latest_feature_pr: 'PR #24'",
            "latest_feature_merge: d167b3ad899159cec809ef1819671b03b3838ffc",
            "latest_feature_postmerge_run: '34044290320'",
            "local_tests_discovered: 418",
            "local_tests_passed: 414",
        ):
            self.assertIn(marker, contract, f"AGENT_FLOW_DOC_ALIGNMENT: contract missing {marker}")

        roadmap = (ROOT / "docs" / "roadmap-v0.2.md").read_text(encoding="utf-8")
        self.assertIn("COMPLETED", roadmap, "AGENT_FLOW_DOC_ALIGNMENT: roadmap not completed")
        self.assertIn("VERSION-BOUND", roadmap, "AGENT_FLOW_DOC_ALIGNMENT: roadmap not version-bound")


if __name__ == "__main__":
    unittest.main()
