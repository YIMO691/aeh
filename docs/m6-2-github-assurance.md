# M6.2 GitHub Assurance Integration

> Status: **CURRENT**
> Source line: `0.3.0.dev0`
> Implementation state: M6.2a–d merged; immutable-workflow dogfood completed

M6.2 connects the provider-neutral M6.1 replay core to GitHub without confusing
three different claims:

1. `OBSERVED_WORKFLOW`: a workflow/check was seen;
2. `REQUIRED_REPOSITORY_WORKFLOW`: branch or ruleset policy requires the exact
   check from the expected GitHub App;
3. `EXTERNALLY_GOVERNED_WORKFLOW`: an independently governed organization or
   enterprise policy requires the workflow.

Only the second and third levels are enforcement claims. A green workflow by
itself is not proof that merging is blocked when the workflow is absent,
renamed, replaced, stale, or emitted by another App.

## Delivered surfaces

`aeh ci github verify-event` normalizes `pull_request` and `merge_group`
payloads, binds authenticated run/check metadata to repository, exact base/head,
workflow path/digest, check name and App, discovers exactly one newly introduced
Change, proves that every diff path is declared, then invokes M6.1 replay.

`aeh ci github render-workflow` deterministically renders a minimal-permission
workflow. It pins `actions/checkout` and `actions/setup-python` to full commit
IDs, checks out the exact event head with full history and without persisted Git
credentials, installs only an HTTPS wheel with an explicit filename and SHA-256,
and writes reports only below `RUNNER_TEMP`. It refuses to render while the
immutable artifact is unconfigured.

`aeh ci github audit` reads either an authenticated snapshot or current GitHub
REST metadata. It evaluates exact required-check/App identity, strict checks,
force-push/deletion/admin enforcement, bypass actors, workflow digest/events,
and the successful check on the latest branch head. Permission, API, or rate
limit gaps produce `INCONCLUSIVE`, not a guessed PASS.

`aeh ci github snapshot-run` captures authenticated workflow-run, check-suite,
check-run, and workflow-content identity inside GitHub Actions. Its token is an
input to the provider request only and is never included in a report.

## Exact Change and diff closure

The event adapter computes `git diff --name-only -z base..head`. PASS requires:

- exactly one changed `.aeh/changes/CHG-YYYY-NNNN/change.yaml`;
- that Change did not exist at the base revision;
- Change-local machine artifacts may change;
- production paths must appear in `green.yaml` or `refactor.yaml`;
- test paths must appear in `test-plan.yaml` / `test-lock.yaml`;
- separately governed metadata must be declared by the enforcement policy;
- no remaining diff path is accepted implicitly.

Zero, multiple, stale/reused, non-canonical, or undeclared paths fail closed.

## Approval boundary

The repository workflow receives no protected HMAC key. Strict HMAC approval
therefore still reports `TRUSTED_CREDENTIAL_CHANNEL_REQUIRED`; repository-
controlled PR code must never receive the secret.

For a solo repository, policy may explicitly select
`SCM_AUTHENTICATED_MERGE`. In that mode the GitHub adapter accepts only a
`MERGE_GATE` attestation carrying the same trust marker and delegates final
authority to GitHub's authenticated merge action. The provider-neutral replay
API remains fail-closed unless the trusted adapter supplies that exact accepted
trust mode. Reports retain the downgrade warning; manual verification never
uses this channel.

## Configuration and rollout boundary

The canonical `core/ci-enforcement-policy.yaml` currently binds the separately
authorized `m6.3b-dogfood-1` wheel and the byte-exact rendered workflow. The repository also
commits its self-hosting `.aeh` runtime snapshot so replay can validate the exact
Change without bootstrapping or mutating the checkout during the assurance job.
These source facts still do not claim active protection: only the authenticated
live audit can establish the repository-required trust level.

The AEH CLI does not modify branch protection/rulesets, merge, push, publish a
wheel, eliminate GitHub/admin authority, or provide OS runner isolation. M6.2d
uses separately authorized operator actions for rollout. Residual administrators,
bypass actors, GitHub, installed Apps, and the runner remain explicit trust
authorities.
