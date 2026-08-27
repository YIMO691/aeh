# Changelog

All notable changes to AEH are recorded here per phase.

## [0.3.0.dev0] — Unreleased

### Added

- M6.1 provider-neutral `aeh ci verify`: a target-read-only replay of committed
  Change Assurance evidence bound to canonical SCM repository identity, exact
  base/head, installed runtime, explicit observed time, externally held
  approval credentials, all consumed file hashes, and a deterministic report
  digest. It never executes project-declared commands.
- Versioned CI replay policy/report contracts, legal/illegal fixtures, real
  Change-flow attack tests, external-only report output, and bootstrap/upgrade/
  wheel propagation through the existing runtime snapshot mechanism.

- M5 constrained process execution: structured argv and compatibility command
  strings run with `shell=False`; shell syntax requires a locked plan
  declaration plus per-invocation `--allow-shell`; cwd, timeout, argument, and
  environment limits are enforced by a versioned runtime policy.
- M5 credential-bound approval decisions using HMAC-SHA256 over canonical
  Change/Gate/actor/time/TTL/evidence payloads. Revocation preserves the
  original signature and adds an independently signed revocation credential;
  protected positive Gates reject missing, wrong-key, tampered, or replayed
  credentials.
- A current M5 security/threat-model document and attack regressions for shell
  injection, cwd escape, environment leakage, payload mutation, wrong key, and
  cross-Change replay.
- A current documentation portal, product About, source-status page, implemented
  architecture, engineering guide, and a current-state supplement for the
  version-bound handbook.
- A bounded documentation contract and regression checker that align public
  version/release/milestone claims with package metadata, require current versus
  version-bound labels, and validate maintained local Markdown links.
- M4 governance hardening merged through PR #11: the dedicated
  `VERIFY_MANUAL` human gate, bounded approval TTL, explicit provenance-
  preserving revocation, and CLI support through `--ttl-seconds` / `REVOKED`.
- TEST_DESIGN now rejects CRITICAL plans that omit declared integration or
  contract verification; VERIFY retains the check for legacy plans.
- Read-only `aeh integration inspect` for bounded local Git/SVN/no-SCM
  identification and nested repository boundary discovery.
- Deterministic `aeh integration export` envelopes that link external
  Project/Task/Run IDs to AEH-owned Change state, verdicts, artifact hashes,
  and Scope/Ownership/Authority/Lifecycle/Provenance/Cost metadata.
- JSON Schemas and contract/CLI regressions for both integration surfaces.
- A public research narrative tracing the design from black-box model limits to
  Harness, deterministic Workflow, AEH Change Assurance and the separate AEW
  operational architecture, with research method and source/limitation maps.

### Boundaries

- M6.1 is an acceptance replay core, not a hosted or universally unbypassable
  CI service. SCM required checks, workflow/ruleset protection, bypass control,
  runner/time trust and merge enforcement remain M6.2; Change concurrency is
  M6.3. AEH still does not merge, push, deploy, or orchestrate agents.

- The Handbook v0.2, Phase 0 architecture, Repository Panorama, release
  evidence, and archive remain version-bound history. The alignment adds
  navigation and explicit status labels rather than rewriting old evidence as
  current truth.
- HMAC credentials prove possession of a configured shared secret, not legal
  human identity, public-key non-repudiation, OIDC, enterprise IAM, or hardware
  custody. Historical unsigned approvals remain readable but cannot unlock M5
  protected positive Gates.
- M4 is assigned to the new `0.3.0.dev0` source line rather than being silently
  folded into the frozen v0.2.1 integrity-patch candidate.
- The integration does not add an external workspace state store, memory, or
  multi-agent orchestrator to AEH. M5 process policy is not kernel, container,
  VM, filesystem, network, syscall, or process-tree isolation.
- SCM inspection is local, bounded, read-only, and network-free. Recognizing
  an SVN working copy does not yet certify the full AEH lifecycle on SVN.
- `0.3.0.dev0` is development metadata, not a tag, GitHub Release, or PyPI
  publication. The latest public release remains v0.2.0.

### Validation status

- M6.1 raises the expected Windows baseline to `347` discovered (`343` passed,
  `4` expected symlink-permission skips), including real Change-flow replay,
  deterministic/zero-write assertions and repository/head/base/runtime/test-
  lock/evidence/traceability/credential attack cases.

- M5 raises the expected Windows baseline to `331` discovered (`327` passed,
  `4` expected symlink-permission skips), including 13 focused execution and
  credential threat-model tests plus contract invariants.
- Documentation alignment adds one contract/link regression, bringing the
  expected current Windows baseline to `316` discovered (`312` passed and `4`
  expected symlink-permission skips); the final exact-commit result is recorded
  by the review PR and CI.
- M4 source and compatibility regression: `314` tests completed (`310` passed,
  `4` expected Windows symlink-permission skips).
- PEP 517 wheel build and clean-room install smoke passed; the installed wheel
  exposed `VERIFY_MANUAL`, `--ttl-seconds`, and `REVOKED`, and retained
  bootstrap/doctor/repair/upgrade/change/AEW-integration smoke coverage.
- PR #11 passed 12/12 checks before merge; the resulting `main` merge commit
  passed all six post-merge cross-platform regression and wheel jobs.
- Post-merge version reconciliation completed `315` tests (`311` passed,
  `4` expected Windows symlink-permission skips). The `0.3.0.dev0` wheel
  metadata and clean-room lifecycle smoke passed.

## [0.2.1] — Unreleased

### Fixed

- Make change-scoped YAML/JSON machine truth Controller-owned by sealing an
  external checkpoint at RED/LOCK_TEST and rejecting untrusted additions,
  removals, edits, symlinks, and Windows reparse points.
- Re-check provenance after every repository-controlled test subprocess in
  repeated RED, GREEN/REFACTOR, and VERIFY, closing the RUN-F055 test-time
  laundering route before Controller truth can be written or resealed.
- Fail closed for in-flight changes created without a Controller checkpoint.

### Validation status

- The remediation head passed 288 local zero-model tests (3 platform skips),
  build/diff/clean-room checks, 12/12 pull-request checks, and the post-merge
  `main` workflow. The V0.2.1 candidate adds an upgrade regression and passes
  289 local tests (3 platform skips) plus its fixed-epoch clean-room wheel gate.
- This entry describes a release candidate only. No `v0.2.1` tag, GitHub
  Release, or PyPI publication has occurred. The bounded remediation model
  rerun and A01–A08 attack evaluation were completed separately and merged in
  the evaluation repository; they did not publish or release AEH.
- The frozen Phase 2 v1.10 verdict remains `REPOSITION`; this patch fixes the
  observed integrity escape but does not by itself prove product effectiveness.

## [0.2.0] — 2026-08-20 (RELEASED to https://github.com/YIMO691/aeh/releases/tag/v0.2.0)

### Added

- M1: relocatable wheel resource bundle and Windows/Linux regression CI.
- M2: plan-first `aeh repair`, persistent BST/RPR transaction journals, byte backups,
  drift-safe apply/rollback, Doctor remediation, and TEST_REPAIR/SPEC_REPAIR routing.
- M3: plan-first `aeh upgrade`, UPG journals, explicit v0.1 runtime snapshot migration,
  deterministic manifest upgrade history, protected project-data boundaries, and rollback.

### Release execution

- M1–M3 are merged to `main`; tag `v0.2.0` and the GitHub Release are public.
- A relocatable wheel is attached to the GitHub Release with its SHA-256 recorded
  in `docs/releases/v0.2.0/RELEASE_CHECKLIST.md`.
- PyPI publication is not authorized and has not occurred.
- Product effectiveness remains `NOT_YET_PROVEN`; Phase 2 / 72-run remains unauthorized.
- Independent Release Safety Review: `READY_FOR_OWNER_RELEASE`; P0=0, P1=0.

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
