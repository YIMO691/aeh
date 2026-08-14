# Contributing to AEH

Thank you for contributing. This file assumes you know nothing about AEH's
internal history — everything you need is in the repository.

## Development environment

Python 3.10+, PyYAML, jsonschema. Editable install:

    python -m venv .venv
    .venv\Scripts\activate        # Windows；POSIX 用 source .venv/bin/activate
    pip install -e .
    aeh doctor <any-bootstrapped-target>

## Running tests

    python -m unittest discover -s tests -p "test_*.py"   # full regression
    python tests/contract/test_contracts.py              # per-suite

Every fix must ship with a regression test.

## V0.1 feature freeze

V0.1 accepts ONLY: release blockers (P0/P1), security fixes, install/CLI/
cross-platform fixes, documentation corrections, obvious UX blockers. Each fix
is recorded in docs/decisions.md as RELEASE-FIX-### with problem / root cause /
fix / regression test / semantic-change flag. New features belong to the V0.2
roadmap (repair, upgrade, CI integration, RAG, Web UI, mutation testing, impact
analysis, multi-agent orchestration, new approval systems, new workflow levels).

## Project anatomy

- core/ — frozen contracts (workflow, states, gates, precedence, classifications, evidence). Change = architecture decision.
- schemas/ — JSON-Schema contracts; machine truth for every artifact.
- bootstrap/ — discovery rules, interview questions, grounding rules (data-driven).
- src/aeh/ — runtime (bootstrap pipeline, doctor, conflict/compiler, adapters, change runtime).
- tests/ — contract + runtime suites; fixtures are synthetic and public-safe.

## How to add a discovery rule

Edit bootstrap/discovery/<domain>.yaml following schemas/discovery-rule.schema.json
(detector: id, field, value, confidence, markers). Multi-valued facts must be
declared in multi_fields so the compiler folds them deterministically. Add a
detection test in tests/discovery/.

## How to add an interview question

Edit bootstrap/interview/<scope>.yaml (question_id, type, field, options,
default). Interview answers resolve through the frozen precedence order
(system > organization > project > team > task > developer > default).

## How to add an adapter

Create adapters/<platform>/adapter.yaml + template, following
schemas/adapter.schema.json and schemas/adapter-output.schema.json. Adapters
are pure renderers: they never re-decide semantics, never relax deny, and must
report unsupported capabilities as GUIDANCE_ONLY.

## How to change a contract

Contract changes are architecture decisions:

1. Propose the change + rationale in the PR description.
2. Update the schema/core file AND every consumer (runtime + tests + fixtures).
3. Run the full regression; any legal/illegal fixture may only change when the
   Owner has approved the decision (see docs/decisions.md CD log).
4. Same-level conflicting values stay BLOCKED_POLICY_CONFLICT — never silently pick one.

## Architecture decisions

Record every machine-visible decision in docs/decisions.md as CD-### (contract
decision) or RISK-### (deferred risk). docs/architecture.md is the canonical
frozen architecture — superseded copies live only in docs/archive/.

## Reporting security issues

Please report security issues privately to the maintainers before opening a
public issue. Do not include secrets or private policy content in public issues;
machine truth files must keep minimum disclosure (effective constraint + ref id
only, never the private body).

## Release discipline

AEH is the Validator, not the Coding Agent. Runtime modules never write
APPROVED; approval is recorded only by aeh change approve as honest human
attestation. Approval can never override a technical failure.
