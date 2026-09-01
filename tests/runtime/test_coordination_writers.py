import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aeh.runtime.coordination as coordination


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


class CoordinationWriterCase(unittest.TestCase):
    required_surface = (
        "reserve_change_id",
        "finalize_reservation",
        "acquire_lease",
        "renew_lease",
        "release_lease",
        "recover_lease",
        "begin_mutation",
        "finalize_mutation",
        "abort_mutation",
        "assert_workspace_maintenance_allowed",
        "coordination_drain_status",
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "target"
        self.state = self.root / "state"
        self.target.mkdir()
        self.change_id = "CHG-2026-0001"
        self.change = self.target / ".aeh" / "changes" / self.change_id
        self.change.mkdir(parents=True)
        (self.change / "change.yaml").write_text("state: initial\n", encoding="utf-8")
        self.token = self.root / "worker.token"

    def tearDown(self):
        self.temp.cleanup()

    def _surface(self):
        missing = [name for name in self.required_surface
                   if not hasattr(coordination, name)]
        self.assertEqual(
            missing, [],
            "M6_3B_COORDINATION_WRITERS_REQUIRED: " + ",".join(missing),
        )

    def _acquire(self, token=None, holder="worker-a", now=NOW):
        self._surface()
        return coordination.acquire_lease(
            str(self.target), self.change_id, holder_ref=holder,
            token_file=str(token or self.token), ttl_seconds=60,
            state_root=str(self.state), now=now,
        )

    def test_required_writer_surface_exists(self):
        self._surface()

    def test_acquire_renew_release_and_redaction(self):
        acquired = self._acquire()
        self.assertEqual(acquired["status"], "LEASE_ACQUIRED")
        self.assertTrue(self.token.is_file())
        token_bytes = self.token.read_bytes()
        encoded = json.dumps(acquired, sort_keys=True)
        self.assertNotIn(str(self.token), encoded)
        self.assertNotIn(token_bytes.decode("ascii"), encoded)

        renewed = coordination.renew_lease(
            str(self.target), self.change_id, token_file=str(self.token),
            expected_revision=acquired["lease_revision"], ttl_seconds=120,
            state_root=str(self.state), now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(renewed["status"], "LEASE_RENEWED")
        released = coordination.release_lease(
            str(self.target), self.change_id, token_file=str(self.token),
            expected_revision=renewed["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(released["status"], "LEASE_RELEASED")
        self.assertTrue(self.token.exists(), "token deletion belongs to caller")
        status = coordination.coordination_status(
            str(self.target), self.change_id, state_root=str(self.state))
        self.assertEqual(status["status"], "RELEASED")

    def test_change_and_workspace_conflicts(self):
        self._acquire()
        with self.assertRaises(coordination.CoordinationError) as same:
            coordination.acquire_lease(
                str(self.target), self.change_id, holder_ref="worker-b",
                token_file=str(self.root / "other.token"), ttl_seconds=60,
                state_root=str(self.state), now=NOW,
            )
        self.assertIn("BLOCKED_CHANGE_LEASE_CONFLICT", str(same.exception))

        other_id = "CHG-2026-0002"
        other = self.target / ".aeh" / "changes" / other_id
        other.mkdir()
        (other / "change.yaml").write_text("state: initial\n", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as workspace:
            coordination.acquire_lease(
                str(self.target), other_id, holder_ref="worker-b",
                token_file=str(self.root / "workspace.token"), ttl_seconds=60,
                state_root=str(self.state), now=NOW,
            )
        self.assertIn("BLOCKED_WORKSPACE_LEASE_CONFLICT", str(workspace.exception))

    def test_token_revision_truth_and_clock_fail_closed(self):
        acquired = self._acquire()
        wrong = self.root / "wrong.token"
        wrong.write_text("0" * 64, encoding="ascii")
        with self.assertRaises(coordination.CoordinationError) as token:
            coordination.renew_lease(
                str(self.target), self.change_id, token_file=str(wrong),
                expected_revision=acquired["lease_revision"], ttl_seconds=60,
                state_root=str(self.state), now=NOW + timedelta(seconds=1))
        self.assertIn("BLOCKED_LEASE_TOKEN_INVALID", str(token.exception))
        with self.assertRaises(coordination.CoordinationError) as revision:
            coordination.renew_lease(
                str(self.target), self.change_id, token_file=str(self.token),
                expected_revision=99, ttl_seconds=60,
                state_root=str(self.state), now=NOW + timedelta(seconds=1))
        self.assertIn("BLOCKED_STALE_LEASE_REVISION", str(revision.exception))
        with self.assertRaises(coordination.CoordinationError) as clock:
            coordination.renew_lease(
                str(self.target), self.change_id, token_file=str(self.token),
                expected_revision=acquired["lease_revision"], ttl_seconds=60,
                state_root=str(self.state), now=NOW - timedelta(seconds=1))
        self.assertIn("BLOCKED_COORDINATION_CLOCK_ROLLBACK", str(clock.exception))
        (self.change / "change.yaml").write_text("state: drift\n", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as truth:
            coordination.release_lease(
                str(self.target), self.change_id, token_file=str(self.token),
                expected_revision=acquired["lease_revision"],
                state_root=str(self.state), now=NOW + timedelta(seconds=2))
        self.assertIn("BLOCKED_CHANGE_TRUTH_DRIFT", str(truth.exception))

    def test_expired_recovery_is_token_free_and_serialized(self):
        acquired = self._acquire()
        with self.assertRaises(coordination.CoordinationError) as live:
            coordination.recover_lease(
                str(self.target), self.change_id,
                expected_revision=acquired["lease_revision"],
                expected_truth_hash=acquired["change_truth_sha256"],
                state_root=str(self.state), now=NOW + timedelta(seconds=30))
        self.assertIn("BLOCKED_LIVE_LEASE", str(live.exception))
        recovered = coordination.recover_lease(
            str(self.target), self.change_id,
            expected_revision=acquired["lease_revision"],
            expected_truth_hash=acquired["change_truth_sha256"],
            state_root=str(self.state), now=NOW + timedelta(seconds=61))
        self.assertEqual(recovered["status"], "LEASE_RECOVERED")
        with self.assertRaises(coordination.CoordinationError) as stale:
            coordination.recover_lease(
                str(self.target), self.change_id,
                expected_revision=acquired["lease_revision"],
                expected_truth_hash=acquired["change_truth_sha256"],
                state_root=str(self.state), now=NOW + timedelta(seconds=62))
        self.assertIn("BLOCKED_STALE_LEASE_REVISION", str(stale.exception))

    def test_mutation_finalize_and_abort_contract(self):
        acquired = self._acquire()
        begun = coordination.begin_mutation(
            str(self.target), self.change_id, operation="TEST_MUTATE",
            token_file=str(self.token),
            expected_revision=acquired["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=1))
        (self.change / "result.yaml").write_text("ok: true\n", encoding="utf-8")
        finalized = coordination.finalize_mutation(
            str(self.target), self.change_id,
            operation_id=begun["operation_id"], token_file=str(self.token),
            expected_revision=begun["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=2))
        self.assertEqual(finalized["status"], "MUTATION_FINALIZED")

        begun2 = coordination.begin_mutation(
            str(self.target), self.change_id, operation="TEST_ABORT",
            token_file=str(self.token),
            expected_revision=finalized["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=3))
        aborted = coordination.abort_mutation(
            str(self.target), self.change_id,
            operation_id=begun2["operation_id"], token_file=str(self.token),
            expected_revision=begun2["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=4))
        self.assertEqual(aborted["status"], "MUTATION_ABORTED")

    def test_abort_after_truth_drift_retains_unresolved_operation(self):
        acquired = self._acquire()
        begun = coordination.begin_mutation(
            str(self.target), self.change_id, operation="TEST_CRASH",
            token_file=str(self.token),
            expected_revision=acquired["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=1))
        (self.change / "partial.yaml").write_text("partial: true\n", encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError) as drift:
            coordination.abort_mutation(
                str(self.target), self.change_id,
                operation_id=begun["operation_id"], token_file=str(self.token),
                expected_revision=begun["lease_revision"],
                state_root=str(self.state), now=NOW + timedelta(seconds=2))
        self.assertIn("BLOCKED_CHANGE_TRUTH_DRIFT", str(drift.exception))
        with self.assertRaises(coordination.CoordinationError) as active:
            coordination.begin_mutation(
                str(self.target), self.change_id, operation="LATER",
                token_file=str(self.token),
                expected_revision=begun["lease_revision"],
                state_root=str(self.state), now=NOW + timedelta(seconds=3))
        self.assertIn("BLOCKED_ACTIVE_OPERATION", str(active.exception))

    def test_maintenance_and_drain_gate(self):
        acquired = self._acquire()
        with self.assertRaises(coordination.CoordinationError) as maintenance:
            coordination.assert_workspace_maintenance_allowed(
                str(self.target), state_root=str(self.state),
                now=NOW + timedelta(seconds=1))
        self.assertIn("BLOCKED_WORKSPACE_LEASE_CONFLICT", str(maintenance.exception))
        blocked = coordination.coordination_drain_status(
            str(self.target), state_root=str(self.state),
            now=NOW + timedelta(seconds=1))
        self.assertEqual(blocked["status"], "BLOCKED_COORDINATION_DRAIN_REQUIRED")
        released = coordination.release_lease(
            str(self.target), self.change_id, token_file=str(self.token),
            expected_revision=acquired["lease_revision"],
            state_root=str(self.state), now=NOW + timedelta(seconds=2))
        self.assertEqual(released["status"], "LEASE_RELEASED")
        coordination.assert_workspace_maintenance_allowed(
            str(self.target), state_root=str(self.state),
            now=NOW + timedelta(seconds=3))
        self.assertEqual(
            coordination.coordination_drain_status(
                str(self.target), state_root=str(self.state),
                now=NOW + timedelta(seconds=3))["status"],
            "COORDINATION_DRAINED")

    def test_reservations_are_monotonic_under_contention(self):
        self._surface()
        results = []
        errors = []
        barrier = threading.Barrier(5)

        def worker(index):
            try:
                barrier.wait()
                results.append(coordination.reserve_change_id(
                    str(self.target), year=2026,
                    reservation_ref="worker-%d" % index,
                    state_root=str(self.state), now=NOW))
            except Exception as exc:  # captured for assertion in parent
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertEqual(errors, [])
        ids = sorted(item["change_id"] for item in results)
        self.assertEqual(len(set(ids)), 5)
        self.assertEqual(ids, ["CHG-2026-%04d" % i for i in range(3, 8)])


if __name__ == "__main__":
    unittest.main()
