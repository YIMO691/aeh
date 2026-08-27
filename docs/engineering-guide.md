# AEH Engineering Guide

> Status: **CURRENT**  
> Source line: `0.3.0.dev0`; latest public release: `v0.2.0`; PyPI not published

This is the current implementation and review guide. It complements the shorter
[Contributing guide](../CONTRIBUTING.md) and the version-bound handbook.

## Repository map

| Path | Purpose |
|---|---|
| `src/aeh/` | CLI, bootstrap, doctor, runtime, repair, upgrade, and integrations |
| `core/` | normative state, workflow, Gate, classification, precedence, and evidence contracts |
| `schemas/` | JSON Schema for machine artifacts |
| `bootstrap/` | declarative discovery, interview, repair, upgrade, and conflict policy inputs |
| `adapters/` | Codex and Claude adapter definitions/templates |
| `tests/` | unit, contract, integration, packaging, and cross-platform regression tests |
| `scripts/` | repository verification and clean-room utilities |
| `docs/` | current docs, research, version-bound baselines, and release evidence |
| `examples/` | minimal and generic-business onboarding examples |

## Local development

AEH requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX:   source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_docs.py
```

Run a focused suite while iterating, then the complete regression before a
reviewable commit. The GitHub workflow repeats the suite on Ubuntu and Windows
with Python 3.10 and 3.11 and builds/installs a wheel in clean environments.

## Change rules

1. Ground a claim in current source or explicit version-bound evidence.
2. Add a failing regression before fixing behavioral defects.
3. Keep runtime machine truth in YAML/JSON validated by schemas, not Markdown.
4. Treat `core/` or `schemas/` changes as contract changes, not ordinary refactors.
5. Preserve backward compatibility or provide an explicit upgrade/migration path.
6. Keep writes inside the declared AEH mutation boundary and make rollback clear.
7. Record architecture or governance decisions in `docs/decisions.md`.

## Contract-change checklist

A contract change normally requires:

- a stable decision/risk reference;
- schema and semantic-validator changes;
- at least one legal and one illegal fixture where applicable;
- lifecycle and CLI regressions;
- compatibility behavior for previously installed snapshots;
- documentation of truth ownership and failure behavior.

M5 and M6 are not implicit extensions of an unrelated change. They require
their own specification, threat model, plan, tests, and Owner decision.

## Documentation rules

Use the labels defined in [docs/README.md](README.md):

- `CURRENT` for present source behavior;
- `VERSION-BOUND` for an exact revision/evidence cutoff;
- `RESEARCH` for sourced reasoning and limitations;
- `FROZEN RELEASE EVIDENCE` and `ARCHIVED` for immutable history.

Update [documentation-contract.yaml](documentation-contract.yaml) when an
authorized release or milestone changes a canonical public claim. Run
`python scripts/check_docs.py` to verify package-version alignment, required
claims, status labels, and local Markdown links.

Do not rewrite `docs/releases/**` to describe a later version. Add a new release
evidence directory. Do not turn the v0.2 handbook into current truth; add a
current supplement or a separately versioned handbook.

## Release discipline

Source version, tag, GitHub Release, package asset, and PyPI publication are
separate decisions. A source version does not prove a release occurred. A
release requires exact-commit tests, wheel metadata and hash verification,
clean-room installation, public-safety review, release evidence, and explicit
authorization.

The current source is `0.3.0.dev0`; the latest public release is `v0.2.0`; no
AEH version is published to PyPI.
