# Design

## Intent

Keep the existing AEH state machine, Gates, evidence, and granular commands. Add a small
Agent-facing decision layer that tells an Agent what to do next and whether the current
task authority is sufficient. The layer does not implement work and does not grant authority.

## Classification facts

`change new --facts <yaml>` accepts optional scoped facts chosen by the Agent from the
actual task: affected paths, sensitive domains, reversibility, and evidence references.
When scoped facts are present, title and repository-wide keywords remain recorded hints,
but only explicit sensitive facts trigger hard escalation. Calls without facts retain the
existing fail-safe behavior for compatibility.

Classification can be reassessed in library code. Reassessment may raise the workflow
level but never silently lower it. Grounding retains its evidence scan while avoiding
repository-wide ambient-domain escalation when scoped facts are available.

## Agent flow

`aeh change continue CHG-* --authority <external-yaml>` reads the existing Change truth
and returns one status: `CONTINUE`, `WAITING_FOR_AUTHORITY`, `BLOCKED`, or `COMPLETE`.
Its next-action table maps installed workflow phases to broad task capabilities. Human
phases always report the exact Gate and are never satisfied by the authority envelope.

The authority file stays outside the repository. It contains a Change binding and a small
allow-list of task capabilities. It suppresses duplicate prompts for already authorized
work but cannot represent or replace HMAC-backed approval.

## Compatibility and safety

- Existing CLI commands and persisted Change artifacts remain valid.
- Existing no-facts classification remains fail-safe and unchanged.
- The new command is advisory and does not transition state or write approval records.
- Approval signing, verification, expiry, credential isolation, and replay are unchanged.
- Codex sees the concise decision contract; detailed levels and commands remain documented
  as advanced/debugging information.
- Regression runs on pull requests and on `main`; feature-branch push no longer duplicates
  the same full matrix. The assurance workflow is not modified.

