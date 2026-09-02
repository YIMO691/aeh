# CHG-2026-0004 design — stable readers, AEW v2, and fault closure

## Boundary

M6.3C completes the frozen M6.3 single-host coordination protocol. It adds a
single stable Change-read primitive, routes Change status, CI replay, and AEW
export through it, upgrades the AEW governance envelope to version 2, expands
real multi-process fault evidence, and reconciles current documentation. It
does not add a scheduler, renewal daemon, cross-host lease, network-filesystem
claim, SCM administration mutation, tag, Release, or PyPI publication.

## Stable snapshot primitive

`stable_change_snapshot` is the only new Change-scoped read authority. It takes
the repository shared lock without creating a missing coordination store, then:

1. resolves repository and physical-workspace identity;
2. reads and schema-validates the current store when present;
3. selects the Change lease/tombstone and rejects an active operation;
4. hashes Change truth and, for activated coordination, requires the hash to
   equal the last accepted truth;
5. executes a bounded local reader callback while retaining the shared lock;
6. hashes Change truth again and requires exact equality before returning.

The successful result contains the callback value plus deterministic,
non-secret provenance. A never-coordinated Change returns `NOT_ACTIVATED`
without creating a store. Lock timeout, malformed or unsupported state, active
operation, accepted-truth mismatch, or before/after drift fails closed with a
stable coordination code. Multiple readers coexist; writer begin/finalize is
excluded for the duration of every callback.

## Reader integrations

`change status` loads its complete report inside one stable snapshot and adds a
redacted coordination projection. Repository-wide discovery remains
lease-free. No status path creates the external store.

CI replay retains its exact-head, changed-path closure, read-only target, and
no-project-code guarantees. Its Change artifact ingestion occurs inside one
stable snapshot; coordination failures become deterministic replay failures,
never partially accepted documents.

AEW export computes the Change contract, verification verdict, manifest,
artifact references, hashes, and source-control projection inside one stable
snapshot. The callback owns no external AEW state and performs no network or
target write.

## AEW governance adapter v2

The adapter schema and exporter version advance together to 2. The envelope
adds a required `coordination` object containing:

- `protocol_version`;
- `state` (`NOT_ACTIVATED`, `ACTIVE`, `RELEASED`, `RECOVERED`, or `BLOCKED`);
- `repository_id_sha256` and `workspace_id_sha256`;
- nullable `lease_revision`, `last_truth_hash`, and `last_receipt_digest`;
- optional `external_workspace_ref_sha256`.

Raw repository identifiers, raw paths, token bodies, token-file paths,
credentials, and state-root paths are forbidden. Artifact ordering and all
derived objects remain deterministic for identical accepted inputs. V1 is not
silently emitted under a v2 contract; rollback compatibility remains an
explicit consumer decision.

## Receipts, redaction, and artifact isolation

Existing canonical receipt construction remains the authority. Tests cover
accepted and rejected lifecycle operations, recovery, deterministic digests,
and token canaries across repository bytes, store JSON, stdout/stderr,
receipts, evidence, and AEW envelopes. Distinct physical workspaces use
separate Change and declared-output roots; attempts to cross those boundaries
fail before execution.

## Multi-process fault matrix

New workers use independently spawned processes and bounded synchronization
files/events rather than thread-only substitutes. The matrix covers concurrent
reservations, competing Change/workspace leases, simultaneous shared readers,
writer exclusion, process termination while holding the OS lock, retained
logical lease blocking after process death, recovery races, and atomic-store
fault boundaries. Every worker uses task-controlled temporary roots and emits
only non-secret structured results.

## CI time budget

The regression workflow remains bounded but increases the full-regression job
budget from the observed undersized 20-minute limit. The clean-room job retains
its existing tighter budget. The new limit is justified by two exact-main
Windows Python 3.10 cancellations at the old boundary with no test assertion
failure, and must cover the expanded M6.3C matrix without masking hangs.

## Current documentation

README, current architecture, roadmap, status, decisions, engineering guide,
documentation contract, and changelog describe the exact achieved protocol,
manual acquire/mutate/release use, stable reads, AEW binding, recovery, drain,
rollback, failure codes, and explicit limits. Frozen release/archive evidence
is excluded from mutation.

## Planned code surface

- `src/aeh/runtime/coordination.py`: stable snapshot and redacted provenance.
- `src/aeh/runtime/change.py`: stable Change status.
- `src/aeh/ci.py`: snapshot-bound replay ingestion and defined failures.
- `src/aeh/integrations/aew.py`: deterministic v2 envelope.
- `schemas/aew-governance-adapter.schema.json`: v2 coordination contract.
- tests for stable readers, AEW v2, receipts, crossover, and real processes.
- `.github/workflows/regression.yml` (or the current regression workflow):
  bounded supported-matrix timeout correction.
- current documentation only.

No new third-party runtime dependency is introduced.

## Verification

RED freezes the stable-reader API, integration routing, v2 schema, redaction,
multi-process exclusion/recovery, artifact isolation, and CI-budget contract.
GREEN and REFACTOR run the locked suite, existing coordination writers, AEW,
CI replay, contracts, full regression partitions, documentation validation,
wheel build, and clean-room smoke. Required GitHub checks run on the exact PR
head; exact post-merge `main` is verified separately.
