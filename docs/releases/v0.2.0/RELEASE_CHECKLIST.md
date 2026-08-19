# AEH v0.2.0 Release Safety Checklist

Review date: 2026-08-19

Verdict: `READY_FOR_OWNER_RELEASE`

This verdict does not create or authorize a tag, GitHub Release, or PyPI
publication. Product effectiveness remains `NOT_YET_PROVEN`, and Phase 2 /
72-run remains unauthorized.

## R0 Integration provenance

- [x] V02-0 PR #1 merged: `88586b2`
- [x] M1 PR #2 merged: `07c501f`
- [x] M2 PR #3 merged: `17bdbb4`
- [x] M3 PR #4 merged: `cc7d93f`
- [x] Integrated merge tree equals accepted M3 head `e6f8d5a`
- [x] Review worktree clean before release-record preparation

## R1 Public safety and repository hygiene

- [x] Secret/token/private-key scan PASS
- [x] Absolute machine-path scan PASS
- [x] Repository filenames are ASCII
- [x] Full internal session/run evidence is not present in the public tree
- [x] Handbook publishes only reviewed material and integrity records

## R2 Contract and document consistency

- [x] Package and Harness version: `0.2.0`
- [x] Compiler compatibility version remains `0.1.0`
- [x] Runtime schema version remains `1`
- [x] Handbook check PASS: 27 chapters and 7 appendices
- [x] Handbook software evidence snapshot remains explicitly distinct from the
      current software candidate
- [x] Product-effectiveness and Phase 2 boundaries are not overstated

## R3 Regression and CI

- [x] Integrated local regression: 273/273 PASS
- [x] Linux Python 3.10 regression PASS
- [x] Linux Python 3.11 regression PASS
- [x] Windows Python 3.10 regression PASS
- [x] Windows Python 3.11 regression PASS
- [x] Linux clean-room wheel PASS
- [x] Windows clean-room wheel PASS

## R4 Package build

- [x] Isolated PEP 517 wheel build PASS
- [x] Fixed-epoch repeat build byte-identical
- [x] Wheel name/version/Python requirement/dependencies PASS
- [x] Console entry point `aeh = aeh.cli:main` present
- [x] Runtime core, schemas, adapters, repair rules, and upgrade policy present
- [x] Tests, task evidence, and private machine data absent from wheel
- [x] Candidate wheel SHA-256:
      `A9D204F92B75F5953D52A321A0DAC195A037CA45C4F40434EC4B6E4C21B60A5C`

## R5 Clean-room lifecycle

- [x] Install wheel in fresh virtual environment
- [x] Bootstrap and Doctor
- [x] Repair dry-run/apply with `RPR-2026-0001`
- [x] Shape integrity-valid v0.1.0 runtime snapshot
- [x] Upgrade dry-run/apply with `UPG-2026-0001`
- [x] Post-upgrade Doctor `READY_WITH_WARNINGS`
- [x] First change `CHG-2026-0001`

## R6 Blockers

- P0: 0
- P1: 0
- P2: existing test-only file-handle `ResourceWarning` messages; no observed
  resource exhaustion, nondeterminism, or failed gate.

Final decision: `READY_FOR_OWNER_RELEASE`.
