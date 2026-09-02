# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Coordination remains a cooperating-process, single-host, local-filesystem protocol using standard-library locking, atomic file operations, and cryptographic hashing.
- AC-001-01 (invariant) Unsupported network or cross-host state is rejected or explicitly outside the assurance claim.
## REQ-002 [CONSTRAINT] M6.3C is delivered after merged M6.3B as a separate Change, branch, PR, approval chain, and rollback unit.
- AC-002-01 (invariant) CHG-2026-0002 and CHG-2026-0003 credentials, lease tokens, and approvals are not reused for CHG-2026-0004.
## REQ-003 [DESIRED] AEW governance export version 2 deterministically binds the exported artifact set to non-secret coordination provenance.
- AC-003-01 (automated) The v2 schema and exporter include protocol version, coordination state, repository hash, workspace hash, lease revision, last accepted truth hash, last receipt digest, and optional external workspace-ref hash from one stable snapshot.
- AC-003-02 (invariant) AEW export contains no raw token, token-file path, repository identifier, workspace path, state-root path, credential, or secret body; identical accepted inputs produce byte-equivalent canonical output.
## REQ-004 [DESIRED] CI replay consumes Change artifacts through the same stable snapshot contract without weakening its existing read-only, no-project-code, and exact-head assurances.
- AC-004-01 (automated) Replay succeeds from one accepted generation and returns a defined non-success verdict when a writer overlaps, an operation is unresolved, or Change truth changes during the read.
- AC-004-02 (invariant) CI replay cannot combine artifacts from different Change generations and cannot activate coordination for a legacy Change.
## REQ-005 [DESIRED] Change status remains token-free and read-only while reporting only a stable Change generation with non-secret coordination provenance.
- AC-005-01 (automated) Status returns stable data for coordinated Changes, reports NOT_ACTIVATED for never-coordinated legacy Changes, and fails closed during overlapping mutation or unresolved truth drift.
- AC-005-02 (invariant) Status does not create or mutate the external store and never exposes a token, token-file path, raw state-root path, or raw workspace path.
## REQ-006 [DESIRED] Change-scoped readers use one bounded shared-lock snapshot primitive that validates coordination state and Change truth before and after reading artifacts.
- AC-006-01 (automated) Concurrent readers coexist, writer begin/finalize is excluded while a snapshot is active, and every successful snapshot has identical pre-read and post-read truth hashes.
- AC-006-02 (invariant) An active operation, accepted-truth mismatch, lock timeout, malformed store, unsupported version, or artifact drift returns a deterministic blocked or inconclusive result and never mixed generations.
## REQ-007 [DESIRED] Coordination receipts and cross-workspace artifacts remain deterministic, schema-valid, redacted, and isolated under accepted, rejected, recovery, and fault paths.
- AC-007-01 (automated) Identical receipt bodies produce identical digests, token canaries are absent from every prohibited sink, and two Changes in distinct workspaces cannot write into each other's Change or declared output artifacts.
- AC-007-02 (invariant) No failure message, receipt, store document, test artifact, repository byte, normal output, or AEW envelope reveals raw lease authority.
## REQ-008 [DESIRED] Current architecture, roadmap, status, decisions, engineering guide, documentation contract, README, and changelog describe exactly the achieved M6.3 coordination boundary and manual operating procedure.
- AC-008-01 (automated) Documentation checks pass and required current documents cover protocol limits, lease lifecycle, stable reads, AEW binding, recovery, drain, rollback, and failure codes.
- AC-008-02 (invariant) Frozen release and archive evidence remain byte-unchanged and the documentation does not claim cross-host, network-filesystem, administrator-proof, or scheduler guarantees.
## REQ-009 [DESIRED] M6.3C remains independently reviewable and completes the supported Windows and Ubuntu, Python 3.10 and 3.11 assurance matrix without an undersized workflow timeout.
- AC-009-01 (automated) Focused stable-reader, AEW, multi-process, redaction, and crossover suites plus full regression, docs check, wheel build, clean-room install, doctor, repair, upgrade/rollback, M4/M5, and CI replay pass.
- AC-009-02 (invariant) The workflow retains bounded execution while allowing the supported full regression to complete on the slowest observed matrix leg and introduces no new third-party runtime dependency.
## REQ-010 [DESIRED] Real multi-process workers exercise barriers, process termination, lock contention, reader/writer overlap, reservation races, recovery races, and partial-write boundaries on Windows and Ubuntu.
- AC-010-01 (automated) Supported-platform tests use independent processes rather than thread-only substitutes and prove unique reservations, exclusive writers, shared readers, crash release of OS locks, retained logical lease blocking, and deterministic recovery serialization.
- AC-010-02 (invariant) Fault injection accepts only complete old state or complete new state; torn state, clock rollback, unsafe aliases, and unresolved operations fail closed.
