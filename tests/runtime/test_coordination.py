import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import jsonschema

import aeh.runtime.coordination as coordination
from aeh import cli
from aeh.doctor import doctor


SHA_A = "a" * 64
SHA_B = "b" * 64
OBSERVED = "2026-08-31T00:00:00+00:00"


class CoordinationCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "target"
        self.target.mkdir()
        (self.target / ".aeh" / "changes" / "CHG-2026-0002").mkdir(parents=True)
        self.state = self.root / "external-state"

    def tearDown(self):
        self.temp.cleanup()

    def _store(self, revision=0):
        return coordination.new_store(SHA_A, OBSERVED, revision=revision)

    def test_identity_aliases_and_repository_common_dir(self):
        previous_cwd = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertEqual(
                coordination.workspace_identity(self.target.name),
                coordination.workspace_identity(str(self.target)),
            )
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(
            coordination.repository_identity(str(self.target), repository_id="repo-A"),
            coordination.repository_identity(str(self.target), repository_id="repo-A"),
        )
        self.assertNotEqual(
            coordination.workspace_identity(str(self.target)),
            coordination.workspace_identity(str(self.root)),
        )

    def test_unsafe_state_roots_fail_closed_without_raw_path(self):
        inside = self.target / "state"
        with self.assertRaises(coordination.CoordinationError) as raised:
            coordination.resolve_store_paths(str(self.target), state_root=str(inside))
        self.assertIn("BLOCKED_COORDINATION_STATE_INSIDE_TARGET", str(raised.exception))
        self.assertNotIn(str(inside), str(raised.exception))
        if os.name == "nt":
            with self.assertRaises(coordination.CoordinationError) as unc:
                coordination.resolve_store_paths(str(self.target), state_root=r"\\server\share\state")
            self.assertIn("BLOCKED_COORDINATION_NETWORK_PATH", str(unc.exception))

    def test_status_not_activated_is_zero_write(self):
        before = set(self.root.rglob("*"))
        status = coordination.coordination_status(
            str(self.target), state_root=str(self.state))
        after = set(self.root.rglob("*"))
        self.assertEqual(status["status"], "NOT_ACTIVATED")
        self.assertEqual(before, after)
        self.assertFalse(self.state.exists())
        encoded = json.dumps(status, sort_keys=True)
        self.assertNotIn(str(self.target), encoded)
        self.assertNotIn(str(self.state), encoded)

    def test_store_atomic_round_trip_and_fault_visibility(self):
        old = self._store(1)
        coordination.write_store_atomic(
            str(self.target), old, state_root=str(self.state))
        self.assertEqual(
            coordination.read_store(str(self.target), state_root=str(self.state)), old)
        new = self._store(2)
        with self.assertRaises(coordination.CoordinationError) as raised:
            coordination.write_store_atomic(
                str(self.target), new, state_root=str(self.state),
                fault="before_replace")
        self.assertIn("BLOCKED_COORDINATION_ATOMIC_WRITE", str(raised.exception))
        self.assertEqual(
            coordination.read_store(str(self.target), state_root=str(self.state)), old)
        coordination.write_store_atomic(
            str(self.target), new, state_root=str(self.state))
        self.assertEqual(
            coordination.read_store(str(self.target), state_root=str(self.state)), new)

    def test_store_malformed_and_unknown_version_block(self):
        paths = coordination.resolve_store_paths(
            str(self.target), state_root=str(self.state))
        paths.repository_dir.mkdir(parents=True)
        paths.store.write_text("{broken", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as malformed:
            coordination.read_store(str(self.target), state_root=str(self.state))
        self.assertIn("BLOCKED_COORDINATION_STORE_INVALID", str(malformed.exception))
        paths.store.write_text(json.dumps({"contract": "coordination.store", "version": 99}), encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as version:
            coordination.read_store(str(self.target), state_root=str(self.state))
        self.assertIn("BLOCKED_COORDINATION_STORE_VERSION", str(version.exception))

    def test_change_truth_stable_and_sensitive(self):
        change = self.target / ".aeh" / "changes" / "CHG-2026-0002"
        (change / "a.yaml").write_bytes(b"a\n")
        first = coordination.change_truth(str(self.target), "CHG-2026-0002")
        second = coordination.change_truth(str(self.target), "CHG-2026-0002")
        self.assertEqual(first, second)
        (change / "a.yaml").write_bytes(b"b\n")
        self.assertNotEqual(
            first["digest"],
            coordination.change_truth(str(self.target), "CHG-2026-0002")["digest"],
        )
        (change / "extra.json").write_text("{}", encoding="utf-8")
        self.assertNotEqual(
            first["digest"],
            coordination.change_truth(str(self.target), "CHG-2026-0002")["digest"],
        )

    def test_change_truth_rejects_temp_remnant(self):
        change = self.target / ".aeh" / "changes" / "CHG-2026-0002"
        (change / "state.aeh-tmp").write_text("partial", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as raised:
            coordination.change_truth(str(self.target), "CHG-2026-0002")
        self.assertIn("BLOCKED_COORDINATION_CHANGE_TEMP", str(raised.exception))

    def test_receipt_is_deterministic_schema_valid_and_redacted(self):
        fields = {
            "operation": "STATUS",
            "outcome": "NOT_ACTIVATED",
            "repository_id_sha256": SHA_A,
            "workspace_id_sha256": SHA_B,
            "change_id": "CHG-2026-0002",
            "change_truth_sha256": SHA_A,
            "store_revision": 0,
            "observed_at": OBSERVED,
        }
        one = coordination.build_receipt(**fields)
        two = coordination.build_receipt(**fields)
        self.assertEqual(one, two)
        schema = json.loads((Path(__file__).parents[2] / "schemas" / "coordination-receipt.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(one, schema)
        rendered = json.dumps(one, sort_keys=True)
        for forbidden in ("token", "credential", "state_root", "workspace_path", "repository_id\""):
            self.assertNotIn(forbidden, rendered)

    def test_shared_lock_excludes_exclusive_until_release(self):
        entered = threading.Event()
        release = threading.Event()

        def reader():
            with coordination.repository_lock(
                    str(self.target), state_root=str(self.state), shared=True,
                    timeout_seconds=1.0, create=True):
                entered.set()
                release.wait(2.0)

        thread = threading.Thread(target=reader)
        thread.start()
        self.assertTrue(entered.wait(1.0))
        with self.assertRaises(coordination.CoordinationError) as raised:
            with coordination.repository_lock(
                    str(self.target), state_root=str(self.state), shared=False,
                    timeout_seconds=0.05, create=True):
                pass
        self.assertIn("BLOCKED_COORDINATION_LOCK_TIMEOUT", str(raised.exception))
        release.set()
        thread.join(2.0)
        with coordination.repository_lock(
                str(self.target), state_root=str(self.state), shared=False,
                timeout_seconds=1.0, create=True):
            pass

    def test_cli_exposes_status_only_and_does_not_activate(self):
        old = os.environ.get("AEH_CONTROLLER_STATE_DIR")
        os.environ["AEH_CONTROLLER_STATE_DIR"] = str(self.state)
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli.main(["coordination", "status", str(self.target)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "NOT_ACTIVATED")
            self.assertFalse(self.state.exists())
            help_output = io.StringIO()
            with contextlib.redirect_stdout(help_output):
                with self.assertRaises(SystemExit):
                    cli.main(["coordination", "acquire", str(self.target)])
            self.assertFalse(self.state.exists())
        finally:
            if old is None:
                os.environ.pop("AEH_CONTROLLER_STATE_DIR", None)
            else:
                os.environ["AEH_CONTROLLER_STATE_DIR"] = old

    def test_doctor_coordination_diagnostic_is_read_only(self):
        old = os.environ.get("AEH_CONTROLLER_STATE_DIR")
        os.environ["AEH_CONTROLLER_STATE_DIR"] = str(self.state)
        try:
            report = doctor.run_doctor(str(self.target), now=None)
            check = next(c for c in report["checks"] if c["check_id"] == "coordination.status")
            self.assertIn(check["status"], ("PASS", "WARN"))
            self.assertFalse(self.state.exists())
        finally:
            if old is None:
                os.environ.pop("AEH_CONTROLLER_STATE_DIR", None)
            else:
                os.environ["AEH_CONTROLLER_STATE_DIR"] = old

    def test_dependency_metadata_unchanged_and_contracts_present(self):
        root = Path(__file__).parents[2]
        setup_text = (root / "setup.py").read_text(encoding="utf-8")
        self.assertNotIn("portalocker", setup_text.lower())
        for name in (
                "coordination-store", "change-lease", "workspace-binding",
                "coordination-receipt"):
            schema = json.loads((root / "schemas" / (name + ".schema.json")).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_runtime_boundary_is_explicit(self):
        root = Path(__file__).parents[2]
        text = (root / "src" / "aeh" / "runtime" / "coordination.py").read_text(encoding="utf-8").lower()
        self.assertIn("single-host", text)
        self.assertIn("local-filesystem", text)
        self.assertIn("does not provide cross-host", text)


if __name__ == "__main__":
    unittest.main()
