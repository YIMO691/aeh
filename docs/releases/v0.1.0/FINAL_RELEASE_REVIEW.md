# AEH V0.1.0 — Final Release Review

This is the single document the Owner reviews for the V0.1.0 release decision.

release:
  project: Adaptive Engineering Harness
  version: 0.1.0
  status: RELEASE_CANDIDATE

source:
  branch: n/a (AEH dir is not a standalone git repository yet; deferred to Owner)
  head_commit: n/a
  parent_repo: main @ 6f00a3cf7f04d69658a3712f68e3508e0983d317 (AEH dir untracked)
  dirty: n/a (parent repo has unrelated pre-existing changes outside AEH; untouched by this task)

feature_freeze:
  status: PASS
  evidence: no V0.2 features added; all changes are release-fixes or documentation.

public_safety:
  secrets: PASS (0 secret files; all keyword hits are fake test fixtures or domain keyword hints)
  company_private_data: PASS (public docs redacted — RELEASE-FIX-006; tests keep fixture-role forbidden-word lists)
  private_policy: PASS (private bodies never appear in public output; minimum disclosure enforced and tested)
  absolute_paths: PASS (0 drive paths in README/docs/examples)
  generated_artifacts: PASS (egg-info, __pycache__, pyc removed; .gitignore covers the rest)

tests:
  automated:
    total: 232
    passed: 232
    failed: 0
    command: python -m unittest discover -s tests -p "test_*.py"

dogfood:
  status: PASS (CHG-2026-0001, CRITICAL escalation, VERIFY_COMPLETE / READY_WITH_WARNINGS)

pilots:
  lightweight: PASS (MERGE_READY)
  standard: PASS (MERGE_READY)
  critical: PASS (READY_WITH_WARNINGS, human approval)
  explore: PASS (no forced TDD)

clean_room:
  install: PASS (fresh venv, pip install -e ., aeh --help)
  bootstrap: PASS (x2 idempotent: semantic diff 0, installed_at stable, managed blocks not duplicated)
  doctor: PASS (READY_WITH_WARNINGS, warnings explained)
  first_change: PASS (full standard chain -> VERIFY_COMPLETE / MERGE_READY)

cold_start:
  result: PASS (fresh agent answered all 10 onboarding questions from repo docs alone)
  evidence: COLD_START_REVIEW.md
  findings_fixed: answers example moved to examples/answers.yaml; panorama banner; upgrade wording; scratch files removed

agents:
  codex: PASS (RENDERED, deny honored, GUIDANCE_ONLY reported)
  claude: PASS (RENDERED, deny honored, GUIDANCE_ONLY reported)
  semantic_equivalence: PASS (same profile, identical semantics)

documentation:
  readme: PASS (13 sections, first screen = What/Why/Agents/Install/Quick Start)
  quick_start: PASS (every command executed verbatim in clean-room)
  contributing: PASS (dev env, tests, freeze, rules/adapters/contracts, ADR, security reporting)
  changelog: PASS (v0.1.0, capabilities, release-fixes, known limitations)
  examples: PASS (minimal + generic-business + answers.yaml; marked "Example / Not production certified")
  limitations: PASS (13 items in KNOWN_LIMITATIONS.md + README §12)

license:
  type: MIT
  copyright_holder: YIMO691
  status: OWNER_CONFIRMED

release_blockers:
  p0: []
  p1: []
  accepted_p2:
    - manual verification pending until REVIEW
    - CRITICAL escalation requires declared integration/contract verification
    - editable install only (relocatable wheel post-V0.1)
    - human approval is attestation-level (strong identity post-V0.1)

release_fixes:
  - id: RELEASE-FIX-005
    blocker: P1 (README test command found 0 tests)
    root_cause: unittest discover requires package markers
    fix: tests/ + suite dirs __init__.py added
    regression: full discover run 232/232
  - id: RELEASE-FIX-006
    blocker: P1 (public-safety: private project names in public docs)
    root_cause: frozen docs named internal project/engine names in red-line statements
    fix: reworded to generic form; semantics unchanged; tests keep fixture-role lists
    regression: re-scan shows 0 hits in docs; full regression PASS
  - id: RELEASE-FIX-007
    blocker: P2 (cold-start discoverability)
    root_cause: answers example hidden in test file; panorama target-shape ambiguity; upgrade wording
    fix: examples/answers.yaml + README ref; panorama banner; KNOWN_LIMITATIONS note
    regression: cold-start subagent re-verified (docs-only)

release_verdict: READY_FOR_OWNER_RELEASE

owner_decisions:
  copyright_holder: YIMO691 (confirmed)
  release_publicly: yes (confirmed)
  accepted_limitations: yes (confirmed)
  git_repo_init_and_commit: authorized (push authorized) (currently: dir untracked inside parent repo)