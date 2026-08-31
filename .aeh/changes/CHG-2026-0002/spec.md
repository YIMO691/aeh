# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Implementation is limited to the Owner-frozen single-host local-filesystem protocol and does not claim cross-host or network-filesystem correctness.
- AC-001-01 (invariant) Documentation and runtime diagnostics state the single-host/local-filesystem boundary without implying universal exclusion.
## REQ-002 [CONSTRAINT] M6.3A uses only the Python standard library plus existing project dependencies.
- AC-002-01 (automated) Project dependency metadata gains no new runtime dependency.
- AC-002-02 (invariant) Platform locking and atomic-file behavior use Python standard-library facilities on every supported platform.
## REQ-003 [DESIRED] Change truth hashing returns a stable digest for one complete regular-file snapshot and fails closed on unsafe or drifting content.
- AC-003-01 (automated) Repeated hashing of unchanged Change files is stable and any byte, length, or path-set change alters the digest.
- AC-003-02 (invariant) Symlink or reparse entries, unsupported types, temporary remnants, overflow, and read drift never produce accepted truth.
## REQ-004 [DESIRED] Coordination receipts are deterministic canonical JSON records and expose hashes and bounded references without secrets or raw paths.
- AC-004-01 (automated) Identical receipt bodies produce identical SHA-256 digests and validate against the receipt schema.
- AC-004-02 (invariant) Token bytes, token-file paths, raw repository IDs, raw workspace paths, state-root paths, and credential bodies are absent from receipts and errors.
## REQ-005 [DESIRED] Cross-platform shared and exclusive repository-store locks provide bounded acquisition and process-exit safety on supported Windows and POSIX local filesystems.
- AC-005-01 (automated) Concurrent shared readers coexist, an exclusive waiter is excluded until readers release, and timeout uses BLOCKED_COORDINATION_LOCK_TIMEOUT.
- AC-005-02 (invariant) A process crash releases the OS lock without granting or changing logical lease authority.
## REQ-006 [DESIRED] M6.3A exposes only a read-only coordination status surface and package/bootstrap/doctor support; writer commands remain unavailable until M6.3B.
- AC-006-01 (automated) The CLI exposes coordination status, reports NOT_ACTIVATED without mutation, and packages/installs every new schema.
- AC-006-02 (invariant) Acquire, renew, release, recover, reservation, and mutator lease enforcement are not exposed by M6.3A.
## REQ-007 [DESIRED] M6.3A preserves all existing AEH behavior and remains independently revertible without an external coordination store migration.
- AC-007-01 (automated) The full existing test suite, docs check, wheel build, and clean-room bootstrap/doctor/status smoke pass.
- AC-007-02 (invariant) Existing Change files, approvals, evidence, private data, transaction journals, and ownership-v1 checkpoints remain byte-preserved.
## REQ-008 [DESIRED] Repository and physical workspace identities are deterministic, non-secret, and resistant to path aliases within the supported local-filesystem boundary.
- AC-008-01 (automated) Relative and absolute aliases of one safe workspace derive the same identity while distinct Git worktrees derive distinct workspace identities and one repository identity.
- AC-008-02 (invariant) Symlink, junction, reparse, state-root-inside-target, and Windows UNC inputs block with stable failure codes when their safety cannot be proven.
## REQ-009 [DESIRED] The additive coordination-v1 external store is canonical, schema validated, atomically replaced, and never created by read-only inspection.
- AC-009-01 (automated) Atomic replacement fault injection exposes either the prior complete store or the new complete store, never a torn accepted document.
- AC-009-02 (invariant) Malformed, unavailable, unsafe, or unsupported-version state blocks; coordination status and doctor do not create the store.
## REQ-010 [DESIRED] Versioned coordination-store, change-lease, workspace-binding, and coordination-receipt contracts accept frozen legal fixtures and reject malformed or unknown-version state.
- AC-010-01 (automated) All four schemas validate their legal fixtures and reject each illegal fixture through the contract suite.
- AC-010-02 (invariant) Unknown coordination contract or store versions fail closed and are never migrated implicitly.
