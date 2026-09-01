# CHG-2026-0003 design — coordinated writers

## Boundary

M6.3B activates single-host, local-filesystem writer coordination on top of the
M6.3A identity, lock, store, truth, and receipt substrate. It does not add
stable Change readers or AEW v2 export; those remain M6.3C.

## Store and reservation

All store mutation occurs under the repository exclusive lock and writes a
fully schema-validated successor document through the existing atomic replace
primitive. `change new` reserves the next yearly identifier before touching the
repository, creates the Change directory and initial `change.yaml` atomically,
then commits the reservation with the resulting Change-truth hash. A failed or
crashed creation consumes the reservation; recovery may commit a complete
Change or mark an incomplete reservation abandoned, never reuse it.

## Lease authority

Acquire creates an external token with exclusive-create semantics before store
acceptance. The store retains only its SHA-256 hash. A WRITE lease binds the
repository hash, workspace hash, Change ID, holder reference, optional external
workspace-reference hash, accepted Change truth, revision, timestamps, status,
and at most one active operation. Default TTL is 900 seconds; accepted TTL is
30–86400 seconds.

Renew, release, and recover are exact compare-and-swap operations. Renew and
release require the external token and expected revision. Recovery is token
free, but only after expiry and only with exact expected revision and accepted
truth. Released and recovered records remain as tombstones. Backward clock
observations, malformed state, unsupported versions, truth drift, active
operations, and ambiguous bindings block.

## Mutation wrapper

One internal operation context is threaded through every Change writer.
`begin_mutation` validates authority and stores an active-operation digest and
advanced revision. The project operation runs without the store lock.
`finalize_mutation` compares the same operation identity and accepted pre-truth,
records the new truth, clears the operation, advances revision, and emits a
non-secret receipt. `abort_mutation` clears only when Change truth is unchanged;
otherwise the unresolved operation remains fail-closed.

Nested state transitions receive the existing context rather than opening a
second operation. Public Python entry points enforce the same requirement as
the CLI. Never-coordinated legacy Changes remain readable and acquire lazily;
after activation, writes without a valid lease context return
`BLOCKED_WRITE_LEASE_REQUIRED`.

## Maintenance and rollback

Bootstrap, repair, upgrade, rollback, and GitHub configuration apply paths use
a short workspace-maintenance guard. It blocks while any live or
expired-unrecovered WRITE lease or active operation targets the workspace.
Downgrade/rollback additionally requires all reservations terminal, all leases
released or recovered, no active operation, and current truths matching their
last accepted values. The coordination store is retained for audit.

## Security and redaction

Token bytes and token-file paths are prohibited from repository files,
approvals, evidence, receipts, ordinary output, exceptions, and logs. Errors
contain stable codes and hashes/bounded references only. Token deletion remains
the caller's responsibility after release.

## Planned code surface

- Extend `src/aeh/runtime/coordination.py` with reservation, lease lifecycle,
  mutation context, maintenance guard, drain check, and deterministic receipts.
- Route `src/aeh/runtime/change.py`, grounding/specification/test-design/RED/
  GREEN/verify/approval/ownership writers through the common wrapper.
- Expose `coordination acquire|renew|release|recover|status` and lease arguments
  in `src/aeh/cli.py`.
- Guard bootstrap/repair/upgrade/rollback/GitHub apply entry points without
  changing their existing authorization gates.
- Add focused writer/CAS tests and adapt existing mutation fixtures to explicit
  leases. No new dependency is introduced.

## Verification

RED freezes the public CLI, direct-Python enforcement, conflict, stale token/
revision/truth, expiry/recovery, abort, reservation, redaction, maintenance,
and drain contracts. GREEN additionally runs all existing regression partitions,
documentation validation, wheel build, and clean-room smoke on the supported
Windows/Ubuntu matrix.
