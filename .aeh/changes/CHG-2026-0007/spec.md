# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] This authorization ends before commit or publication.
- AC-001-01 (invariant) No local commit, push, pull request, merge, SCM administration mutation, bypass, Gate credential, tag, Release, or PyPI operation occurs.
## REQ-002 [DESIRED] A first-time user can understand what AEH does, when it is useful, and how to start using it with Codex without first reading the implementation architecture.
- AC-002-01 (automated) README.md links the Chinese README and Codex guide and contains a user-outcome introduction, a Codex prompt example, and the four risk-proportional workflow levels.
- AC-002-02 (invariant) The README preserves the source-install and unreleased/PyPI boundaries and does not claim that an AI agent or a passing test alone is trustworthy proof.
## REQ-003 [DESIRED] Chinese-speaking Codex users receive copyable prompt patterns for small bugs, normal features, and critical changes, with explicit staged authorization boundaries.
- AC-003-01 (automated) README.zh-CN.md and docs/codex-usage.md exist, are linked from the documentation portal, cover DIRECT, LIGHTWEIGHT, STANDARD, and CRITICAL, and contain local-only and publish authorization examples.
- AC-003-02 (invariant) The guidance never treats implementation approval as permission to commit, push, create a PR, merge, publish, bypass policy, or generate Gate credentials.
## REQ-004 [DESIRED] Current project status and planning documents distinguish the completed M1-M6 capability milestone from the later documentation-alignment merge and from future uncommitted work.
- AC-004-01 (automated) docs/status.md records PR 22, merge debf35196ce5b9f649e6ff270327854224fccaee, and postmerge run 33745066439; docs/roadmap-v0.2.md is labeled completed and version-bound rather than current.
- AC-004-02 (invariant) Historical M6 evidence remains attributable to its original PR and merge while the latest documentation baseline is separately identified.
## REQ-005 [DESIRED] Documentation validation fails when the new public entry points, risk-level guidance, authorization boundary, or current status facts drift.
- AC-005-01 (automated) scripts/check_docs.py and tests.documentation.test_documentation enforce the new files, links, required concepts, and exact current-status identifiers, and both checks pass after implementation.
- AC-005-02 (invariant) The final local diff is limited to the declared documentation, documentation checker/test, and CHG-2026-0007 artifacts.
