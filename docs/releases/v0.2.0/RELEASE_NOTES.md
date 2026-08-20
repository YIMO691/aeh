# AEH v0.2.0 - Repairable and Upgradeable Runtime

AEH v0.2.0 turns the v0.1 contract harness into a relocatable, recoverable
runtime with an explicit upgrade path. AEH remains an independent Change
Assurance system: generators propose changes; AEH validates evidence, scope,
tests, traceability, and acceptance gates.

## Highlights

- **Relocatable wheel**: install AEH from the attached wheel and run it from any
  working directory; runtime core, schemas, adapters, repair rules, and upgrade
  policy are bundled.
- **Cross-platform regression gate**: Windows/Linux × Python 3.10/3.11 plus
  clean-room wheel lifecycle jobs on both operating systems.
- **Plan-first repair**: `aeh repair <target>` defaults to a zero-write plan;
  `--apply` uses persistent journals, before-state backups, drift checks,
  automatic failure rollback, and explicit rollback.
- **Explicit upgrade**: `aeh upgrade <target>` safely migrates an
  integrity-valid v0.1.0 runtime snapshot to v0.2.0 while preserving project
  profile, workflow, bootstrap answers, private data, changes, approvals, and
  agent files.
- **Design and evidence baseline**: Handbook v0.2 records the system boundary,
  Phase 1.1 evidence, architecture decisions, claims, and source registries.

## Quality gates

- Local integrated regression: **273/273 PASS**
- Final GitHub main matrix: **6/6 PASS**
- Handbook deterministic check: **PASS** (27 chapters, 7 appendices)
- Fixed-epoch repeat wheel build: **byte-identical**
- Release wheel SHA-256:
  `8FC11F9B42CD90FB4E4D1B64380E429D9AD19D80CACFC76396C0B46F59B3ED19`
- Clean-room lifecycle: bootstrap → Doctor → repair → v0.1-shaped runtime →
  upgrade → Doctor → first change: **PASS**
- Release blockers: **P0=0, P1=0**

## Install

Download `adaptive_engineering_harness-0.2.0-py3-none-any.whl` from this Release,
then run:

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install adaptive_engineering_harness-0.2.0-py3-none-any.whl
aeh bootstrap /path/to/your-project
aeh doctor /path/to/your-project
```

On POSIX, activate with `source .venv/bin/activate`.

## Upgrade and repair

```text
aeh repair /path/to/your-project
aeh repair /path/to/your-project --apply

aeh upgrade /path/to/your-project
aeh upgrade /path/to/your-project --apply
```

Both commands are dry-run by default. Review the plan before using `--apply`.

## Honest boundaries

- Product effectiveness remains `NOT_YET_PROVEN`; Phase 2 / 72-run is not
  authorized.
- Approval is attestation, not cryptographically strong identity.
- Upgrade is bounded to an integrity-valid v0.1.0 snapshot; no automatic,
  network, incremental, arbitrary-history, or multi-version upgrade.
- No PyPI publication, automatic merge/push, deep user-repository CI
  integration, Web UI, RAG, or multi-agent orchestration.

Full evidence and limitations:

- `docs/releases/v0.2.0/RELEASE_CHECKLIST.md`
- `docs/releases/v0.2.0/RELEASE_TEST_REPORT.md`
- `docs/releases/v0.2.0/KNOWN_LIMITATIONS.md`
