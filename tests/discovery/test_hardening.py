"""AEH Phase 2 Hardening — Discovery 信任/安全/可复现边界测试

覆盖：路径防逃逸、content 证据最小化、provenance、规则 schema 拒绝、binary/oversized、
resource bound、无网络、只读。
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

from aeh import discovery as D  # noqa: E402

RULES = os.path.join(ROOT, "bootstrap", "discovery")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "repos")
OUT_SCHEMA = os.path.join(ROOT, "schemas", "discovery.schema.json")
RULE_SCHEMA = os.path.join(ROOT, "schemas", "discovery-rule.schema.json")


def load_json_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPathEscape(unittest.TestCase):
    def test_resolve_within_rejects_parent_traversal(self):
        root = os.path.join(FIXTURES, "minimal-py")
        self.assertIsNone(D._resolve_within(root, "../outside.txt"))
        self.assertIsNone(D._resolve_within(root, "sub/../../etc"))
        self.assertIsNone(D._resolve_within(root, os.path.join("..", "outside.txt")))

    def test_resolve_within_rejects_absolute(self):
        root = os.path.join(FIXTURES, "minimal-py")
        self.assertIsNone(D._resolve_within(root, os.path.abspath(root)))
        self.assertIsNone(D._resolve_within(root, "C:\Windows\win.ini"))

    def test_resolve_within_accepts_legit_path(self):
        root = os.path.join(FIXTURES, "minimal-py")
        self.assertIsNotNone(D._resolve_within(root, "pyproject.toml"))

    def test_rule_schema_rejects_escape_path(self):
        schema = load_json_schema(RULE_SCHEMA)
        rule = {
            "contract": "bootstrap.discovery.rule", "version": 1, "domain": "git",
            "detectors": [{"id": "bad", "field": "git_root", "value": "x",
                           "markers": [{"type": "file", "path": "../outside.txt"}]}],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(rule, schema)

    def test_scanner_rejects_invalid_rule_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_rule = os.path.join(tmp, "bad.yaml")
            with open(bad_rule, "w", encoding="utf-8") as f:
                f.write("contract: bootstrap.discovery.rule\nversion: 1\ndomain: git\n"
                        "detectors:\n  - {id: bad, field: git_root, value: x, markers: [{type: file, path: ../outside.txt}]}\n")
            with self.assertRaises(D.DiscoveryError):
                D.discover(os.path.join(FIXTURES, "minimal-py"), tmp, RULE_SCHEMA)


class TestContentEvidenceMinimal(unittest.TestCase):
    def test_content_evidence_has_no_raw_content(self):
        result = D.discover(os.path.join(FIXTURES, "minimal-py"), RULES, RULE_SCHEMA)
        content_evs = [e for f in result["facts"] for e in f["evidence"] if e["type"] == "content"]
        self.assertGreater(len(content_evs), 0)
        for e in content_evs:
            self.assertIn("file_hash", e)
            self.assertRegex(e["file_hash"], "^[0-9a-fA-F]{64}$")
            self.assertIn("rule_id", e)
            self.assertIn("marker_index", e)
            self.assertIn("match_line", e)
            self.assertNotIn("raw", e)
        serialized = json.dumps(result, default=str)
        self.assertNotIn("testpaths", serialized)   # fixture 仓库正文不得进入输出
        self.assertNotIn("tool.pytest", serialized)

    def test_content_marker_skips_binary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules_dir = os.path.join(tmp, "rules")
            os.makedirs(rules_dir)
            with open(os.path.join(rules_dir, "r.yaml"), "w", encoding="utf-8") as f:
                f.write("contract: bootstrap.discovery.rule\nversion: 1\ndomain: repository\n"
                        "detectors:\n  - {id: bin-test, field: language, value: binary, "
                        "markers: [{type: content, path: data.bin, contains: magic}]}\n")
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            with open(os.path.join(repo, "data.bin"), "wb") as f:
                f.write(b"\x00\x01\x02magic")
            result = D.discover(repo, rules_dir, RULE_SCHEMA)
            self.assertFalse([x for x in result["facts"] if x["field"] == "language" and x["value"] == "binary"])

    def test_oversized_file_skipped_with_tiny_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules_dir = os.path.join(tmp, "rules")
            os.makedirs(rules_dir)
            with open(os.path.join(rules_dir, "r.yaml"), "w", encoding="utf-8") as f:
                f.write("contract: bootstrap.discovery.rule\nversion: 1\ndomain: repository\n"
                        "detectors:\n  - {id: big-test, field: language, value: big, "
                        "markers: [{type: content, path: big.txt, contains: needle}]}\n")
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            with open(os.path.join(repo, "big.txt"), "w", encoding="utf-8") as f:
                f.write("x" * 4096)
            result = D.discover(repo, rules_dir, RULE_SCHEMA, limits={"max_content_bytes": 1024})
            self.assertFalse([x for x in result["facts"] if x["field"] == "language" and x["value"] == "big"])


class TestProvenance(unittest.TestCase):
    def test_provenance_fields_present(self):
        result = D.discover(os.path.join(FIXTURES, "minimal-py"), RULES, RULE_SCHEMA)
        self.assertEqual(result["scanner_version"], D.SCANNER_VERSION)
        self.assertRegex(result["ruleset_digest"], "^[0-9a-fA-F]{64}$")
        self.assertEqual(result["version"], 2)
        self.assertIn("base_commit", result["repository"])
        self.assertIn("dirty", result["repository"])

    def test_ruleset_digest_changes_with_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules_dir = os.path.join(tmp, "rules")
            shutil.copytree(RULES, rules_dir)
            r1 = D.discover(os.path.join(FIXTURES, "minimal-py"), rules_dir, RULE_SCHEMA)
            with open(os.path.join(rules_dir, "git.yaml"), "a", encoding="utf-8") as f:
                f.write("# change\n")
            r2 = D.discover(os.path.join(FIXTURES, "minimal-py"), rules_dir, RULE_SCHEMA)
            self.assertNotEqual(r1["ruleset_digest"], r2["ruleset_digest"])

    def test_output_schema_validates_v2(self):
        for repo in ("minimal-py", "minimal-node", "empty"):
            result = D.discover(os.path.join(FIXTURES, repo), RULES, RULE_SCHEMA)
            jsonschema.validate(result, load_json_schema(OUT_SCHEMA))


class TestResourceAndSafety(unittest.TestCase):
    def test_walk_bound_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules_dir = os.path.join(tmp, "rules")
            os.makedirs(rules_dir)
            with open(os.path.join(rules_dir, "r.yaml"), "w", encoding="utf-8") as f:
                f.write("contract: bootstrap.discovery.rule\nversion: 1\ndomain: repository\n"
                        "detectors:\n  - {id: many, field: language, value: python, markers: [{type: glob, pattern: '**/*.py'}]}\n")
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            for i in range(30):
                with open(os.path.join(repo, "f%d.py" % i), "w", encoding="utf-8") as f:
                    f.write("x")
            result = D.discover(repo, rules_dir, RULE_SCHEMA, limits={"max_walk_files": 10})
            codes = [w["code"] for w in result["warnings"]]
            self.assertIn("resource_limit", codes)

    def test_no_network_and_read_only(self):
        src = open(os.path.join(ROOT, "src", "aeh", "discovery.py"), "r", encoding="utf-8").read()
        for banned in ["urllib", "socket", "requests", "http.client", "ftp"]:
            self.assertNotIn(banned, src)
        for banned in ["os.remove", "os.rename", "os.rmdir", "shutil.rmtree", '"w"', "'w'", '"wb"', "'wb'"]:
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
