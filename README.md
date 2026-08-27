# Adaptive Engineering Harness (AEH)

[![AEH regression](https://github.com/YIMO691/aeh/actions/workflows/regression.yml/badge.svg?branch=main)](https://github.com/YIMO691/aeh/actions/workflows/regression.yml)
[![Latest release](https://img.shields.io/github/v/release/YIMO691/aeh)](https://github.com/YIMO691/aeh/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Status: **CURRENT**
>
> **Independent change assurance for AI-assisted software engineering.**
> Current source: `0.3.0.dev0` (unreleased) · Latest public release: `v0.2.0` ·
> M1–M5 merged · M6 planned · PyPI not published

Coding agents can produce an implementation and a persuasive explanation. AEH
adds a separate acceptance layer: machine-enforced contracts, replayable
evidence, risk-based workflow Gates, and explicit human decisions that can
block a Change before it reaches `MERGE_READY`.

**The agent does the work; AEH makes the change visible, reviewable,
reproducible, and blockable when the evidence is weak.**

## Why AEH

A model reviewing its own output is not an independent acceptance authority.
AEH separates implementation from acceptance:

```text
coding agent / developer -> proposes and implements
contract                 -> defines what is legal
validator                -> independently recomputes the decision
evidence                 -> makes that decision replayable and reviewable
```

The wider design path is **black-box model -> Harness -> Workflow -> AEH ->
AEW**. The Harness controls an agent session; Workflow structures engineering
states; AEH assures one software Change; AEW coordinates projects, agents,
tasks, memory, and operations at workspace scale.

Read [About AEH](docs/about.md) for the full product thesis and
[From Black Box to AEW](docs/research/01_From_Black_Box_to_AEW.md) for the
research narrative.

## What it does today

- discovers a repository and installs a versioned `.aeh/` runtime snapshot;
- diagnoses installation, contract, adapter, and Change health without writing;
- classifies changes into five risk-based workflow levels;
- governs grounding, specification, test design, RED/GREEN, refactor,
  verification, approval, review, repair, and `MERGE_READY` transitions;
- locks tests and verifies evidence hashes, scope, traceability, and required Gates;
- plans and applies repair or explicit upgrade transactions with journals,
  backups, rollback, and recovery;
- supports manual verification, approval TTL/expiry, and
  provenance-preserving revocation;
- constrains AEH-managed process launch with no-shell defaults, cwd/timeout/
  environment policy, and dual authorization for declared shell execution;
- binds protected positive approvals to externally held HMAC-SHA256
  credentials with payload, Change, Gate, TTL, and revocation verification;
- generates managed Codex and Claude adapter sections;
- inspects bounded local Git/SVN boundaries and exports deterministic governance
  envelopes for AEW.
- replays committed Change Assurance evidence in a clean external Git checkout
  without running project code or mutating the repository.

AEH is intended for selective assurance where failure has meaningful cost:
security, money, identity, permissions, migrations, shared contracts,
infrastructure, release, compliance, or high-autonomy agent work.

## Install

AEH requires Python 3.10 or newer. No AEH version is published to PyPI.

For development or an explicitly trusted checkout:

```bash
git clone https://github.com/YIMO691/aeh.git
cd aeh
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX:   source .venv/bin/activate
python -m pip install -e .
aeh --help
```

For a released version, prefer the wheel and recorded SHA-256 from the trusted
[GitHub Release](https://github.com/YIMO691/aeh/releases/latest). Do not infer a
PyPI package from the project name.

## Five-minute start

Use a disposable repository first.

```bash
# 1. Preview and install AEH into a target repository
aeh bootstrap /path/to/project

# 2. Confirm the installed runtime is healthy
aeh doctor /path/to/project

# 3. Start a Change
cd /path/to/project
aeh change new "fix duplicate claim side effect" --level STANDARD
```

Then move through the evidence-producing lifecycle:

```bash
aeh change ground CHG-2026-0001
aeh change spec CHG-2026-0001 --reqs reqs.yaml
aeh change test-design CHG-2026-0001 --plan plan.yaml --test-src ./my-tests
aeh change red CHG-2026-0001

# Implement the production change with your coding agent or normal tools.

aeh change green CHG-2026-0001 --scope scope.yaml
aeh change verify CHG-2026-0001
aeh change approve CHG-2026-0001 \
  --gate MERGE_GATE --status APPROVED --actor <your-name>
aeh change review CHG-2026-0001
```

The exact path depends on the Change classification and effective workflow.
AEH stops at `MERGE_READY`; it does not push, open a PR, merge, deploy, or
release on its own.

## Manual verification and approval lifecycle

When a plan declares manual verification, record the separate Gate before
verification:

```bash
aeh change approve CHG-2026-0001 \
  --gate VERIFY_MANUAL --status APPROVED --actor <reviewer> \
  --ttl-seconds 86400 --evidence-ref <artifact-or-ticket> \
  --key-id <reviewer-key-id>
aeh change verify CHG-2026-0001
```

An approval can be revoked without erasing the original attestation:

```bash
aeh change approve CHG-2026-0001 \
  --gate VERIFY_MANUAL --status REVOKED --actor <revoker> \
  --evidence-ref <decision-or-incident-id> --key-id <revoker-key-id>
```

Keys stay outside committed truth, normally under
`.aeh/private/approval-keys/<key-id>.key`. See
[M4 governance](docs/m4-governance.md) for lifecycle behavior and
[M5 security](docs/m5-security.md) for credentials and command execution.

## Repair and upgrade

Both operations are plan-first. Omit `--apply` to inspect the plan.

```bash
aeh repair /path/to/project
aeh repair /path/to/project --apply
aeh repair /path/to/project --rollback RPR-2026-0001

aeh upgrade /path/to/project --source-revision <trusted-revision>
aeh upgrade /path/to/project --apply --source-revision <trusted-revision>
aeh upgrade /path/to/project --rollback UPG-2026-0001
```

Upgrade is explicit and version-bound. It is not an automatic, network-driven,
incremental, or arbitrary multi-version migration service.

## AEW integration

AEH and AEW remain separate systems. AEH can inspect local SCM boundaries and
export a governance envelope without giving AEW authority to write AEH verdicts.

```bash
aeh integration inspect /path/to/project
aeh integration export CHG-2026-0001 --workdir /path/to/project \
  --project-id <external-project> --task-id <external-task> --run-id <external-run>
```

See [AEW integration](docs/integrations/aew.md) for ownership, verdict mapping,
privacy, and non-goals.

## Read-only CI replay

M6.1 exposes a provider-neutral verifier for an exact committed checkout:

```bash
aeh ci verify CHG-2026-0001 --workdir /path/to/checkout \
  --repository-id github.com/owner/repository \
  --base-sha <40-hex-base> --head-sha <40-hex-head> \
  --observed-at 2026-08-27T04:00:00Z \
  --approval-key reviewer=/outside/checkout/reviewer.key
```

It emits a deterministic JSON verdict and digest. It checks evidence already
produced by AEH; it does not execute test-plan commands. See
[M6.1 CI replay](docs/m6-ci-replay.md) for the report and trust boundary.

## Trust boundary

AEH currently provides contracts, validators, evidence integrity, explicit
mutation boundaries, transaction rollback, a portable constrained-process
launcher, and credential-bound approvals. It does **not** provide:

- public-key identity, non-repudiation, OIDC, enterprise IAM, or hardware key custody;
- kernel, container, VM, filesystem, network, syscall, or process-tree isolation;
- an unbypassable remote CI service or automatic required-check configuration;
- multi-agent orchestration, RAG, mutation testing, impact analysis, or a Web UI;
- automatic push, PR, merge, deployment, or release.

M5 is deliberately bounded: HMAC proves possession of a configured shared
credential, while the execution policy constrains launch semantics without
claiming OS isolation. M6.1 supplies the read-only replay core; M6.2 SCM
enforcement and M6.3 bounded Change concurrency remain planned.

## Current status

The current source version is `0.3.0.dev0`; the latest public release is
`v0.2.0`. The frozen `v0.2.1` integrity candidate was never released. Its fix,
SCM/AEW integration, and M4 governance are present on the current development
line. PyPI is not published.

The current baseline completed 347 tests: 343 passed and 4 expected Windows
symlink-permission cases were skipped. The corresponding main workflow passed
all 6 cross-platform regression and clean-room wheel jobs.

M1–M5 are merged. M6.1 is an implementation candidate on this source branch;
M6.2 and M6.3 remain planned. See the canonical
[current status](docs/status.md) and [roadmap](docs/roadmap-v0.2.md).

## Documentation

- [Documentation portal](docs/README.md)
- [About AEH](docs/about.md)
- [Current status](docs/status.md)
- [Current architecture](docs/architecture-current.md)
- [Engineering guide](docs/engineering-guide.md)
- [M5 security boundary](docs/m5-security.md)
- [M6.1 CI replay](docs/m6-ci-replay.md)
- [Research narrative](docs/research/README.md)
- [Decisions and risks](docs/decisions.md)
- [Contributing](CONTRIBUTING.md)

Version-bound handbook, architecture, archive, and release evidence are kept for
traceability and are clearly separated from current source truth.

## Supported agent surfaces

| Agent | Managed surface | Status |
|---|---|---|
| Codex | `AGENTS.md` managed section | Supported |
| Claude Code | `CLAUDE.md` managed section | Supported |
| Other agents | declarative adapter contract | Extensible; not implied supported |

Bootstrap preserves user-owned content outside managed sections and fails safe
on ambiguous conflicts.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_docs.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing contracts or schemas.

## License

[MIT](LICENSE)
