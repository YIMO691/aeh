# Dogfood: AEH on AEH (V0.1 release evidence)

Target: a full copy of the adaptive-engineering-harness repository itself.
Harness: installed from source (PYTHONPATH=src), python -m aeh.cli.
Change: fix a real Validator bug — adapters/render.py leaked template file
handles (ResourceWarning on every render).

## Flow (no stage faked; blockages recorded)

| Step | Result |
| --- | --- |
| bootstrap (own repo) | BLOCKED_POLICY_CONFLICT → fixed via release-fix 002 (polyglot fact folding) → BOOTSTRAP_COMPLETE |
| change new "修复模板渲染文件句柄未关闭" --level STANDARD | CHANGE_CREATED, classification STANDARD |
| ground | GROUNDING_COMPLETE, **escalated to CRITICAL** (own repo contains hard-domain fixtures — fail-safe, honest) |
| spec | BLOCKED_STALE_EVIDENCE → fixed via release-fix 003 (TEST evidence rel_path) → SPEC_COMPLETE |
| test-design | TEST_DESIGN_COMPLETE (test: render both adapters, assert no ResourceWarning) |
| red | RED_COMPLETE (VALID_RED, signature unclosed_template_file) |
| green | GREEN_COMPLETE (with-block fix; scope manifest src/aeh/adapters/render.py) |
| refactor | REFACTOR_COMPLETE (_read_text helper extraction) |
| approve | MERGE_GATE APPROVED (actor: dogfood-operator, honest attestation) |
| verify | **VERIFY_COMPLETE, overall READY_WITH_WARNINGS, state VERIFY** |

## Findings

1. **P1 (fixed)**: AEH could not bootstrap its own repository — polyglot facts
   (repository.language, architecture.structure, documentation) conflicted at
   the same precedence level. Fixed by deterministic multi-valued fact folding
   (release-fix 002); the frozen same-level BLOCKED_POLICY_CONFLICT rule is
   unchanged for single-valued fields.
2. **P1 (fixed)**: grounding TEST evidence recorded rel_path relative to tests/,
   so every TEST evidence went stale in the next phase; the relpath rebase was
   also cwd-dependent (cross-drive ValueError). Fixed (release-fix 003) with a
   regression test.
3. **P2 (documented)**: CRITICAL escalation at ground requires the test plan to
   declare integration/contract verification entries; a plan written before the
   escalation hits BLOCKED_VERIFICATION_PLAN_INSUFFICIENT at verify. Remediation
   is visible in the ground report (level: CRITICAL) — documented in README §8 (First Change).
4. **P2 (documented)**: manual verification items stay PENDING until REVIEW —
   already a known Phase 13 design decision (CD-097).

## Honest notes

- The GREEN retry required one operator repair: the pilot driver wrote a
  malformed with-block (indentation). This was operator error in the coding step,
  not an AEH defect; GREEN correctly failed on the broken code (GREEN_FAILED)
  and passed after the repair — demonstrating the validator doing its job.
- The change escalated to CRITICAL on grounding because AEH's own test fixtures
  contain economy-domain keywords. Fail-safe over-escalation is by design
  (classifications.yaml); this is recorded as an expected outcome, not a bug.

## Ported fix

release-fix 004: the same handle-leak fix + a regression test landed in
src/aeh/adapters/render.py and tests/adapters/test_adapters.py (16/16 PASS).