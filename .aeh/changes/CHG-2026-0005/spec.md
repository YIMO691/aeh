# Spec

machine truth in spec.yaml

## REQ-001 [DESIRED] A governed Change with stale post-GREEN evidence can legally restart repair from REFACTOR.
- AC-001-01 (automated) REFACTOR can enter SPEC_REPAIR or TEST_REPAIR only through the existing explicit repair conditions.
- AC-001-02 (automated) REFACTOR or SPEC can return to GROUND only through an explicit GROUNDING_STALE repair condition.
- AC-001-03 (invariant) Repair never requires or permits direct editing of machine-owned Change state.
## REQ-002 [DESIRED] AEH supports an explicit SCM-authenticated MERGE_GATE delegation for solo repositories without requiring a local HMAC key.
- AC-002-01 (automated) SCM_AUTHENTICATED_MERGE accepts only an APPROVED MERGE_GATE with a human actor and evidence reference, and verification reports READY_WITH_WARNINGS.
- AC-002-02 (invariant) The delegated mode cannot satisfy VERIFY_MANUAL or override any technical failure.
## REQ-003 [DESIRED] Strict HMAC approval remains the default and provider-neutral replay remains fail-closed.
- AC-003-01 (automated) Existing HMAC approval and tamper tests continue to pass without changed call sites.
- AC-003-02 (automated) Provider-neutral replay rejects SCM delegation unless a trusted adapter passes the exact accepted trust mode.
- AC-003-03 (invariant) Repository-controlled CI never receives an HMAC secret and delegated trust is never accepted implicitly.
## REQ-004 [DESIRED] The GitHub adapter makes the trust downgrade visible and delegates final authority to the authenticated SCM merge action.
- AC-004-01 (automated) Configured GitHub replay passes only the declared trust mode and reports merge_approval_channel plus an approval.channel check.
- AC-004-02 (invariant) The reported approval channel always matches the configured provider policy.
