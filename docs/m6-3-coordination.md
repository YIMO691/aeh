# M6.3 Coordination Boundary

> Status: **CURRENT** for source line `0.3.0.dev0`.

M6.3 is delivered in three serial stages. M6.3A establishes contracts and a
read-only substrate; M6.3B adds bounded Change reservation and lease mutations;
M6.3C adds stable readers, AEW v2 projection, the real-process fault matrix,
and a bounded full-regression budget. These capabilities remain a local
coordination protocol, not a scheduler.

## Current M6.3 capability

M6.3A adds four versioned JSON contracts, deterministic repository/workspace
identity hashes, an external canonical repository store, bounded shared and
exclusive OS locks, exact Change-truth hashing, deterministic non-secret
receipts, and `aeh coordination status`.

M6.3B adds reservation, acquire, renew, release, explicit recovery, mutation
begin/finalize/abort CAS, workspace maintenance guards, and a drain Gate. The
lease token is external authority and is never stored in Change artifacts.

M6.3C adds `stable_change_snapshot`, which retains one shared repository lock
while it validates accepted Change truth, executes a bounded callback, and
validates the same truth again. Change status, CI replay artifact ingestion,
and AEW export use this primitive. If no store exists, a legacy read reports
`NOT_ACTIVATED` and does not create coordination state. Active operations,
truth drift, malformed or unsupported stores, unsafe paths, and lock timeouts
fail closed instead of returning mixed generations.

## Correctness boundary

The protocol supports one host and a local filesystem only. It does not provide
cross-host or network-filesystem correctness and blocks Windows UNC paths,
state roots inside the governed target, and symlink/junction/reparse boundaries
when safety cannot be proven. POSIX uses `fcntl.flock`; Windows uses native
`LockFileEx` shared/exclusive byte-range locking. A process exit releases the
OS lock but never grants or changes logical lease authority.

Real spawned-process tests prove concurrent readers, writer exclusion, crash
release of the OS lock, retained logical-lease blocking, workspace isolation,
and deterministic failure on unresolved state. AEH remains a validator and
does not become a general agent scheduler.

## State and privacy

The additive store is located below `AEH_CONTROLLER_STATE_DIR` at
`coordination-v1/repositories/<repository-hash>/store.json`. Status, receipts,
and stable errors expose hashes and bounded references—not raw repository IDs,
workspace paths, state-root paths, token bytes, credential bodies, or token-file
paths.

Every accepted stable read exposes only protocol version, coordination state,
repository/workspace identity hashes, nullable lease revision and accepted
truth/receipt digests, plus an optional hash of the external workspace ref.
AEW governance adapter v2 requires this object and emits it from the same
snapshot as Change artifacts. Raw paths, repository identifiers, credentials,
and lease tokens are excluded.

## Replay and workflow budget

CI replay keeps its clean exact-head, tracked-input, no-project-code, and
read-only guarantees; coordination overlap becomes an `INCONCLUSIVE` replay
check. The supported regression matrix remains bounded at 40 minutes while the
clean-room wheel job remains bounded at 20 minutes.

## Manual operating sequence

1. Reserve or select the Change, then acquire one external WRITE lease.
2. Pass the token file, exact lease revision, and workspace ref to every Change
   mutation; stale revisions and overlapping operations fail closed.
3. Use status, CI replay, or AEW export without a lease token; each uses a
   stable shared snapshot.
4. Finalize or abort each mutation, then release the logical lease and delete
   its token file.
5. Before workspace maintenance, upgrade, rollback, or removal, require the
   maintenance/drain checks to report no active lease or pending reservation.

Recovery is explicit and requires expiry, exact accepted truth, and bounded
serialization. It is not automatic renewal or daemon-driven ownership.
Rollback means reverting the M6.3C source/schema/docs commit after the store is
drained; existing v1 stores remain version-checked external state.
