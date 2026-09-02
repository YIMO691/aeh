import inspect
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest

import jsonschema
import yaml

from aeh import ci
from aeh.integrations import aew
from aeh.runtime import change as change_module
from aeh.runtime import coordination


CHANGE_ID = "CHG-2026-0001"
RED_SIGNATURE = "M6_3C_STABLE_READERS_AEW_V2_REQUIRED"


def _write_change(target, marker):
    change_dir = Path(target, ".aeh", "changes", CHANGE_ID)
    change_dir.mkdir(parents=True)
    body = {
        "change_id": CHANGE_ID,
        "title": marker,
        "classification": {"level": "CRITICAL"},
        "workflow": {"level": "CRITICAL", "phases": ["SPEC"]},
        "state": {"current": "SPEC", "previous": "GROUND"},
        "gates": {"classification": "PASS", "grounding": "PASS", "spec": "PASS"},
    }
    Path(change_dir, "change.yaml").write_text(
        yaml.safe_dump(body, sort_keys=True), encoding="utf-8")
    return change_dir


def _shared_reader_worker(target, state_root, ready, release, output):
    try:
        def read_value():
            ready.set()
            if not release.wait(10):
                raise RuntimeError("reader release timeout")
            return "reader-complete"

        result = coordination.stable_change_snapshot(
            target, CHANGE_ID, read_value, state_root=state_root,
            timeout_seconds=5.0)
        output.put(("ok", result["value"]))
    except BaseException as exc:
        output.put(("error", type(exc).__name__ + ":" + str(exc)))


def _exclusive_lock_worker(target, state_root, ready):
    with coordination.repository_lock(
            target, state_root=state_root, shared=False, timeout_seconds=5.0):
        ready.set()
        time.sleep(30)


class StableReaderContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aeh-m63c-")
        self.root = Path(self.temp.name)
        self.target = self.root / "target"
        self.state = self.root / "state"
        self.target.mkdir()
        _write_change(self.target, "workspace-a")

    def tearDown(self):
        self.temp.cleanup()

    def _require_surface(self):
        if not hasattr(coordination, "stable_change_snapshot"):
            self.skipTest(RED_SIGNATURE + ": stable_change_snapshot missing")

    def _acquire(self):
        token = self.root / "reader-authority.token"
        result = coordination.acquire_lease(
            str(self.target), CHANGE_ID, holder_ref="reader-contract",
            token_file=str(token), ttl_seconds=120, state_root=str(self.state))
        return token, result

    def test_required_surface_schema_and_bounded_ci_budget(self):
        problems = []
        if not hasattr(coordination, "stable_change_snapshot"):
            problems.append("stable_change_snapshot missing")
        if "coordination_state_root" not in inspect.signature(
                change_module.change_status).parameters:
            problems.append("change_status stable-reader argument missing")
        if "coordination_state_root" not in inspect.signature(aew.export_change).parameters:
            problems.append("AEW stable-reader argument missing")
        if "coordination_state_root" not in inspect.signature(ci.verify).parameters:
            problems.append("CI replay stable-reader argument missing")

        repo_root = Path(__file__).resolve().parents[2]
        schema = json.loads(Path(
            repo_root, "schemas", "aew-governance-adapter.schema.json"
        ).read_text(encoding="utf-8"))
        if schema.get("properties", {}).get("version", {}).get("const") != 2:
            problems.append("AEW adapter schema is not v2")
        required = set(schema.get("required", []))
        if "coordination" not in required:
            problems.append("AEW v2 coordination object missing")

        workflow = yaml.safe_load(Path(
            repo_root, ".github", "workflows", "regression.yml"
        ).read_text(encoding="utf-8"))
        regression_timeout = workflow["jobs"]["regression"]["timeout-minutes"]
        cleanroom_timeout = workflow["jobs"]["cleanroom-wheel"]["timeout-minutes"]
        if not 30 <= regression_timeout <= 60:
            problems.append("regression timeout is not bounded 30..60 minutes")
        if cleanroom_timeout > 20:
            problems.append("clean-room timeout was broadened without need")

        self.assertEqual(problems, [], RED_SIGNATURE + ": " + "; ".join(problems))

    def test_legacy_snapshot_is_stable_and_does_not_create_store(self):
        self._require_surface()
        change_path = self.target / ".aeh" / "changes" / CHANGE_ID / "change.yaml"
        before = change_path.read_bytes()
        result = coordination.stable_change_snapshot(
            str(self.target), CHANGE_ID,
            lambda: change_path.read_text(encoding="utf-8"),
            state_root=str(self.state))
        self.assertEqual(result["status"], "SNAPSHOT_COMPLETE")
        self.assertEqual(result["coordination"]["state"], "NOT_ACTIVATED")
        self.assertEqual(change_path.read_bytes(), before)
        stores = list(self.state.rglob("store.json")) if self.state.exists() else []
        self.assertEqual(stores, [])

    def test_active_operation_and_truth_drift_fail_closed(self):
        self._require_surface()
        token, acquired = self._acquire()
        begun = coordination.begin_mutation(
            str(self.target), CHANGE_ID, operation="TEST_ACTIVE",
            token_file=str(token), expected_revision=acquired["lease_revision"],
            state_root=str(self.state))
        with self.assertRaises(coordination.CoordinationError) as active:
            coordination.stable_change_snapshot(
                str(self.target), CHANGE_ID, lambda: None,
                state_root=str(self.state))
        self.assertIn("BLOCKED_ACTIVE_OPERATION", str(active.exception))
        coordination.abort_mutation(
            str(self.target), CHANGE_ID, begun["operation_id"], str(token),
            begun["lease_revision"], state_root=str(self.state))
        Path(self.target, ".aeh", "changes", CHANGE_ID, "drift.yaml").write_text(
            "drift: true\n", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as drift:
            coordination.stable_change_snapshot(
                str(self.target), CHANGE_ID, lambda: None,
                state_root=str(self.state))
        self.assertIn("BLOCKED_CHANGE_TRUTH_DRIFT", str(drift.exception))

    def test_real_process_shared_readers_exclude_writer(self):
        self._require_surface()
        token, acquired = self._acquire()
        context = multiprocessing.get_context("spawn")
        release = context.Event()
        ready = [context.Event(), context.Event()]
        output = context.Queue()
        readers = [context.Process(
            target=_shared_reader_worker,
            args=(str(self.target), str(self.state), ready[index], release, output),
        ) for index in range(2)]
        for process in readers:
            process.start()
        try:
            self.assertTrue(ready[0].wait(10), "first reader did not enter snapshot")
            self.assertTrue(ready[1].wait(10), "second reader did not enter snapshot")
            with self.assertRaises(coordination.CoordinationError) as blocked:
                coordination.begin_mutation(
                    str(self.target), CHANGE_ID, operation="WRITER_WHILE_READERS",
                    token_file=str(token), expected_revision=acquired["lease_revision"],
                    state_root=str(self.state), timeout_seconds=0.25)
            self.assertIn("BLOCKED_COORDINATION_LOCK_TIMEOUT", str(blocked.exception))
        finally:
            release.set()
            for process in readers:
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
        results = [output.get(timeout=3), output.get(timeout=3)]
        self.assertEqual(sorted(results), [("ok", "reader-complete")] * 2)

    def test_process_death_releases_os_lock_but_not_logical_lease(self):
        self._require_surface()
        _token, _acquired = self._acquire()
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        process = context.Process(
            target=_exclusive_lock_worker,
            args=(str(self.target), str(self.state), ready))
        process.start()
        self.assertTrue(ready.wait(10), "child did not acquire exclusive lock")
        process.terminate()
        process.join(10)
        with coordination.repository_lock(
                str(self.target), state_root=str(self.state), shared=False,
                timeout_seconds=2.0):
            pass
        with self.assertRaises(coordination.CoordinationError) as logical:
            coordination.acquire_lease(
                str(self.target), CHANGE_ID, holder_ref="competitor",
                token_file=str(self.root / "competitor.token"), ttl_seconds=120,
                state_root=str(self.state))
        self.assertIn("BLOCKED_CHANGE_LEASE_CONFLICT", str(logical.exception))

    def test_status_and_aew_v2_share_redacted_deterministic_provenance(self):
        self._require_surface()
        token, acquired = self._acquire()
        token_canary = token.read_text(encoding="ascii").strip()
        status = change_module.change_status(
            str(self.target), CHANGE_ID,
            coordination_state_root=str(self.state))
        first = aew.export_change(
            str(self.target), CHANGE_ID, task_id="TASK-1", run_id="RUN-1",
            coordination_state_root=str(self.state))
        second = aew.export_change(
            str(self.target), CHANGE_ID, task_id="TASK-1", run_id="RUN-1",
            coordination_state_root=str(self.state))
        self.assertEqual(first, second)
        self.assertEqual(first["version"], 2)
        self.assertEqual(first["coordination"]["state"], "ACTIVE")
        self.assertEqual(
            first["coordination"]["lease_revision"], acquired["lease_revision"])
        self.assertEqual(status["coordination"], first["coordination"])
        rendered = json.dumps({"status": status, "aew": first}, sort_keys=True)
        for forbidden in (token_canary, str(token), str(self.state), str(self.target)):
            self.assertNotIn(forbidden, rendered)
        schema = json.loads(Path(
            Path(__file__).resolve().parents[2], "schemas",
            "aew-governance-adapter.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(first, schema)

    def test_distinct_workspace_snapshots_do_not_cross_artifacts(self):
        self._require_surface()
        other = self.root / "other"
        other.mkdir()
        _write_change(other, "workspace-b")
        first = coordination.stable_change_snapshot(
            str(self.target), CHANGE_ID,
            lambda: Path(self.target, ".aeh", "changes", CHANGE_ID,
                         "change.yaml").read_text(encoding="utf-8"),
            state_root=str(self.state))
        second = coordination.stable_change_snapshot(
            str(other), CHANGE_ID,
            lambda: Path(other, ".aeh", "changes", CHANGE_ID,
                         "change.yaml").read_text(encoding="utf-8"),
            state_root=str(self.state))
        self.assertIn("workspace-a", first["value"])
        self.assertNotIn("workspace-b", first["value"])
        self.assertIn("workspace-b", second["value"])
        self.assertNotEqual(
            first["coordination"]["workspace_id_sha256"],
            second["coordination"]["workspace_id_sha256"])

    def test_ci_replay_declares_stable_snapshot_binding(self):
        self._require_surface()
        parameters = inspect.signature(ci.verify).parameters
        self.assertIn("coordination_state_root", parameters)
        source = inspect.getsource(ci.verify)
        self.assertIn("stable_change_snapshot", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
