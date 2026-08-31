# M6.3 Coordination Boundary

M6.3 is delivered in three serial stages. M6.3A establishes contracts and a
read-only substrate; M6.3B will add bounded Change reservation and lease
mutations; M6.3C will add stable readers, AEW v2 projection, and the complete
fault matrix. Completion of M6.3A alone is not completion of M6.3 or V0.2.

## M6.3A capability

M6.3A adds four versioned JSON contracts, deterministic repository/workspace
identity hashes, an external canonical repository store, bounded shared and
exclusive OS locks, exact Change-truth hashing, deterministic non-secret
receipts, and `aeh coordination status`.

The command and the Doctor coordination diagnostic are read-only. If no store
exists they report `NOT_ACTIVATED` and do not create a directory, lock, store,
receipt, or Change artifact. Unknown contract versions and malformed state fail
closed; no implicit migration is attempted.

## Correctness boundary

The protocol supports one host and a local filesystem only. It does not provide
cross-host or network-filesystem correctness and blocks Windows UNC paths,
state roots inside the governed target, and symlink/junction/reparse boundaries
when safety cannot be proven. POSIX uses `fcntl.flock`; Windows uses
`msvcrt.locking` on byte zero. A process exit releases the OS lock but never
grants or changes logical lease authority.

M6.3A intentionally exposes no acquire, renew, release, recover, reservation,
or mutator-CAS command. AEH remains a validator and does not become a general
agent scheduler.

## State and privacy

The additive store is located below `AEH_CONTROLLER_STATE_DIR` at
`coordination-v1/repositories/<repository-hash>/store.json`. Status, receipts,
and stable errors expose hashes and bounded references—not raw repository IDs,
workspace paths, state-root paths, token bytes, credential bodies, or token-file
paths.
