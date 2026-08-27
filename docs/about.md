# About AEH

> Status: **CURRENT**

## The short definition

**Adaptive Engineering Harness (AEH) is an independent change-assurance layer
for AI-assisted software engineering.** It turns engineering policy, change
contracts, test evidence, scope, traceability, and approval gates into
machine-checkable acceptance decisions.

In plain language: **the coding agent does the work; AEH makes the change
visible, reviewable, reproducible, and blockable when the evidence is weak.**

## Why this exists

An AI model is a black box from the engineer's point of view. It can generate a
convincing implementation and a convincing explanation, but the explanation is
not independent proof that the change is correct. Asking the same agent to
review itself does not create a separate acceptance authority.

The design path is therefore:

```text
Black-box model
  -> Harness: controls tools, context, permissions, and execution
  -> Workflow: defines ordered engineering states and required artifacts
  -> AEH: independently checks one Change and its evidence
  -> AEW: coordinates projects, agents, tasks, memory, and operations at workspace scale
```

These layers solve different problems. A harness controls an agent session. A
workflow structures work. AEH accepts or blocks a software Change. AEW is the
larger operational workspace and must not silently become AEH's source of
machine truth.

## The central idea

> Generator freedom can increase; acceptance authority must remain independent.

AEH separates four responsibilities:

1. **Agent or developer** — proposes and implements the change.
2. **Contract** — defines what artifacts and transitions are legal.
3. **Validator** — recomputes whether the contract is satisfied.
4. **Evidence** — makes the decision reproducible and reviewable.

Markdown reports are useful navigation, but they are not allowed to override
machine-readable Change state or validator output.

## What AEH currently provides

The `0.3.0.dev0` source line includes:

- repository discovery, bootstrap, and read-only health diagnosis;
- five risk-based workflow levels and per-Change state isolation;
- grounding, requirements, acceptance criteria, test design, RED/GREEN,
  refactor, verification, approval, review, and repair states;
- test locking, evidence hashes, traceability, and risk gates;
- plan-first repair, upgrade, transaction journals, rollback, and recovery;
- manual verification, approval expiry/TTL, and provenance-preserving revocation;
- constrained no-shell-by-default process launch with explicit shell authorization;
- credential-bound protected approvals and signed revocation;
- Codex and Claude adapter generation;
- bounded, read-only Git/SVN inspection and deterministic AEW governance export.

## When it is worth using

AEH is best used selectively where a wrong change has meaningful cost:

- security, permissions, money, identity, or irreversible data changes;
- shared contracts, migrations, infrastructure, release, or compliance work;
- changes produced by powerful agents with broad repository access;
- work that needs an audit trail or an independent acceptance decision.

For trivial or easily reversible edits, the full workflow can cost more than it
returns. AEH's own Phase 2 evidence supports **selective independent assurance**,
not a mandatory unattended workflow for every coding task.

## Honest boundaries

AEH is not an autonomous coding agent, orchestration platform, remote CI
service, identity provider, or general-purpose OS sandbox. It stops at
`MERGE_READY`; push, pull request, merge, and release remain external actions.

M5 provides a portable constrained-process boundary and HMAC credential
verification. Those controls do not provide kernel isolation, public-key
non-repudiation, OIDC, enterprise IAM, or legal human identity. M6 remains
planned; deep user-project CI integration and multi-agent orchestration are not
current capabilities. The latest public release is
`v0.2.0`; `0.3.0.dev0` is unreleased, and no AEH version is published to PyPI.

## Continue reading

- [Current status](status.md)
- [Current architecture](architecture-current.md)
- [Engineering guide](engineering-guide.md)
- [Research narrative](research/README.md)
- [AEW integration](integrations/aew.md)
