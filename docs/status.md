# AEH Current Status

> Status: **CURRENT**  
> Last reconciled: 2026-08-27

## Release and source state

| Item | Current value |
|---|---|
| Source version | `0.3.0.dev0` |
| Latest GitHub release | `v0.2.0` |
| PyPI | Not published |
| Roadmap | M1–M5 merged; M6 planned |
| Current source test baseline | 331 discovered, 327 passed, 4 expected Windows symlink-permission skips |
| Latest post-merge main CI | 6/6 jobs passed on Ubuntu/Windows and Python 3.10/3.11 |

`0.3.0.dev0` is development metadata, not a tag or public release. The frozen
`v0.2.1` integrity-patch candidate was never released; its integrity fix was
carried forward into the current source line.

## Milestone status

| Milestone | State | Delivered capability |
|---|---|---|
| M1 | MERGED | relocatable wheel and cross-platform AEH regression CI |
| M2 | MERGED | plan-first repair, transaction journal, rollback, bootstrap recovery |
| M3 | MERGED | explicit version-bound upgrade and rollback |
| M4 | MERGED | manual verification Gate, approval TTL/expiry/revocation, earlier CRITICAL plan validation |
| M5 | MERGED | constrained process execution and credential-bound protected approvals |
| M6 | PLANNED | deep user-project CI integration and bounded multi-agent concurrency |

By milestone count, five of six planned M milestones are merged. This does not
mean the final product is complete: M5 constrains portable process launch and
shared-credential approval, but does not provide OS isolation or enterprise
identity. M6 remains separate.

## Current capability boundary

AEH can bootstrap and diagnose a repository, govern a Change from classification
through `MERGE_READY`, preserve test and evidence integrity, recover or upgrade
an installed runtime, and export bounded governance truth to AEW.

AEH cannot provide public-key human identity, non-repudiation, a kernel-level
execution sandbox, an unbypassable remote CI service, or multi-agent
orchestration. It does not merge or release changes by itself.

## Evidence and authority

- Package version authority: `pyproject.toml`
- Runtime contracts: `core/` and `schemas/`
- Executable behavior: `src/aeh/`
- Regression evidence: `tests/` and GitHub Actions
- Development history: `CHANGELOG.md`
- Roadmap decisions: [roadmap-v0.2.md](roadmap-v0.2.md)
- Release evidence: `docs/releases/<version>/`
- Documentation claims: [documentation-contract.yaml](documentation-contract.yaml)

The documentation checker validates these public claims against package
metadata and required navigation links. It does not replace runtime validators.
