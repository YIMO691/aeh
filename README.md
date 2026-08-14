# Adaptive Engineering Harness (AEH)

Machine-enforced SDD + TDD harness for **Codex** and **Claude** coding agents.
AEH does not write your code — it installs a contract layer into your repository,
so that agents must work through evidence, spec, tests and verification, with
independently enforced gates.

> V0.1.0 status: release candidate. See §12 Security / Known limitations.

---

## 1. What AEH is

AEH turns a normal repository into a governed engineering workspace:

- **LLM = reasoning** — Codex/Claude keep writing code.
- **Contract = legality** — machine-readable YAML/JSON contracts define what is allowed and what state counts as done.
- **Validator = independent enforcement** — AEH (not the agent) validates scope, hashes, test locks and gates.
- **Evidence = reproducibility** — every claim lands in a change-scoped evidence directory.

One core, two platforms: the same compiled profile renders enforcement instructions
for Codex (AGENTS.md) and Claude (CLAUDE.md) without semantic drift.

## 2. Why

Coding agents are good at writing code and bad at being audited. AEH gives you:

- evidence-grounded specs (no trust-me requirements),
- test-driven RED → GREEN with a machine-enforced test lock,
- change-scoped isolation (parallel changes never share state),
- risk-based workflow (LIGHTWEIGHT / STANDARD / CRITICAL with hard escalation),
- traceability REQ → AC → TEST → CODE → VER, forward and backward,
- honest human approval that can never override a technical failure.

## 3. Supported agents

| Platform | Surface | Status |
| --- | --- | --- |
| Codex | AGENTS.md managed section | RENDERED, tested |
| Claude Code | CLAUDE.md managed section | RENDERED, tested |

Capabilities a platform cannot enforce are reported honestly as
unsupported_capabilities (GUIDANCE_ONLY) — never silently dropped, never relaxed.

## 4. Installation

V0.1 installs as an editable package (the only supported installation path for
now — see §12 limitations):

    git clone <repo-url>
    cd adaptive-engineering-harness
    python -m venv .venv
    .venv\Scripts\activate        # Windows；POSIX 用 source .venv/bin/activate
    pip install -e .
    aeh --help

## 5. Quick Start

    cd /path/to/your-project
    aeh bootstrap .           # installs .aeh/ + managed agent sections (fail-safe defaults)
    aeh doctor .              # health check — must say READY / PASS before work

    aeh change new "fix duplicate claim side effect" --level STANDARD

Then open Codex or Claude Code in your project and work normally — the managed
section tells the agent what AEH enforces. Drive the workflow yourself:

    aeh change ground CHG-2026-0001
    aeh change spec   CHG-2026-0001 --reqs reqs.yaml
    aeh change test-design CHG-2026-0001 --plan plan.yaml --test-src ./my-tests
    aeh change red    CHG-2026-0001
    aeh change green  CHG-2026-0001 --scope scope.yaml
    aeh change verify CHG-2026-0001
    aeh change approve CHG-2026-0001 --gate MERGE_GATE --status APPROVED --actor <your-name>

Every command above was executed end-to-end in a clean-room environment
(fresh venv + fresh repository) as part of the V0.1 release gate.

### Answers (explicit policy)

Without --answers, bootstrap applies fail-safe defaults and records their
provenance as default_applied with confidence UNKNOWN — honest, but not your
policy. For a real project, answer the interview explicitly:

    aeh bootstrap . --answers answers.yaml

answers.yaml follows schemas/answers.schema.json; copy examples/answers.yaml
(a complete, usable example) and edit it for your project.

## 6. Bootstrap

aeh bootstrap <target> installs into the target repository:

- .aeh/ — manifest, compiled profile, effective workflow, runtime contracts, per-change workspaces,
- a managed section in AGENTS.md / CLAUDE.md (your original content is preserved),
- a .gitignore entry for .aeh/private/.

Bootstrap is deterministic: semantic outputs exclude timestamps; the install plan
is validated before any write.

## 7. Doctor

aeh doctor <target> is read-only and reports BLOCKED / WARN / PASS checks
(installation integrity, runtime contract digests, private-data hygiene, git state,
staging residue). On a fresh repository it honestly reports
install.aeh_exists: BLOCKED → run aeh bootstrap — it never pretends.

## 8. First Change

1. aeh change new "<title>" --level STANDARD — classification (hard-escalation
   keywords like 奖励/领取/money escalate to CRITICAL; fail-safe by design).
2. aeh change ground <id> — evidence scan; polyglot repos are handled
   (multi-valued facts fold deterministically).
3. aeh change spec <id> --reqs reqs.yaml — REQ/AC with stable IDs.
4. aeh change test-design <id> --plan plan.yaml --test-src <dir> — test plan + test file install (test locations only).
5. aeh change red <id> — tests must fail with a recognized signature (VALID_RED) and the test files get locked.
6. Fix the production code (the agent's job), then aeh change green <id> --scope scope.yaml —
   AEH verifies scope hashes, lock integrity and that RED tests now pass.
7. aeh change refactor <id> --scope scope.yaml (optional, structural-equivalence refactor).
8. aeh change verify <id> — verification + traceability; CRITICAL requires a
   declared integration/contract verification entry and human MERGE_GATE approval
   (aeh change approve). Output: MERGE_READY / READY_WITH_WARNINGS / BLOCKED.
9. aeh change review <id> — projects review.md (narrative only; machine truth is YAML).

**AEH stops at MERGE_READY.** Merge, push, PR and release remain external systems.

## 9. Five workflow levels

| Level | Shape | Gates |
| --- | --- | --- |
| DIRECT | trivial comment/typo | classification + basic verify |
| LIGHTWEIGHT | small bug | ground → spec → RED → GREEN → VERIFY |
| STANDARD | normal feature | + test-design gate, test lock |
| CRITICAL | money/persistence/protocol/security… | hard escalation, deep grounding, integration/contract verification, human approval |
| EXPLORE | spike | HYPOTHESIS → EXPERIMENT → EVIDENCE → DECISION (no forced TDD) |

Hard escalation domains: money_economy, persistence, save_migration,
protocol_compatibility, authentication_authorization, security_boundary,
irreversible_migration, destructive_data_operation.

## 10. SDD/TDD runtime overview

- **SDD**: requirements come from evidence (or explicit user requirements), compiled into a spec with acceptance criteria.
- **TDD**: each automated AC gets a test; RED proves the test fails for the right reason; GREEN proves the fix; a test lock guarantees nobody edits tests mid-cycle.
- **Verification closes the loop**: target tests + regression + declared verification, risk-based depth, full REQ↔AC↔TEST↔CODE↔VER traceability, orphan detection.

## 11. Extending AEH

- Schemas in schemas/, frozen core contracts in core/, runtime modules in src/aeh/runtime/.
- Discovery rules are data-driven (bootstrap/discovery/*.yaml).
- Agent adapters are pure renderers (src/aeh/adapters/render.py) — adding a platform does not touch core semantics.

## 12. Security / Known limitations (V0.1)

- **Command execution**: test commands run via argv (structured) with a
  command-string compatibility path (shell=True); no OS sandbox. Trust the plan author.
- **Human approval = attestation**, not strong identity: aeh change approve --actor <name>
  records an honest human attestation; no OIDC/IAM/signatures/approval TTL yet.
- **Multi-file install is rollback-capable but not a repository-wide atomic
  transaction**: bootstrap stages → validates → applies; individual file writes
  are not a single atomic unit.
- **Some adapter capabilities are GUIDANCE_ONLY** (e.g., Codex git_push deny,
  Claude web_access deny) — reported honestly, never silently dropped.
- **No repair/upgrade system**, no CI deep integration, no automatic merge/push,
  no complex multi-agent orchestration. These are post-V0.1.
- **Editable install only**: pip install -e . keeps core/schemas beside the
  source tree; a relocatable wheel with data files is post-V0.1.
- **Manual verification items stay PENDING** until the REVIEW phase — V0.1 has
  no separate approval gate for manual checks.
- **Keyword hints are heuristics**: they escalate (fail-safe), they never
  silently downgrade.

## 13. Current V0.1 scope

Feature freeze is in effect: V0.1 accepts only release blockers, security and
documentation fixes — no new features.

In scope: bootstrap, doctor, change lifecycle (new/ground/spec/test-design/red/green/
refactor/verify/approve/review), five-level workflows, evidence model, test lock,
traceability, risk-based verification, Codex/Claude adapters.

Out of scope (V0.2+): repair/recover, upgrade system, CI deep integration, RAG,
Web UI, mutation testing, impact analysis, multi-agent orchestration, strong
approval identity.

## Development

    python -m unittest discover -s tests -p "test_*.py"   # full regression
    python tests/contract/test_contracts.py              # per-suite

See CONTRIBUTING.md, CHANGELOG.md, docs/architecture.md (frozen),
docs/decisions.md (CD/RISK log), docs/pilots/ (V0.1 release evidence).

## License

MIT — see LICENSE.