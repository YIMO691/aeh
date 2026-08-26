# Adaptive Engineering Harness (AEH)

Machine-enforced SDD + TDD harness for **Codex** and **Claude** coding agents.
AEH does not write your code — it installs a contract layer into your repository,
so that agents must work through evidence, spec, tests and verification, with
independently enforced gates.

> V0.2.0 is the latest GitHub release. The current source is the unreleased
> V0.2.1 integrity-patch candidate, which adds Controller-owned machine-truth
> isolation. Neither version is published to PyPI; install from a trusted
> GitHub release asset or source checkout.

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

Install AEH from a source checkout using the standard, non-editable wheel path:

    git clone <repo-url>
    cd adaptive-engineering-harness
    python -m venv .venv
    .venv\Scripts\activate        # Windows；POSIX 用 source .venv/bin/activate
    python -m pip install .
    aeh --help

The build embeds the canonical `core/`, `schemas/`, `bootstrap/`, and `adapters/`
resources in the wheel, so `aeh` can run from any working directory. AEH is not
published to PyPI yet; install from a trusted checkout or an internally built wheel.

For AEH development, use an editable install and run the full regression:

    python -m pip install -e .
    python -m unittest discover -s tests -p "test_*.py"

To reproduce the clean-room wheel gate locally:

    python -m pip wheel --no-deps . --wheel-dir dist
    python scripts/cleanroom_smoke.py --wheel "dist/*.whl"

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

### Repair and rollback (V0.2 M2 development baseline)

Doctor never repairs automatically. Inspect the deterministic dry-run plan first,
then opt in to the exact writes:

    aeh repair .
    aeh repair . --apply

Each applied bootstrap or repair transaction has a persistent journal and byte-level
backups under `.aeh/transactions/`. Rollback refuses to overwrite later edits:

    aeh repair . --rollback RPR-2026-0001

Repair covers canonical runtime restoration, bounded managed-section repair, atomic-write
residue, and the `.aeh/private/` gitignore boundary. A runtime source/version mismatch is
blocked and must use the explicit upgrade command or a matching older repair source.

### Explicit upgrade (V0.2 M3 candidate)

Upgrade is also plan-first. It validates that the installed runtime still matches its old
manifest before showing the runtime/manifest diff:

    aeh upgrade . --source-revision <trusted-revision>
    aeh upgrade . --apply --source-revision <trusted-revision>

Only `.aeh/runtime/core|schemas` and `.aeh/manifest.yaml` are eligible for writes.
Profile, effective workflow, bootstrap answers, private data, changes/approvals, agent files,
and `.gitignore` are preserved. Every applied upgrade has a `UPG-*` journal and can be rolled
back while its after-state still matches:

    aeh upgrade . --rollback UPG-2026-0001

Downgrades, damaged source snapshots, and same-version/different-content collisions are blocked.
Automatic/network upgrade, arbitrary historical migrations, and multi-version installs remain
out of scope.

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
   (aeh change approve). RED/LOCK_TEST records a Controller checkpoint outside
   the repository before coding starts; GREEN and VERIFY fail closed if any
   change-scoped YAML/JSON was added, removed, or modified outside a Controller
   command. Output: MERGE_READY /
   READY_WITH_WARNINGS / BLOCKED.
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

### Agent Engineering Workspace integration

AEH can expose Change Assurance truth to an external, provider-neutral
engineering workspace without becoming that workspace's state or runtime
system. Inspect local SCM boundaries first:

    aeh integration inspect /path/to/project

For an installed project and existing Change, export a deterministic envelope
linked to the external canonical Task and Run:

    aeh integration export CHG-2026-0001 \
      --workdir /path/to/project \
      --project-id PROJECT-1 --task-id TASK-1 --run-id RUN-1

The export contains no artifact bodies: only AEH state, native and portable
verdicts, SCM identity, relative evidence references, hashes, and the six
cross-cutting metadata fields Scope, Ownership, Authority, Lifecycle,
Provenance, and Cost. Both commands are local, read-only, and network-free.
See `docs/integrations/aew.md` for ownership and verdict mappings.

## 12. Security / Known limitations (V0.1)

- **Command execution**: test commands run via argv (structured) with a
  command-string compatibility path (shell=True); no OS sandbox. Trust the plan author.
- **Human approval = attestation**, not strong identity: aeh change approve --actor <name>
  records an honest human attestation; no OIDC/IAM/signatures/approval TTL yet.
- **Controller checkpoint boundary**: at RED/LOCK_TEST, change-scoped YAML/JSON
  hashes are stored outside the governed repository (override with
  `AEH_CONTROLLER_STATE_DIR`, which must also remain outside it). This detects
  agent-side machine-truth writes during implementation and later phases.
  GREEN, repeated RED, and VERIFY re-check the checkpoint after every batch of
  repository-controlled test commands and before Controller truth is written,
  so test-time writes are not adopted by the next seal. The boundary still
  assumes the Controller state is protected by an OS/filesystem boundary that
  both the coding agent and executed repository code cannot write; AEH does not
  provide an OS sandbox. An in-flight change created by an older AEH build has no
  checkpoint and therefore fails closed until RED is replayed through a governed
  repair path (or the change is restarted).
- **Multi-file writes are journaled, not filesystem-wide atomic**: bootstrap and repair
  use per-file atomic replace plus persistent backups and rollback; a whole transaction is
  not one OS-level atomic operation.
- **Some adapter capabilities are GUIDANCE_ONLY** (e.g., Codex git_push deny,
  Claude web_access deny) — reported honestly, never silently dropped.
- **Upgrade is deliberately bounded**: explicit full runtime snapshot upgrade only; no network
  discovery, automatic upgrade, incremental patching, or multi-version coexistence.
- No CI deep integration, no automatic merge/push,
  no complex multi-agent orchestration. These are post-V0.1.
- **SVN boundary**: `aeh integration inspect` recognizes an SVN root and nested
  repositories, but bootstrap/change assurance remain primarily tested on Git
  and plain local directories. SCM recognition is not a claim of full SVN
  lifecycle certification.
- **No PyPI release yet**: relocatable wheel installation is supported from a
  trusted checkout or built artifact, but package-index publication is deferred.
- **Manual verification items stay PENDING** until the REVIEW phase — V0.1 has
  no separate approval gate for manual checks.
- **Keyword hints are heuristics**: they escalate (fail-safe), they never
  silently downgrade.

## 13. Software version and development scope

The package metadata in the current source candidate is `0.2.1`; the latest
published release remains `v0.2.0`. M1–M3 and the post-evaluation Controller
machine-truth isolation fix are merged to `main`. V0.2.1 has not been tagged or
released, and PyPI publication remains out of scope.

Phase 2 v1.10 completed 72 frozen runs and recommended `REPOSITION`: use AEH as
selective independent assurance for genuinely high-risk changes, not as a
mandatory unattended workflow for every coding task. The observed RUN-F055
integrity escape is fixed in the V0.2.1 candidate. A bounded remediation rerun
blocked machine-truth laundering in 3/3 attempts, and the A01–A08 suite was
independently adjudicated BLOCKED in 8/8 attempts. This closes the observed
escape but does not overturn the broader `REPOSITION` decision or prove general
product effectiveness.

In scope: bootstrap, doctor, plan-first repair/upgrade/rollback, change lifecycle
(new/ground/spec/test-design/red/green/refactor/verify/approve/review/repair), five-level
workflows, evidence model, test lock, traceability, risk-based verification, and
Codex/Claude adapters, plus read-only SCM inspection and AEW governance export.

Out of scope: automatic/network/incremental/multi-version upgrade, CI deep integration, RAG,
Web UI, mutation testing, impact analysis, multi-agent orchestration, strong
approval identity.
V0.2 sequencing and priorities: see docs/roadmap-v0.2.md.

Architecture and evidence baseline: see `docs/handbook/README.md`. The handbook
remains an explicitly version-bound Phase 1.1 snapshot; the later Phase 2 v1.10
result and remediation status are summarized above rather than retroactively
rewritten into that frozen evidence baseline.

Release evidence and accepted limitations: see
`docs/releases/v0.2.0/RELEASE_CHECKLIST.md`, `RELEASE_TEST_REPORT.md`, and
`KNOWN_LIMITATIONS.md`. V0.2.1 candidate evidence is under
`docs/releases/v0.2.1/`.

## Development

    python -m unittest discover -s tests -p "test_*.py"   # full regression
    python tests/contract/test_contracts.py              # per-suite

See CONTRIBUTING.md, CHANGELOG.md, docs/architecture.md (frozen),
docs/decisions.md (CD/RISK log), docs/pilots/ (V0.1 release evidence).

## License

MIT — see LICENSE.
