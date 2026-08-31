# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Coordination remains a single-host local-filesystem protocol using standard-library locking, atomic file operations, and cryptographic hashing.
- AC-001-01 (invariant) Unsupported network or cross-host state is rejected or explicitly outside the assurance claim.
## REQ-002 [CONSTRAINT] M6.3B is delivered after M6.3A and before M6.3C as a separate Change, branch, PR, approval chain, and rollback unit.
- AC-002-01 (invariant) CHG-2026-0002 credentials and approvals are not reused for CHG-2026-0003.
## REQ-003 [DESIRED] Bootstrap, repair, upgrade, rollback, and GitHub configuration apply paths use a workspace-maintenance guard and downgrade obeys the coordination drain Gate.
- AC-003-01 (automated) Maintenance can run when the workspace has no live or expired-unrecovered writer authority and blocks otherwise; drained rollback succeeds without deleting the external store.
- AC-003-02 (invariant) No force or bypass flag can install an older writer while reservations, leases, active operations, or truth mismatches remain unresolved.
## REQ-004 [DESIRED] Change allocation uses a repository-scoped monotonic external reservation and atomic Change creation so concurrent creators never duplicate or reuse an identifier.
- AC-004-01 (automated) Concurrent change-new processes receive distinct increasing identifiers and exactly one complete schema-valid Change for every committed reservation.
- AC-004-02 (invariant) A crash may consume an identifier but a pending, abandoned, or committed reservation is never reused or silently deleted.
## REQ-005 [DESIRED] Coordination acquire creates a bounded WRITE lease bound to repository, physical workspace, Change truth, holder, external token hash, revision, and expiry.
- AC-005-01 (automated) Acquire accepts one safe request, exclusively creates the external token file, and blocks same-Change or same-workspace conflicts with stable codes.
- AC-005-02 (invariant) Token bytes and token-file paths never enter the repository, Change artifacts, receipts, normal output, errors, or logs.
## REQ-006 [DESIRED] Every public Change-mutating CLI path and direct Python entry point uses one begin-execute-finalize-or-abort coordination wrapper with optimistic truth CAS.
- AC-006-01 (automated) Transition, repair, ground, spec, test-design, red, green, refactor, verify, approve, review-related writes, traceability, and Controller checkpoint updates block without valid lease context after activation.
- AC-006-02 (invariant) Begin and finalize validate token, revision, identity, time, active operation, and Change truth; nested transitions reuse the active context and cannot open a bypass transaction.
## REQ-007 [DESIRED] Existing never-coordinated Changes activate lazily without rewriting their artifacts and continue to operate manually without AEW once a valid lease is acquired.
- AC-007-01 (automated) First acquire records current legacy Change truth, manual acquire-mutate-release succeeds, and existing fixtures upgrade without data loss.
- AC-007-02 (invariant) M6.3B preserves existing approvals, evidence, private data, transaction journals, v1 ownership checkpoints, and the already-merged M6.3A contracts.
## REQ-008 [DESIRED] Failed or crashed mutations never publish an accepted mixed truth and leave deterministic state for retry, expiry, or separately governed reconciliation.
- AC-008-01 (automated) Faults before execution, after begin, before Change replace, and before finalize yield either unchanged truth with an abort or a retained unresolved operation that blocks later writers.
- AC-008-02 (invariant) Abort clears an operation only when current truth still equals the pre-operation truth; changed truth remains fail-closed.
## REQ-009 [DESIRED] M6.3B remains cross-platform, independently reviewable, and regression-safe across the supported Python and operating-system matrix.
- AC-009-01 (automated) Focused concurrency tests, full regression, docs check, wheel build, clean-room install, doctor, repair, upgrade/rollback, M4/M5, and CI replay pass.
- AC-009-02 (invariant) The slice introduces no new third-party runtime dependency and does not claim cross-host or network-filesystem correctness.
## REQ-010 [DESIRED] Renew and release enforce exact token, identity, expected revision, live time, no active operation, and unchanged accepted Change truth.
- AC-010-01 (automated) Valid renew and release advance revisions while stale revision, wrong token, expiry, truth drift, and active-operation cases fail closed.
- AC-010-02 (invariant) Release retains a RELEASED tombstone and never deletes the caller-owned token file or historical coordination state.
## REQ-011 [DESIRED] Token-free recovery is allowed only for an expired lease with exact expected revision and truth, no active operation, and deterministic serialized race handling.
- AC-011-01 (automated) Exactly one concurrent eligible recovery writes a RECOVERED tombstone and later attempts return deterministic stale or already-recovered outcomes.
- AC-011-02 (invariant) Live leases, truth drift, unresolved operations, clock rollback, malformed state, and unsupported versions cannot be force-recovered.
