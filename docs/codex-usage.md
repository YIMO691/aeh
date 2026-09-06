# Using AEH with Codex

> Status: **CURRENT**
> Source line: `0.3.0.dev0`

This guide shows how to use AEH from a Codex conversation without choosing a
workflow or memorizing the CLI. You state the goal and authority boundary;
Codex drives the workflow and AEH validates the resulting truth.

## The short version

In an AEH-enabled repository, give Codex the goal and the boundary once:

> Use AEH for this task. Decide the lightest safe workflow from the actual
> change, implement and verify locally, and continue without asking me about
> internal stages. Stop only if the scope expands, a check fails, or an action
> falls outside my authority: no commit, push, PR, merge, release, or Gate
> credential.

Codex should maintain a task-scoped authority envelope outside the repository
and call `aeh change continue` internally. `CONTINUE` means the next action is
already authorized; `WAITING_FOR_AUTHORITY`, `BLOCKED`, and `COMPLETE` are the
only reasons to interrupt or finish. Do not ask the user to choose a workflow level.

## What the Agent decides internally

The levels remain useful for audit and debugging, but they are not questions
the user must answer. Codex considers actual scope, reversibility, external
side effects, uncertainty, and evidence. Title keywords are hints, not proof
that an unrelated sensitive subsystem is being changed.

### Tiny, reversible edit (`DIRECT`)

> Correct the typo in the command description. Use AEH and work locally only.

`DIRECT` is for a genuinely small change whose failure is easy to detect and
undo. If grounding reveals broader behavior or contract impact, Codex should
escalate rather than force the task to remain DIRECT.

### Focused bug (`LIGHTWEIGHT`)

> Fix the empty-state message shown after the final item is deleted. Add a
> focused regression test, demonstrate the failure before the fix, implement
> it, and verify locally. Stop before commit.

This is the normal choice for a small bug: a bounded bug contract and a real
RED/GREEN result, without the full feature process.

### Feature or cross-file change (`STANDARD`)

> Add CSV export to the report screen using AEH. Implement and verify locally.
> Do not push or open a PR.

Use STANDARD when the change adds behavior, crosses components, or needs an
explicit specification and traceability.

### Sensitive change (`CRITICAL`)

> Change the payment permission rules using AEH. Preserve raw evidence and stop
> only when a human Gate actually requires my decision. Never create or reuse a
> credential unless I authorize that exact Change and Gate.

CRITICAL is appropriate for security, money, identity, permissions, migration,
release, infrastructure, compliance, and high-impact autonomous work. It adds
human decision points; it does not allow an agent to manufacture approval.

### Exploration (`EXPLORE`)

> Explore whether incremental parsing would improve this command. Keep the work
> disposable, record the hypothesis and evidence, and do not promote it into a
> production Change unless I approve the scope.

EXPLORE lets uncertain work end in discard or promotion. It is not a shortcut
around production Gates.

## Give one useful authority boundary

Do not approve internal AEH phases one by one. State what the Agent may do for
the task; Codex records that as an external authority envelope and keeps going
while the next action is covered. Remote and irreversible actions stay explicit.

### Local implementation only

> You may inspect, create a task-scoped branch/worktree, modify the declared
> files, and run local checks. Do not commit, push, create or update a PR,
> merge, tag, release, deploy, publish, change SCM administration, bypass a
> check, or create a Gate credential.

### Commit only

> The local diff and verification are accepted. You may create one local commit
> containing only the declared Change. Do not push or perform any remote action.

### Push and pull request

> You may push the named branch and create or update its pull request, then run
> or observe the required checks. Do not merge, bypass checks, change branch
> protection, tag, release, deploy, or publish.

### Normal merge and post-merge verification

> After all required Gates and exact-head checks pass, you may merge normally
> and verify the exact resulting main commit. No bypass, force push, SCM
> administration change, tag, release, deploy, or publication is authorized.

You can combine commit, push, PR, required checks, and normal merge in one task
authorization when that is genuinely your intent. The Agent must still stop if
scope expands or a required check fails. “Implement” alone does not imply those
remote actions.

## Credential-backed Gates

When AEH requires an HMAC-backed decision, authorize one credential for one
Change and one Gate. In short: use one Change and one Gate per credential. A
suitable instruction names:

- the Change ID and exact Gate;
- `actor=user` or the real human reviewer;
- that the credential must be new and task-specific;
- which other credentials it must be independent from;
- that it must remain outside the repository, evidence, and logs;
- every Gate where reuse is forbidden;
- deletion immediately after independent verification.

Example structure:

> Approve creation and use of a new task-specific external HMAC credential to
> sign CHG-YYYY-NNNN / SPEC_REVIEW as actor=user. It must not enter the
> repository, evidence, or logs; it must not be used for RED_GATE,
> VERIFY_MANUAL, or MERGE_GATE; delete it immediately after independent
> verification.

This instruction authorizes possession proof for that Gate only.
It does not authorize implementation, commit, push, merge, or publication.
Those actions require separate authority.

## What Codex should report at a stop

A useful handoff is short and concrete:

- Change ID, classification, branch/worktree, and exact base commit;
- current phase or Gate;
- tests executed, including whether RED was a real behavior failure;
- verification result and any warning or residual boundary;
- credentials or lease tokens deleted, without exposing their contents;
- files changed and whether a commit or remote mutation occurred;
- the exact next authorization needed.

If a check did not execute, Codex should say so. Environment failure is not a
valid RED, a local tree match is not a remote required check, and source code is
not proof that branch protection is active.

## A practical sequence

For normal work, the conversation can be as simple as:

1. State the goal and the complete authority boundary for this task.
2. Let Codex drive classification, Change commands, tests, and evidence.
3. Respond only if Codex reports a real human Gate, missing authority, failure,
   or material scope change; otherwise review the completed result.

Small bugs normally finish without intermediate questions. Critical changes
still stop at the human decisions that cannot safely be delegated.

## Boundaries to remember

AEH constrains its own workflow and process-launch semantics; it is not a
kernel sandbox. It does not provide legal identity, cross-host coordination,
automatic branch protection, or automatic publication. HMAC proves possession
of a shared secret, not who a person legally is.

For the precise model, read [About AEH](about.md),
[M5 Security Boundary](m5-security.md),
[M6.2 GitHub Assurance](m6-2-github-assurance.md), and
[M6.3 Coordination Boundary](m6-3-coordination.md).
