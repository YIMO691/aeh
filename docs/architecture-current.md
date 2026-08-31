# AEH Current Architecture

> Status: **CURRENT**  
> Source line: `0.3.0.dev0`

This document describes the implemented architecture in the current source.
The approved Phase 0 principles remain available in the version-bound
[Architecture Freeze](architecture.md).

## System boundary

```text
Developer / coding agent
        |
        v
  aeh CLI and adapters
        |
        +--> bootstrap / discovery / doctor
        +--> Change lifecycle runtime
        +--> repair / upgrade / rollback
        +--> SCM inspection / AEW export
        +--> read-only CI evidence replay
        |
        v
contracts + schemas + validators
        |
        v
.aeh machine artifacts, evidence, journals, and human-readable projections
```

AEH owns Change Assurance truth. The coding agent owns implementation work.
Git, CI, pull requests, merges, releases, and AEW retain their own external
truth and are referenced rather than absorbed.

## Five layers

| Layer | Repository surface | Responsibility |
|---|---|---|
| Guidance | adapters, generated agent instructions, Markdown | explains how to work; never decides a Gate |
| Normative contracts | `core/*.yaml`, `schemas/*.json` | defines legal states, evidence, transitions, and artifacts |
| Compiler and bootstrap | `src/aeh/bootstrap`, discovery/interview/compiler code | derives and installs a versioned project runtime |
| Enforcement runtime | `src/aeh/runtime`, doctor, repair, upgrade, integrations, CI replay | independently evaluates and mutates only authorized AEH surfaces; CI replay is target-read-only |
| Evidence and projection | `.aeh/changes`, journals, reports, review projections | preserves replayable inputs, hashes, verdicts, and explanations |

## Truth ownership

| Truth | Owner |
|---|---|
| Source implementation and repository history | project SCM |
| AEH contract legality and Change state | AEH contracts and validators |
| Test execution outcome | recorded command output plus AEH evidence validation |
| Human decision | attributed record plus HMAC credential possession; not legal identity or non-repudiation |
| PR, merge, deployment, release | external SCM/CI/release systems |
| Workspace scheduling, agents, memory | AEW or another orchestrator |

An AEW export is a deterministic envelope over AEH-owned facts. It cannot write
back a passing verdict or replace AEH's validator.

## Installation topology

`aeh bootstrap <target>` discovers the repository, resolves explicit answers,
and installs a versioned `.aeh/` runtime snapshot plus managed adapter sections.
The manifest records the source revision and digests required to explain which
contracts produced the installed runtime.

Bootstrap is plan-first and fail-safe. Doctor is read-only. Repair and upgrade
use explicit plans, transaction journals, byte backups, and rollback rather
than silent overwrite.

## Bounded local coordination

M6.3B coordinates Change writers on one host and a local filesystem. A
repository-scoped external store serializes monotonic Change-ID reservations,
WRITE leases, workspace bindings, fencing revisions, active operations, and
non-secret receipt digests. Lease tokens are created only at an explicit path
outside both the target and coordination store; committed state contains only
their SHA-256 digest.

After a Change first acquires a lease, public Change writers require the token
file and exact lease revision. One begin/execute/finalize transaction compares
Change truth before and after the write; nested runtime calls reuse that active
operation. Abort succeeds only when truth is unchanged. Expired authority and
unresolved operations remain fail-closed until eligible recovery. Bootstrap,
repair, upgrade, rollback, and GitHub configuration also refuse workspace
maintenance while conflicting writer authority exists, and upgrade rollback
requires a repository-wide drain.

The assurance boundary is deliberately narrow: local OS file locking and
atomic replacement do not establish correctness across hosts or network
filesystems. Stable coordinated readers and AEW v2 provenance remain M6.3C.

## Change Assurance lifecycle

The principal path is:

```text
NEW -> GROUND -> SPEC -> TEST_DESIGN -> RED -> GREEN
    -> REFACTOR? -> VERIFY -> APPROVE -> REVIEW -> MERGE_READY
```

Actual transitions depend on the risk-classified effective workflow. Each
Change has isolated state; there is no global "current Change". Validators
enforce test integrity, scope, traceability, required verification, and Gate
state before advancement.

## Security model

Current protections include explicit mutation boundaries, schema validation,
test locking, evidence hashes, source-revision checks, bounded local SCM
inspection, approval TTL/expiry, credential signatures, provenance-preserving
revocation, and constrained process-launch policy.

Current limitations are equally important:

- HMAC authenticates configured shared-credential possession, not legal human
  identity, public-key non-repudiation, OIDC, IAM, or hardware custody;
- constrained process launch is not kernel/container/VM/filesystem/network/
  syscall/process-tree isolation;
- M6.1 produces deterministic read-only CI replay verdicts; M6.2 binds them
  to GitHub metadata and the configured required-check workflow, while runner
  isolation, bypass authority and merge enforcement remain external;
- AEH stops at `MERGE_READY` and does not autonomously merge or release.

M5 implements the bounded portable security layer. M6.1 adds the replay core;
M6.2 adds the GitHub adapter and live dogfood required-check path. M6.3A/B add
the bounded local coordination substrate and writer protocol; M6.3C remains
responsible for coordinated readers, AEW v2 provenance, and extended faults.

## CI replay boundary

`aeh ci verify` validates an exact clean Git checkout without running commands
declared by that checkout. It recomputes installed-runtime integrity, schema
legality, Change gates, test/protected-file locks, evidence hashes, grounding
freshness, traceability, and approvals. Its canonical report binds the SCM
repository identity, base/head IDs, caller-supplied observed time, installed
runtime and every consumed repository input.

The command does not establish a trusted clock or runner, configure a branch
rule, prevent administrator bypass, merge, push, or write into the inspected
repository. Those authority boundaries cannot be created by a local validator.

## GitHub assurance boundary

`aeh ci github verify-event` consumes authenticated run/check metadata and
accepts only one fresh Change whose declared implementation, tests and governed
metadata close the exact base/head diff. The renderer pins Action commits and
an immutable wheel hash; the auditor distinguishes observed, repository-required
and externally governed workflows. The default policy is intentionally
unconfigured, so current source does not claim that this repository is protected.

## Compatibility and extension

The public extension surfaces are declarative discovery/interview inputs,
schemas, contracts, and adapters. Contract changes require a decision entry,
legal and illegal fixtures, regression coverage, backward-compatibility
analysis, and an explicit migration path when installed snapshots change.

See [engineering-guide.md](engineering-guide.md) for the implementation workflow
and [repository-panorama.md](repository-panorama.md) for the detailed historical
design baseline.
