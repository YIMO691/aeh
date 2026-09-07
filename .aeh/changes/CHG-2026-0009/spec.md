# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Critical human Gates remain distinct and require explicit task-specific authorization.
- AC-001-01 (invariant) SPEC_REVIEW, RED_GATE, and MERGE_GATE are not inferred from the external capability envelope.
## REQ-002 [DESIRED] Public documentation describes the merged Agent-driven flow and its exact PR
- AC-002-01 (automated) README files, current status, changelog, architecture, documentation contract, and regression checks record PR
- AC-002-02 (invariant) The source remains 0.3.0.dev0, latest public release remains v0.2.0, and PyPI remains unpublished.
## REQ-007 [DESIRED] The Upgrade path can refresh a changed runtime snapshot within the same unreleased development version when the destination source revision is different.
- AC-007-01 (automated) The existing same-version collision regression accepts a different runtime digest for 0.3.0.dev0 with a new source revision and completes the trusted upgrade transaction.
- AC-007-02 (invariant) Same-version refresh remains forbidden for final releases, identical source revisions, source-integrity failures, and downgrades.
## REQ-003 [DESIRED] The installed Change schema accepts the scoped classification facts produced by the merged Agent-driven flow.
- AC-003-01 (automated) The synchronized installed change.schema.json is byte-identical to the canonical source change.schema.json and therefore accepts facts, keyword_hints, and downgrade_blocked.
- AC-003-02 (invariant) Synchronization must not weaken any existing Change schema requirement or CI approval rule.
## REQ-004 [DESIRED] The remediation stays inside the already approved normal commit, push, pull request, required-check, merge, and post-merge verification workflow.
- AC-004-01 (invariant) No SCM administration, bypass, force push, tag, Release, PyPI publication, or mutable assurance artifact is introduced.
## REQ-005 [DESIRED] The repository prevents a future source/runtime snapshot drift from silently breaking the next self-hosted Change in required assurance.
- AC-005-01 (automated) The self-host runtime regression fails on the exact d167 base and passes only after trusted snapshot synchronization.
- AC-005-02 (invariant) The regression checks repository packaging state without executing project-controlled code in CI replay.
## REQ-006 [DESIRED] The repository self-host runtime snapshot matches the runtime contracts shipped by the current source tree.
- AC-006-01 (automated) A repository regression compares the canonical source runtime digest, installed runtime digest, and manifest runtime digest and requires all three to be equal.
- AC-006-02 (invariant) The runtime snapshot and manifest are changed only through an AEH trusted bootstrap or upgrade path, never by direct file editing.
