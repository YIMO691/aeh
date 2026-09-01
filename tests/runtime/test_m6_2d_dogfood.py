import hashlib
import os
from pathlib import Path
import unittest
from unittest import mock

import yaml

from aeh.runtime import ownership


WHEEL_SHA256 = "398ac2938d8c36bfcb483d1d1ef51ecbd650361a9bacc5c5d6ea78123a10764f"
WORKFLOW_SHA256 = "f283942a0c2ad937ea44ba5b8b4ae86628d0824e5e554c5c8776383f789b5ad8"
WHEEL_URL = (
    "https://github.com/YIMO691/aeh/releases/download/m6.3b-dogfood-1/"
    "adaptive_engineering_harness-0.3.0.post6.dev0-py3-none-any.whl"
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

        if source != runtime:
            self.fail("M6_2D_POLICY_UNCONFIGURED")
        if (
            source["workflow"].get("expected_sha256") != WORKFLOW_SHA256
            or artifact.get("url") != WHEEL_URL
            or artifact.get("sha256") != WHEEL_SHA256
        ):
            self.fail("M6_2D_POLICY_UNCONFIGURED")
        self.assertEqual(source["required_check"], {
            "name": "AEH assurance / verify",
            "app_id": 15368,
        })
        workflow = Path(".github/workflows/aeh-assurance.yml").read_bytes()
        text = workflow.decode("utf-8")
        if "pip install --no-deps" in text:
            self.fail("M6_2D_DEPENDENCY_INSTALL_BYPASSED")
        self.assertEqual(source["workflow"]["expected_sha256"], WORKFLOW_SHA256)
        self.assertEqual(artifact["url"], WHEEL_URL)
        self.assertEqual(artifact["sha256"], WHEEL_SHA256)
        self.assertEqual(hashlib.sha256(workflow).hexdigest(), WORKFLOW_SHA256)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", text)
        self.assertIn("actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97", text)
        self.assertIn(WHEEL_SHA256, text)
        self.assertIn('python -m pip install "$RUNNER_TEMP/$AEH_WHEEL_FILENAME"', text)
        self.assertIn("snapshot-run --policy core/ci-enforcement-policy.yaml", text)
        self.assertIn("verify-event --event", text)
        self.assertIn("--policy core/ci-enforcement-policy.yaml --report", text)


if __name__ == "__main__":
    unittest.main()
