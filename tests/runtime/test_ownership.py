import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from aeh.runtime import ownership as omod


class TestControllerOwnership(unittest.TestCase):
    def _workspace(self):
        target = tempfile.mkdtemp(prefix="aeh-owner-target-")
        cid = "CHG-2026-0001"
        cdir = os.path.join(target, ".aeh", "changes", cid)
        os.makedirs(cdir)
        with open(os.path.join(cdir, "change.yaml"), "w", encoding="utf-8") as stream:
            stream.write("change_id: CHG-2026-0001\n")
        return target, cid, cdir

    def test_checkpoint_round_trip_and_diff(self):
        target, cid, cdir = self._workspace()
        state = tempfile.mkdtemp(prefix="aeh-owner-state-")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: state}):
            omod.record_checkpoint(target, cid)
            self.assertEqual(omod.assert_checkpoint(target, cid)["change_id"], cid)
            with open(os.path.join(cdir, "tasks.yaml"), "w", encoding="utf-8") as stream:
                stream.write("tasks: []\n")
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_MACHINE_TRUTH_PROVENANCE: added=tasks.yaml"):
                omod.assert_checkpoint(target, cid)

    def test_state_root_inside_target_rejected(self):
        target, cid, _ = self._workspace()
        inside = os.path.join(target, ".aeh", "controller-state")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: inside}):
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_CONTROLLER_STATE_INSIDE_TARGET"):
                omod.record_checkpoint(target, cid)

    def test_missing_checkpoint_fails_closed(self):
        target, cid, _ = self._workspace()
        state = tempfile.mkdtemp(prefix="aeh-owner-state-")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: state}):
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_CONTROLLER_CHECKPOINT_MISSING"):
                omod.assert_checkpoint(target, cid)

    def test_unavailable_state_root_is_a_blocked_error(self):
        target, cid, _ = self._workspace()
        state_file = os.path.join(tempfile.mkdtemp(prefix="aeh-owner-state-"), "not-a-dir")
        with open(state_file, "w", encoding="utf-8") as stream:
            stream.write("occupied\n")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: state_file}):
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_CONTROLLER_CHECKPOINT_UNAVAILABLE"):
                omod.record_checkpoint(target, cid)

    def test_machine_truth_file_symlink_is_rejected_when_supported(self):
        target, cid, cdir = self._workspace()
        state = tempfile.mkdtemp(prefix="aeh-owner-state-")
        external = os.path.join(tempfile.mkdtemp(prefix="aeh-owner-link-"), "truth.yaml")
        with open(external, "w", encoding="utf-8") as stream:
            stream.write("tasks: []\n")
        link = os.path.join(cdir, "tasks.yaml")
        try:
            os.symlink(external, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: state}):
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_MACHINE_TRUTH_SYMLINK"):
                omod.record_checkpoint(target, cid)

    def test_change_workspace_symlink_is_rejected_when_supported(self):
        target, cid, cdir = self._workspace()
        state = tempfile.mkdtemp(prefix="aeh-owner-state-")
        with mock.patch.dict(os.environ, {omod.STATE_DIR_ENV: state}):
            omod.record_checkpoint(target, cid)
            backing = cdir + "-backing"
            os.replace(cdir, backing)
            try:
                os.symlink(backing, cdir, target_is_directory=True)
            except (OSError, NotImplementedError):
                os.replace(backing, cdir)
                self.skipTest("directory symlink creation unavailable")
            with self.assertRaisesRegex(omod.OwnershipError,
                                        "BLOCKED_MACHINE_TRUTH_SYMLINK"):
                omod.assert_checkpoint(target, cid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
