# Using AEH with Codex

> Status: **CURRENT**
> Source line: `0.3.0.dev0`

This guide shows how to use AEH from a Codex conversation without memorizing
the full CLI. It focuses on practical prompts and authority boundaries; the
[engineering guide](engineering-guide.md) remains the detailed CLI reference.

## The short version

In an AEH-enabled repository, ask Codex to read the repository instructions,
classify the change, and follow the effective workflow:

> Use AEH for this task. Read AGENTS.md, .aeh/profile.yaml, and
> .aeh/effective-workflow.yaml first. Choose the lightest safe workflow, keep
> evidence under the Change, implement and verify locally, and stop before any
> action that needs authority I have not explicitly granted.

Codex should tell you the classification, current Gate, evidence-backed result,
and next action. It should not silently treat an earlier approval as permission
for a later stage.

## Pick a prompt by task size

### Tiny, reversible edit (`DIRECT`)

> Correct the typo in the command description. Use AEH, confirm this is truly
> low risk and reversible, make the local edit, and run the smallest relevant
> check. Do not commit or publish.

`DIRECT` is for a genuinely small change whose failure is easy to detect and
undo. If grounding reveals broader behavior or contract impact, Codex should
escalate rather than force the task to remain DIRECT.

### Focused bug (`LIGHTWEIGHT`)

> Fix the empty-state message shown after the final item is deleted. Use the
> AEH LIGHTWEIGHT bug path if the evidence supports it. Add one focused
> regression test, demonstrate the failure before the fix, implement the fix,
> and verify locally. Stop before commit.

This is the normal choice for a small bug: a bounded bug contract and a real
RED/GREEN result, without the full feature process.

### Feature or cross-file change (`STANDARD`)

> Add CSV export to the report screen using AEH. Ground the affected behavior,
> compile a specification and test plan, show the intended RED, implement the
> feature, and complete local verification and review. Do not push or open a PR
> without separate approval.

Use STANDARD when the change adds behavior, crosses components, or needs an
explicit specification and traceability.

### Sensitive change (`CRITICAL`)

> Change the payment permission rules using AEH and classify it as CRITICAL.
> Preserve raw evidence, use independent human Gates, and stop before each Gate
> that requires my decision. Never create or reuse a credential unless I
> authorize that exact Change and Gate.

CRITICAL is appropriate for security, money, identity, permissions, migration,
release, infrastructure, compliance, and high-impact autonomous work. It adds
human decision points; it does not allow an agent to manufacture approval.

### Exploration (`EXPLORE`)

> Explore whether incremental parsing would improve this command. Keep the work
> disposable, record the hypothesis and evidence, and do not promote it into a
> production Change unless I approve the scope.

EXPLORE lets uncertain work end in discard or promotion. It is not a shortcut
around production Gates.

## Authorize one stage at a time

An effective Codex instruction states both what is allowed and where to stop.

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

These examples are intentionally separate. “Implement”, “continue”, or “the
tests pass” should not be interpreted as all later permissions.

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

1. “Inspect this task and propose the AEH level. Do not modify files yet.”
2. “Implement locally and verify. Stop before commit.”
3. Review the diff and evidence.
4. “Create the local commit only.”
5. “Push this branch, open the PR, and run required checks. Do not merge.”
6. Review provider-bound checks and any required human Gate.
7. “Merge normally and verify the exact main commit.”

Small bugs may complete locally at step 2 with LIGHTWEIGHT evidence. Critical
changes add explicit Gate approvals between these stages.

## Boundaries to remember

AEH constrains its own workflow and process-launch semantics; it is not a
kernel sandbox. It does not provide legal identity, cross-host coordination,
automatic branch protection, or automatic publication. HMAC proves possession
of a shared secret, not who a person legally is.

For the precise model, read [About AEH](about.md),
[M5 Security Boundary](m5-security.md),
[M6.2 GitHub Assurance](m6-2-github-assurance.md), and
[M6.3 Coordination Boundary](m6-3-coordination.md).
