# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Existing granular AEH commands and persisted Change artifacts remain backward compatible.
- AC-001-01 (invariant) Existing runtime, contract, integration, documentation, and clean-room tests continue to pass after the new tests are added.
## REQ-002 [CONSTRAINT] This authorization ends before any cryptographic human approval, local commit, or remote mutation.
- AC-002-01 (invariant) No HMAC credential, commit, push, pull request, merge, SCM administration mutation, tag, Release, or PyPI publication occurs under this authorization.
## REQ-003 [DESIRED] A task-scoped external authority envelope lets AEH distinguish work already authorized from a genuine user decision boundary.
- AC-003-01 (automated) The continue command accepts an external authority file, reports CONTINUE for an authorized ordinary action, and reports WAITING_FOR_AUTHORITY with the missing capability for an unauthorized action or human Gate.
- AC-003-02 (invariant) An authority envelope never satisfies SPEC_REVIEW, RED_GATE, VERIFY_MANUAL, or MERGE_GATE and never replaces a credential-backed approval.
## REQ-004 [DESIRED] AEH classification uses explicit change facts as the primary risk signal and treats title keywords as warnings rather than sufficient proof of critical impact.
- AC-004-01 (automated) A bounded documentation or ordinary bug Change containing an ambient sensitive word can remain at the Agent-supported level when its facts declare no sensitive impact, while an actual sensitive impact escalates to CRITICAL.
- AC-004-02 (invariant) Evidence-backed escalation is always allowed and an attempted downgrade without explicit facts is rejected or retains the safer level.
## REQ-005 [DESIRED] An Agent can ask AEH for one concise next-action decision instead of exposing the full internal workflow to the user.
- AC-005-01 (automated) The change CLI exposes a continue command that returns exactly one of CONTINUE, WAITING_FOR_AUTHORITY, BLOCKED, or COMPLETE together with the current phase and a machine-readable next action.
- AC-005-02 (invariant) The continue command reuses the installed workflow, state, Gate, and approval truth and does not create a second state machine or silently mutate approval evidence.
## REQ-006 [DESIRED] Codex guidance presents goals, results, and real authority boundaries while keeping levels and granular commands available as advanced detail.
- AC-006-01 (automated) The managed Codex template and Codex usage guide tell the Agent to choose and drive the workflow, use change continue internally, and avoid asking the user to select a level or approve an action already inside the active authority envelope.
- AC-006-02 (invariant) The guidance still forbids permission expansion, Gate credential invention, bypass, and unverified completion claims.
## REQ-007 [DESIRED] GitHub regression runs once for pull-request validation and again only on the resulting main branch state, not for every feature-branch push as a duplicate full suite.
- AC-007-01 (automated) regression.yml limits push-triggered full regression to main while retaining pull_request and workflow_dispatch execution.
- AC-007-02 (invariant) The required assurance workflow and immutable verifier trust path are unchanged.
