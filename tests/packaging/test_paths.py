import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeh import paths  # noqa: E402


def make_package_root(complete=True):
    root = Path(tempfile.mkdtemp(prefix="aeh-package-root-"))
    data = root / "data"
    data.mkdir()
    if complete:
        (data / "core").mkdir()
        (data / "schemas").mkdir()
        (data / "core" / "workflow.yaml").write_text("contract: test\n", encoding="utf-8")
        (data / "schemas" / "manifest.schema.json").write_text("{}\n", encoding="utf-8")
    return root


class TestResourcePaths(unittest.TestCase):
    def test_source_tree_root(self):
        self.assertEqual(Path(paths.ae_root()), ROOT)

    def test_all_resource_domains_exist(self):
        for domain in sorted(paths.RESOURCE_DOMAINS):
            with self.subTest(domain=domain):
                self.assertTrue(Path(paths.join(domain)).is_dir())

    def test_packaged_bundle_has_priority(self):
        package_root = make_package_root()
        with mock.patch.object(paths, "_package_files", return_value=package_root):
            self.assertEqual(Path(paths.ae_root()), package_root / "data")

    def test_incomplete_packaged_bundle_is_not_hidden_by_source_fallback(self):
        package_root = make_package_root(complete=False)
        with mock.patch.object(paths, "_package_files", return_value=package_root):
            with self.assertRaisesRegex(paths.AehResourceError, "incomplete"):
                paths.ae_root()

    def test_missing_package_and_source_raise_explicit_error(self):
        package_root = Path(tempfile.mkdtemp(prefix="aeh-empty-package-"))
        fake_module = Path(tempfile.mkdtemp(prefix="aeh-empty-source-")) / "aeh" / "paths.py"
        fake_module.parent.mkdir()
        with mock.patch.object(paths, "_package_files", return_value=package_root), \
             mock.patch.object(paths, "__file__", str(fake_module)):
            with self.assertRaisesRegex(paths.AehResourceError, "not found"):
                paths.ae_root()

    def test_unknown_domain_is_rejected(self):
        with self.assertRaisesRegex(paths.AehResourceError, "unknown"):
            paths.join("unknown", "file.txt")

    def test_domain_escape_is_rejected(self):
        with self.assertRaisesRegex(paths.AehResourceError, "escapes"):
            paths.join("core", "..", "schemas", "manifest.schema.json")

    def test_resolution_is_deterministic(self):
        self.assertEqual(paths.ae_root(), paths.ae_root())
        self.assertEqual(paths.join("core", "workflow.yaml"),
                         paths.join("core", "workflow.yaml"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
