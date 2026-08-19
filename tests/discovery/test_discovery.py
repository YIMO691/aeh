"""AEH Phase 2 — Repository Discovery 测试

覆盖：事实模型不变量（value+confidence+evidence）、真实扫描两个 fixture 仓库、
discovery 输出 Schema 校验、unknown 生成、规则与扫描器零硬编码。
"""
import os
import shutil
import sys
import tempfile
import unittest

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.discovery import discover  # noqa: E402

RULES = os.path.join(ROOT, "bootstrap", "discovery")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "repos")
SCHEMA_PATH = os.path.join(ROOT, "schemas", "discovery.schema.json")

DOMAINS = ["repository", "testing", "ci", "git", "ai_rules", "architecture"]
CONFIDENCE = ["DETECTED", "INFERRED", "USER_CONFIRMED", "UNKNOWN"]


def load_schema():
    import json
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.py_fixture = tempfile.mkdtemp(prefix="aeh-discovery-git-fixture-")
        shutil.copytree(os.path.join(FIXTURES, "minimal-py"), cls.py_fixture, dirs_exist_ok=True)
        os.makedirs(os.path.join(cls.py_fixture, ".git"), exist_ok=True)
        cls.py_result = discover(cls.py_fixture, RULES)
        cls.node_result = discover(os.path.join(FIXTURES, "minimal-node"), RULES)
        cls.empty_result = discover(os.path.join(FIXTURES, "empty"), RULES)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.py_fixture)

    @staticmethod
    def find(result, domain, field, value):
        return [f for f in result["facts"]
                if f["domain"] == domain and f["field"] == field and f["value"] == value]

    def test_minimal_py_detections(self):
        r = self.py_result
        self.assertTrue(self.find(r, "repository", "language", "python"))
        self.assertTrue(self.find(r, "repository", "package_manager", "poetry"))
        self.assertTrue(self.find(r, "testing", "testing", "detected"))
        self.assertTrue(self.find(r, "testing", "framework", "pytest"))
        self.assertTrue(self.find(r, "ci", "platform", "github_actions"))
        self.assertTrue(self.find(r, "git", "git_root", "detected"))
        self.assertTrue(self.find(r, "ai_rules", "agents_md", "present"))
        self.assertTrue(self.find(r, "architecture", "structure", "src_tests_separated"))

    def test_minimal_py_unknowns(self):
        unknown = {(u["domain"], u["field"]) for u in self.py_result["unknowns"]}
        self.assertIn(("repository", "build_system"), unknown)
        self.assertIn(("ai_rules", "claude_md"), unknown)
        self.assertIn(("ai_rules", "aeh_installed"), unknown)
        for u in self.py_result["unknowns"]:
            self.assertEqual(u["reason"], "no_markers_matched")

    def test_minimal_node_detections(self):
        r = self.node_result
        self.assertTrue(self.find(r, "repository", "language", "javascript"))
        self.assertTrue(self.find(r, "repository", "package_manager", "npm"))
        self.assertTrue(self.find(r, "testing", "framework", "jest"))
        self.assertTrue(self.find(r, "ci", "platform", "gitlab_ci"))
        self.assertTrue(self.find(r, "ai_rules", "claude_md", "present"))
        self.assertTrue(self.find(r, "ai_rules", "rules_dir", "claude_dir"))

    def test_empty_repo_is_unknown_not_guessed(self):
        r = self.empty_result
        self.assertEqual(r["facts"], [])
        fields = {(u["domain"], u["field"]) for u in r["unknowns"]}
        self.assertIn(("repository", "language"), fields)
        self.assertIn(("git", "git_root"), fields)

    def test_fact_model_invariants(self):
        for r in (self.py_result, self.node_result, self.empty_result):
            ids = set()
            for f in r["facts"]:
                self.assertIn(f["domain"], DOMAINS)
                self.assertIn(f["confidence"], CONFIDENCE)
                self.assertNotIn(f["id"], ids)
                ids.add(f["id"])
                if f["confidence"] == "DETECTED":
                    self.assertGreaterEqual(len(f["evidence"]), 1, f["id"])

    def test_output_validates_against_schema(self):
        for r in (self.py_result, self.node_result, self.empty_result):
            jsonschema.validate(r, load_schema())

    def test_scan_is_deterministic(self):
        a = discover(self.py_fixture, RULES)
        b = discover(self.py_fixture, RULES)
        self.assertEqual(a["facts"], b["facts"])
        self.assertEqual(a["unknowns"], b["unknowns"])


class TestZeroHardcode(unittest.TestCase):
    def test_rules_and_scanner_zero_project_hardcode(self):
        forbidden = ["Unity", "ET6", "Ares", "Speciesboom", "Aresvirus", "D:" + "\\", "C:" + "\\Users"]
        targets = []
        for dp, _, fns in os.walk(os.path.join(ROOT, "bootstrap", "discovery")):
            targets.extend(os.path.join(dp, f) for f in fns)
        targets.append(os.path.join(ROOT, "src", "aeh", "discovery.py"))
        for path in targets:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            for token in forbidden:
                self.assertNotIn(token, text, os.path.basename(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
