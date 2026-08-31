# M6.3A Design — Coordination Contracts and External Store Substrate

## Boundary

M6.3A is a single-host, local-filesystem coordination substrate. It does not
claim cross-host or network-filesystem correctness, and it exposes no lease or
reservation mutator command. The only CLI surface added here is read-only
`aeh coordination status`.

## Components

1. `schemas/coordination-store.schema.json` defines one canonical repository
   store document with contract/version guards, revision, bounded collections,
   and hashes rather than raw repository or workspace identifiers.
2. `schemas/change-lease.schema.json`, `workspace-binding.schema.json`, and
   `coordination-receipt.schema.json` freeze the records needed by later M6.3
   stages without activating their write workflows.
3. `aeh.runtime.coordination` derives repository/workspace hashes, resolves the
   external `coordination-v1/repositories/<hash>` path, acquires bounded OS file
   locks, validates canonical state, performs atomic replacement, hashes exact
   Change truth, and builds deterministic non-secret receipts.
4. CLI status and Doctor call one read-only status function. When no store is
   present it returns `NOT_ACTIVATED` and creates neither directory nor file.
5. Bootstrap/package resource enumeration remains generic: the four new root
   schemas are copied into installed `.aeh/runtime/schemas` and wheel data.

## Data flow

`target -> safe canonical workspace -> repository/workspace SHA-256 -> external
state path -> shared lock -> schema-validated store -> redacted status`.

Writer-only test helpers use `exclusive lock -> validate expected complete
document -> canonical temp sibling -> flush/fsync -> os.replace -> best-effort
parent fsync`. A failed replacement never promotes a temporary remnant.

## Failure model

Unsafe paths, reparse/symlink boundaries, UNC/network-style roots, unsupported
versions, malformed JSON, incomplete Change truth, and lock timeout fail closed
with stable `BLOCKED_COORDINATION_*` codes. Errors and receipts must not contain
raw target paths, state-root paths, raw repository IDs, token material, or
credential bodies.

## Rollback

All changes are additive. Removing the module, four schemas, fixtures, tests,
CLI parser branch, and Doctor check restores the prior behavior. Existing
Change files, ownership-v1 checkpoints, approvals, journals, and evidence are
not migrated or rewritten.
