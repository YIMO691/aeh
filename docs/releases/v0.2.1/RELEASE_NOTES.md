# AEH v0.2.1 - Controller-owned Machine Truth

Status: **UNRELEASED CANDIDATE**

V0.2.1 is a bounded integrity patch for the RUN-F055 escape observed during
Phase 2 v1.10. It does not start M4 or change AEH's external merge/release
boundary.

## Fixes

- Seal change-scoped YAML/JSON state in a Controller checkpoint outside the
  governed repository when RED reaches LOCK_TEST.
- Reject added, removed, modified, symlinked, or Windows-reparse-point machine
  truth before GREEN, REFACTOR, VERIFY, REVIEW, and trusted approval.
- Re-check the checkpoint after every repository-controlled test process so a
  test cannot write state that the Controller later adopts and reseals.
- Fail closed for older in-flight changes that have no Controller checkpoint.

## Upgrade

V0.2.0 installations use the existing explicit, plan-first path:

```text
aeh upgrade /path/to/project --source-revision v0.2.1
aeh upgrade /path/to/project --apply --source-revision v0.2.1
```

Review the dry-run plan before applying it. Repository-controlled project data
and change evidence remain outside the upgrade write boundary.

## Honest boundaries

- The latest published release remains v0.2.0 until a separate Owner release
  decision is recorded.
- Phase 2 v1.10 recommended `REPOSITION`; this patch fixes one observed
  integrity escape but is not proof of general product effectiveness.
- No remediation model rerun or A01–A08 attack run has been performed.
- The Controller state directory still requires an OS/filesystem boundary that
  coding agents and repository-controlled subprocesses cannot write.
- AEH still stops at MERGE_READY and does not merge, push, or release changes.
