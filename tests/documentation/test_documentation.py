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


if __name__ == "__main__":
    unittest.main()

