# Changelog

All notable changes to AEH are recorded here per phase.

## [0.2.0] — UNRELEASED CANDIDATE

### Added

- M1: relocatable wheel resource bundle and Windows/Linux regression CI.
- M2: plan-first `aeh repair`, persistent BST/RPR transaction journals, byte backups,
  drift-safe apply/rollback, Doctor remediation, and TEST_REPAIR/SPEC_REPAIR routing.
- M3: plan-first `aeh upgrade`, UPG journals, explicit v0.1 runtime snapshot migration,
  deterministic manifest upgrade history, protected project-data boundaries, and rollback.

### Release status

- Candidate only: no v0.2.0 tag, GitHub Release, or PyPI publication.
- Product effectiveness remains `NOT_YET_PROVEN`; Phase 2 / 72-run remains unauthorized.
- A separate Release Safety Review is required after the stacked M1–M3 review chain.

## [0.1.0] — 2026-08-14 (RELEASED to https://github.com/YIMO691/aeh)

### Added

- Phase 0-13: frozen architecture, contracts (core/ + schemas/), discovery,
  interview, conflict/compiler, adapters (Codex/Claude), bootstrap/install,
  doctor, change lifecycle (new/ground/spec/test-design/red/green/refactor/
  verify/approve/review), evidence model, test lock, traceability,
  risk-based verification, human approval path.
- Phase 14 (release): packaging (pip install -e .), README/LICENSE/CONTRIBUTING/
  CHANGELOG, examples, pilot + dogfood evidence under docs/pilots/.

### Fixed (release-fixes)

- release-fix 001: repository packaging assets (pyproject.toml, .gitignore).
- release-fix 002: polyglot repositories could not bootstrap — multi-valued
  discovery facts (repository.language/documentation, architecture.structure)
  now fold deterministically instead of BLOCKED_POLICY_CONFLICT (frozen
  same-level-conflict semantics preserved for genuinely single-valued fields).
- release-fix 003: grounding TEST evidence recorded rel_path relative to the
  tests/ directory, making evidence go stale in the next phase; paths are now
  repository-root-relative and cwd-independent (cross-drive relpath fix).
- release-fix 004: adapters/render.py leaked file handles (ResourceWarning) —
  template reads now close their handles; regression test added.

- release-fix 005: README test command (unittest discover) found 0 tests — tests/
  package markers added; 232/232 via the documented command.
- release-fix 006: public-safety redaction — private project names in public docs
  reworded to generic form (semantics unchanged); tests keep fixture-role lists.
- release-fix 007: cold-start discoverability — examples/answers.yaml added,
  panorama target-shape banner, upgrade wording clarified.

### Dogfood

- AEH bootstrapped itself and completed a real change end-to-end:
  fix template file-handle leak — CRITICAL (hard escalation on its own repo),
  RED/GREEN/REFACTOR/VERIFY + human MERGE_GATE approval → READY_WITH_WARNINGS.
### Known limitations

See README §12 and docs/releases/v0.1.0/KNOWN_LIMITATIONS.md: human approval is
attestation (not strong identity), some adapter capabilities are GUIDANCE_ONLY,
multi-file install is rollback-capable but not a repository-wide atomic
transaction, command-string execution is a compatibility path, no repair/upgrade/
CI integration/auto merge-push/multi-agent orchestration, manual verification
pending until REVIEW, editable install only.

### Release safety

Public-safety review (docs/releases/v0.1.0/RELEASE_CHECKLIST.md): no secrets, no
company-private data, no absolute machine paths, no private policy content, no
generated artifacts in the public tree. V0.1.0 is a release candidate — not
"production ready" or "enterprise certified".
