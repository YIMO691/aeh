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
| Enforcement runtime | `src/aeh/runtime`, doctor, repair, upgrade, integrations | independently evaluates and mutates only authorized AEH surfaces |
| Evidence and projection | `.aeh/changes`, journals, reports, review projections | preserves replayable inputs, hashes, verdicts, and explanations |

## Truth ownership

| Truth | Owner |
|---|---|
| Source implementation and repository history | project SCM |
| AEH contract legality and Change state | AEH contracts and validators |
| Test execution outcome | recorded command output plus AEH evidence validation |
| Human decision | attributed approval record; not cryptographic identity in M4 |
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
inspection, approval TTL/expiry, and provenance-preserving revocation.

Current limitations are equally important:

- approval is an attributable human attestation, not strong identity;
- test command execution is not a general cross-platform sandbox;
- CI evidence is external and not yet a deep, unbypassable user-project Gate;
- AEH stops at `MERGE_READY` and does not autonomously merge or release.

M5 addresses sandboxing and strong approval identity. M6 depends on M5 and adds
deep CI integration plus bounded multi-agent concurrency.

## Compatibility and extension

The public extension surfaces are declarative discovery/interview inputs,
schemas, contracts, and adapters. Contract changes require a decision entry,
legal and illegal fixtures, regression coverage, backward-compatibility
analysis, and an explicit migration path when installed snapshots change.

See [engineering-guide.md](engineering-guide.md) for the implementation workflow
and [repository-panorama.md](repository-panorama.md) for the detailed historical
design baseline.
