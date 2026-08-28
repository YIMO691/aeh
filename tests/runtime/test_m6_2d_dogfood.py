import hashlib
import os
from pathlib import Path
import unittest
from unittest import mock

import yaml

from aeh.runtime import ownership


WHEEL_SHA256 = "9e827970a9b45e515a6101afbd26d5df3a50e158e4ac182bdcd5d9b9e4b03893"
WORKFLOW_SHA256 = "35b9ec52e9d1874f7b58d23243e8522afbb6074550c2b8ee0b15c37639751ea5"
WHEEL_URL = (
    "https://github.com/YIMO691/aeh/releases/download/m6.2d-dogfood-1/"
    "adaptive_engineering_harness-0.3.0.dev0-py3-none-any.whl"
)


class TestM62dDogfoodPolicy(unittest.TestCase):
    def test_cross_volume_controller_state_is_outside_target(self):
        with mock.patch.dict(os.environ, {ownership.STATE_DIR_ENV: r"C:\aeh-controller-state"}):
            with mock.patch.object(ownership.os.path, "commonpath", side_effect=ValueError("different drives")):
                try:
                    root = ownership.state_root(r"D:\aeh-repository")
                except ownership.OwnershipError:
                    self.fail("M6_2D_CROSS_VOLUME_STATE_BLOCKED")
        self.assertEqual(root, ownership._canonical(r"C:\aeh-controller-state"))

    def test_exact_policy_and_workflow_are_committed(self):
        source = yaml.safe_load(Path("core/ci-enforcement-policy.yaml").read_text(encoding="utf-8"))
        runtime = yaml.safe_load(
            Path(".aeh/runtime/core/ci-enforcement-policy.yaml").read_text(encoding="utf-8")
        )
        artifact = source["workflow"].get("artifact")
        if not artifact:
            self.fail("M6_2D_POLICY_UNCONFIGURED")

        self.assertEqual(source, runtime)
        self.assertEqual(source["required_check"], {
            "name": "AEH assurance / verify",
            "app_id": 15368,
        })
        self.assertEqual(source["workflow"]["expected_sha256"], WORKFLOW_SHA256)
        self.assertEqual(artifact["url"], WHEEL_URL)
        self.assertEqual(artifact["sha256"], WHEEL_SHA256)
        workflow = Path(".github/workflows/aeh-assurance.yml").read_bytes()
        self.assertEqual(hashlib.sha256(workflow).hexdigest(), WORKFLOW_SHA256)
        text = workflow.decode("utf-8")
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", text)
        self.assertIn("actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97", text)
        self.assertIn(WHEEL_SHA256, text)


if __name__ == "__main__":
    unittest.main()
