# M6.3A Frozen Decisions

- D-001: Scope is single-host and local-filesystem only; UNC/network and
  unprovable path safety are blocked.
- D-002: Controller state lives below the existing external
  `AEH_CONTROLLER_STATE_DIR`, under `coordination-v1/repositories/<repo-hash>`.
- D-003: Repository identity uses an explicit stable identifier when supplied,
  otherwise Git common-directory identity, with a safe canonical-target
  fallback. Workspace identity always hashes the physical canonical workspace.
- D-004: One canonical JSON store exists per repository. Unknown contract or
  version is never migrated implicitly.
- D-005: POSIX uses `fcntl.flock`; Windows uses byte-zero `msvcrt.locking`.
  Acquisition is bounded and timeout is
  `BLOCKED_COORDINATION_LOCK_TIMEOUT`.
- D-006: Read-only status and Doctor never create the state root, lock, store,
  receipt, or Change artifact.
- D-007: Change truth includes every regular file in the exact Change directory,
  sorted by POSIX relative path with length and SHA-256. Links, reparse entries,
  unsupported types, temporary remnants, overflow, and read drift block.
- D-008: Receipt digest is SHA-256 over canonical JSON excluding the digest
  field. Receipts contain only hashes and bounded references.
- D-009: No new runtime dependency is permitted.
- D-010: Acquire/renew/release/recover, Change-ID reservation, mutator CAS,
  stable readers, and AEW v2 remain deferred to M6.3B/C.
- D-011: Final review exposed a CRITICAL workflow bridge mismatch: the workflow
  reaches REGRESSION while the legacy verify runtime accepted only
  GREEN/REFACTOR/VERIFY and attempted the legacy VERIFY state. The Controller
  returns this Change to REFACTOR only to regenerate locked evidence after the
  bridge and idempotent REFACTOR rerun fixes, then replays INTEGRATION,
  RUNTIME_PLATFORM_VERIFY, and REGRESSION. This grants no approval and does not
  bypass VERIFY or MERGE_GATE.
- D-012: The first authorized VERIFY attempt correctly failed closed because
  the verifier passed both a display command and the locked argv to the
  constrained executor. The verifier now gives locked argv precedence, matching
  GREEN/REFACTOR execution semantics. The Controller repeats REFACTOR and the
  complete regression before retrying VERIFY; the MERGE_GATE approval remains
  independently signed and is not treated as technical evidence.
- D-013: The next VERIFY attempt passed all technical executions but blocked on
  seven orphan supporting files. Their Test Plan targets are completed to match
  the already-frozen TEST-001 intent (the complete additive substrate,
  packaging, and fail-closed contracts). No test source, assertion, RED
  signature, or lock hash changes; VERIFY reruns every technical execution.
