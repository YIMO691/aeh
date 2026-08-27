# M6.1 — Read-only CI replay

> Status: **CURRENT**  
> Source line: `0.3.0.dev0`

M6.1 adds a provider-neutral acceptance verifier. It re-evaluates committed AEH machine evidence in an exact Git checkout; it does not run project commands and does not trust `verification.yaml` by itself.

## Command contract

```text
aeh ci verify CHANGE_ID \
  --workdir REPOSITORY \
  --repository-id SCM_HOST/OWNER/REPOSITORY \
  --base-sha 40_HEX_SHA \
  --head-sha 40_HEX_SHA \
  --observed-at RFC3339 \
  [--approval-key KEY_ID=PATH] \
  [--report PATH_OUTSIDE_REPOSITORY]
```

The command validates `repository-id` against the checkout's `remote.origin.url`, the clean checkout and exact base/head relation, the installed runtime manifest and policy, Change artifacts and schemas, test/protected-file locks, evidence hashes, grounding freshness, traceability, verification outcomes, and effective approvals. The deterministic JSON report binds all consumed file hashes and contains a canonical SHA-256 digest. Exit code `0` means `PASS`; all other verdicts fail closed.

`--observed-at` is an explicit replay input used to evaluate approval expiry. M6.1 records it but cannot prove that the caller supplied a trustworthy time. Protected CI configuration and SCM required-check enforcement are M6.2 concerns.

## Security boundary

The verifier may invoke read-only Git metadata commands. It never invokes commands declared by a project, changes Change state, refreshes evidence, writes below the repository root, merges, pushes, or creates a pull request. `--report` is rejected when it resolves inside the target repository.

M6.1 strengthens acceptance recomputation but is not universally unbypassable: repository administrators, ruleset bypass actors, compromised runners, or mutable workflow configuration remain outside its authority.
