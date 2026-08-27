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

Production preimages and postimages are recovered from raw `base-sha` and
`head-sha` Git objects. The verifier accepts only their deterministic LF/CRLF
byte materializations, preserving GREEN evidence across ordinary line-ending
conversion without running checkout filters or modifying the target tree.

`--observed-at` is an explicit replay input used to evaluate approval expiry.
M6.1 records it but cannot prove that the caller supplied a trustworthy time.
The M6.2 GitHub adapter can derive it from authenticated run metadata and audit
required-check enforcement; deployment and live validation remain a separate
rollout boundary. See [M6.2 GitHub assurance](m6-2-github-assurance.md).

## Security boundary

The verifier may invoke read-only Git metadata commands. It never invokes commands declared by a project, changes Change state, refreshes evidence, writes below the repository root, merges, pushes, or creates a pull request. `--report` is rejected when it resolves inside the target repository.

M6.1 strengthens acceptance recomputation but is not universally unbypassable: repository administrators, ruleset bypass actors, compromised runners, or mutable workflow configuration remain outside its authority.
