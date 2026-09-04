# Adaptive Engineering Harness (AEH)

[![AEH regression](https://github.com/YIMO691/aeh/actions/workflows/regression.yml/badge.svg?branch=main)](https://github.com/YIMO691/aeh/actions/workflows/regression.yml)
[![Latest release](https://img.shields.io/github/v/release/YIMO691/aeh)](https://github.com/YIMO691/aeh/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[简体中文](README.zh-CN.md) · [Codex usage guide](docs/codex-usage.md) · [Documentation](docs/README.md)

> Status: **CURRENT**
> Source: `0.3.0.dev0` (unreleased) · Latest GitHub release: `v0.2.0` ·
> M1–M6 merged · PyPI not published

AEH is an independent acceptance layer for software changes made with coding
agents. Codex can write the change; AEH makes the requirements, tests,
evidence, approvals, and final decision explicit and replayable.

Use it when a mistake would cost more than a quick retry: shared contracts,
permissions, migrations, money, releases, infrastructure, security, or work
performed by a highly autonomous agent.

## What changes when you use AEH?

Without AEH, the same agent can implement a change, run its own tests, and tell
you that the work is safe. With AEH, acceptance is a separate process:

```text
your intent -> risk-sized workflow -> implementation -> independent checks -> your decision
```

AEH records what was requested, locks the relevant test evidence, rejects
illegal state changes, and stops at human Gates when authority is required. A
confident agent response or a passing test is useful evidence, but neither is
treated as proof by itself.

## Use AEH with Codex

After AEH is installed in a repository, you can work in natural language. For
a normal change, tell Codex:

> Use AEH for this change. Inspect the repository instructions, choose the
> lightest safe workflow, create the Change, implement and verify locally.
> Stop before commit, push, PR, merge, release, or any credential-backed Gate
> unless I authorize that step separately.

For a small bug:

> Fix the incorrect empty-state message. Treat this as a small bug, add a
> focused regression test, and use the lightest AEH workflow that the evidence
> permits. Work locally only.

For a sensitive change:

> Change the payment permission check using AEH. Treat it as CRITICAL, preserve
> raw evidence, and stop at every human Gate for separate approval.

See [Using AEH with Codex](docs/codex-usage.md) for ready-to-copy prompts,
staged authorization examples, and what Codex should report at each stop.

## Choose the lightest safe workflow

AEH is intentionally not equally heavy for every change.

| Level | Use it for | Typical path |
|---|---|---|
| `DIRECT` | tiny, low-risk, easily reversible edits | classify → implement → basic verify |
| `LIGHTWEIGHT` | ordinary bugs with a focused regression test | targeted ground → bug contract → RED/GREEN → verify |
| `STANDARD` | features and cross-file behavior changes | ground → spec → test design → RED/GREEN → review |
| `CRITICAL` | security, money, identity, permissions, migration, release, or high-impact automation | STANDARD plus independent human Gates and stronger evidence |

`EXPLORE` is available for experiments that may be discarded or later promoted
into a governed change. Classification can escalate when repository evidence
shows wider impact; an agent should not silently downgrade it.

## Install

AEH requires Python 3.10 or newer. No AEH package is currently published to
PyPI.

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

## Bootstrap a repository

Try AEH on a disposable repository first:

```bash
aeh bootstrap /path/to/project
aeh doctor /path/to/project
```

Bootstrap installs a versioned `.aeh/` runtime snapshot and managed agent
instructions. In a governed repository, Codex reads `AGENTS.md`,
`.aeh/profile.yaml`, and `.aeh/effective-workflow.yaml` before implementation.

If you want to drive the lifecycle directly instead of asking Codex, start a
Change with the CLI:

```bash
cd /path/to/project
aeh change new "fix duplicate claim side effect" --level LIGHTWEIGHT
aeh change status CHG-2026-0001
```

The exact next commands depend on the effective workflow. The
[engineering guide](docs/engineering-guide.md) covers the full CLI lifecycle,
repair, upgrade, approvals, CI replay, and coordination.

## Authority stays staged

AEH does not treat “implement this” as permission to publish it. Keep these
decisions separate:

1. inspect and plan;
2. modify and verify locally;
3. commit;
4. push and open a pull request;
5. merge;
6. tag, release, deploy, or publish.

Credential-backed Gates are separate again. A credential should be scoped to
one Change and one Gate, kept outside the repository and evidence, and never
reused for another Gate.

AEH itself stops at the governed decision boundary. It does not automatically
push, create a PR, merge, deploy, or release.

## Trust boundary

AEH provides versioned contracts, evidence integrity, test locking, explicit
mutation boundaries, constrained process launch, credential-bound approvals,
read-only CI replay, and bounded single-host Change coordination.

It does **not** provide:

- public-key identity, legal non-repudiation, enterprise IAM, or hardware key custody;
- kernel, container, VM, filesystem, network, syscall, or process-tree isolation;
- an unbypassable hosted CI service or automatic branch-protection configuration;
- cross-host or network-filesystem coordination correctness;
- automatic push, PR, merge, deployment, release, or PyPI publication.

HMAC proves possession of a configured shared secret; it does not prove legal
identity. Source files alone do not prove that external SCM controls are active.
Read [M5 security](docs/m5-security.md),
[M6.2 GitHub assurance](docs/m6-2-github-assurance.md), and
[M6.3 coordination](docs/m6-3-coordination.md) for precise boundaries.

## Current status

The current source version is `0.3.0.dev0`; the latest public release is
`v0.2.0`. M1–M6 and M6.3A/B/C are merged, while the current source line remains
unreleased and PyPI remains unpublished. The current regression baseline is
412 tests: 408 passed and 4 expected Windows symlink-permission cases skipped.

See [AEH Current Status](docs/status.md) for exact merge and CI evidence. The
[V0.2 roadmap](docs/roadmap-v0.2.md) is a completed, version-bound planning
record rather than the source of current operational truth.

## Documentation

- [Using AEH with Codex](docs/codex-usage.md)
- [Documentation portal](docs/README.md)
- [About AEH](docs/about.md)
- [Current status](docs/status.md)
- [Current architecture](docs/architecture-current.md)
- [Engineering guide](docs/engineering-guide.md)
- [Security boundary](docs/m5-security.md)
- [Contributing](CONTRIBUTING.md)

Version-bound research, handbook, archive, and release evidence are retained
for traceability and are not promoted to current truth.

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
