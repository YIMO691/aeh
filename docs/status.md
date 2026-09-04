# AEH Current Status

> Status: **CURRENT**  
> Last reconciled: 2026-09-04

## Release and source state

| Item | Current value |
|---|---|
| Source version | `0.3.0.dev0` |
| Latest GitHub release | `v0.2.0` |
| PyPI | Not published |
| Roadmap | M1–M6 merged; M6.3A/B/C complete |
| Current source test baseline | 412 discovered, 408 passed, 4 expected Windows symlink-permission skips |
| Latest post-merge main CI | 6/6 jobs passed on Ubuntu/Windows and Python 3.10/3.11 |
| Latest documentation baseline | PR #22 merged as `debf35196ce5b9f649e6ff270327854224fccaee`; post-merge run `33745066439` passed 6/6 jobs |

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
| M6 | MERGED | CI replay/GitHub assurance plus bounded local Change coordination, stable readers, and AEW v2 provenance |

All six top-level implementation milestones are merged. M6.3C binds status, CI
replay, and AEW v2 export to one stable local Change snapshot. PR #21 passed
13/13 checks, merged as `b72dcd5d261a35ea90b8b5b97899b6b4e5c8358a`, and
the exact-main post-merge run passed 6/6 jobs. This does not provide OS
isolation, enterprise identity, cross-host coordination, or network-filesystem
correctness.

The later documentation-alignment change was merged through PR #22 as
`debf35196ce5b9f649e6ff270327854224fccaee`. Its exact-main post-merge workflow,
run `33745066439`, passed all 6 jobs. PR #22 aligned public documentation to the
already completed M1–M6 implementation; it did not create a new capability
milestone or release.

## Current capability boundary

AEH can bootstrap and diagnose a repository, govern a Change from classification
through `MERGE_READY`, preserve test and evidence integrity, recover or upgrade
an installed runtime, export bounded governance truth to AEW, and replay a
committed Change in a clean external Git checkout without running project code.
The current source line can also bind GitHub PR/merge-group runs to an exact
new Change and declared diff, render a pinned immutable-artifact workflow, and
audit required-check enforcement without changing GitHub settings.

M6.3C also provides token-free stable status/CI/AEW reads over
the single-host local-filesystem coordination store. Real spawned-process tests
cover concurrent readers, writer exclusion, crash release of OS locks, retained
logical leases, and workspace isolation.

M6.2d adds an explicit solo-repository approval option:
`SCM_AUTHENTICATED_MERGE` delegates final `MERGE_GATE` authority to the SCM's
authenticated merge action and emits warnings. Strict HMAC approval remains
available and is still required for manual verification or stronger governance.

AEH cannot provide public-key human identity, non-repudiation, a kernel-level
execution sandbox, an unbypassable hosted CI service/SCM rule, or multi-agent
orchestration. The default M6.2 policy deliberately cannot render or claim an
active workflow until artifact and workflow digests are configured. AEH does
not merge or release changes by itself.

## Evidence and authority

- Package version authority: `pyproject.toml`
- Runtime contracts: `core/` and `schemas/`
- Executable behavior: `src/aeh/`
- Regression evidence: `tests/` and GitHub Actions
- Development history: `CHANGELOG.md`
- Completed V0.2 roadmap record: [roadmap-v0.2.md](roadmap-v0.2.md)
- Release evidence: `docs/releases/<version>/`
- Documentation claims: [documentation-contract.yaml](documentation-contract.yaml)

The documentation checker validates these public claims against package
metadata and required navigation links. It does not replace runtime validators.
