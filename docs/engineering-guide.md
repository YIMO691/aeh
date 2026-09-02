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

M6.1 follows this rule with `core/ci-policy.yaml`, CI policy/report schemas,
legal and illegal fixtures, real-flow attack tests, upgrade coverage, and a
documented read-only boundary. M6.2a–c add a separate enforcement policy,
provider event/snapshot/report/workflow contracts, exact-diff attacks, a secure
renderer and read-only audit. M6.3 adds external coordination contracts,
writer CAS, stable readers, and AEW v2; every slice retains separate human
Gates and rollback evidence.

M5 execution and approval changes must preserve the boundaries in
[m5-security.md](m5-security.md): no-shell default execution, dual explicit
shell authorization, external credential custody, and no claims of OS sandbox
or enterprise identity properties.

CI replay changes must preserve [m6-ci-replay.md](m6-ci-replay.md): never run
project-declared commands, never write below the inspected repository root,
bind repository/base/head/runtime/time and committed inputs, and fail closed
when a protected approval credential is unavailable.

GitHub integration changes must preserve
[m6-2-github-assurance.md](m6-2-github-assurance.md): exact check/App/head and
workflow digest binding, one fresh Change, complete declared diff closure,
immutable artifact/action pins, no protected credential in repository CI, and
honest `INCONCLUSIVE` results when provider metadata is unavailable.

Coordination changes must preserve
[m6-3-coordination.md](m6-3-coordination.md): one-host/local-filesystem scope,
external token custody, exact lease revisions, stable pre/post truth, read-only
legacy behavior, explicit recovery/drain, redacted receipts, and real spawned-
process coverage. Never replace the process tests with thread-only substitutes.

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
