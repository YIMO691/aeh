# AEH Documentation

> Status: **CURRENT**  
> Source line: `0.3.0.dev0`  
> Latest public release: `v0.2.0`  
> Roadmap: M1–M5 + M6.1 + M6.2a–c merged; M6.2d live dogfood candidate; M6.3 planned; PyPI not published

This is the canonical entry point for AEH documentation. It separates current
software truth from version-bound research and historical release evidence.

## Choose a reading path

### I want to understand why AEH exists

1. [About AEH](about.md)
2. [From Black Box to AEW](research/01_From_Black_Box_to_AEW.md)
3. [Research method and evidence](research/02_Research_Method_and_Evidence.md)

### I want to use AEH

1. [Repository README](../README.md)
2. [Current status and boundaries](status.md)
3. [M4 manual verification governance](m4-governance.md)
4. [M5 security boundary](m5-security.md)
5. [AEW integration](integrations/aew.md)
6. [M6.1 CI replay](m6-ci-replay.md)
7. [M6.2 GitHub assurance](m6-2-github-assurance.md)
8. [Examples](../examples/README.md)

### I want to develop or review AEH

1. [Current architecture](architecture-current.md)
2. [Engineering guide](engineering-guide.md)
3. [Contributing](../CONTRIBUTING.md)
4. [Roadmap](roadmap-v0.2.md)
5. [Decision log](decisions.md)

## Document authority

| Label | Meaning | Examples |
|---|---|---|
| `CURRENT` | Describes the current source line and may be used for present-tense claims | this index, status, current architecture |
| `VERSION-BOUND` | Accurate only for the revision and evidence cutoff named in the document | Phase 0 architecture, v0.2 handbook |
| `RESEARCH` | Explains reasoning, sources, limitations, and strategic interpretation | `docs/research/` |
| `FROZEN RELEASE EVIDENCE` | Records what was reviewed or released at a specific version | `docs/releases/` |
| `ARCHIVED` | Superseded design material retained for traceability | `docs/archive/` |

Markdown never becomes runtime machine truth. Current behavior is ultimately
defined by package metadata, `core/`, `schemas/`, executable validators, tests,
and exact CI evidence. [documentation-contract.yaml](documentation-contract.yaml)
only governs public documentation claims; it does not govern AEH Change state.

## Historical material

- [Architecture Freeze](architecture.md) is the approved Phase 0 contract and is
  intentionally version-bound.
- [Repository Panorama](repository-panorama.md) is a detailed V0.1/V0.2 design
  baseline, not the fastest description of the current implementation.
- [Engineering & Architecture Handbook v0.2](handbook/README.md) is a research
  snapshot bound to `v0.1.0 @ 6513102`.
- `docs/releases/` and `docs/archive/` are preserved evidence, not live status.

For the present state, always start with [status.md](status.md).
