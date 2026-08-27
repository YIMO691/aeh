# M4 Manual Verification and Approval Lifecycle

M4 closes three governance gaps without turning human approval into technical
proof or strong identity.

## Manual verification gate

A `manual` entry in `test-plan.yaml` remains visibly pending until a trusted
human records the separate gate:

```text
aeh change verify CHG-2026-0001
# BLOCKED_WAITING_MANUAL

aeh change approve CHG-2026-0001 \
  --gate VERIFY_MANUAL --status APPROVED --actor reviewer \
  --ttl-seconds 3600

aeh change verify CHG-2026-0001
```

The resulting verification item uses `method=manual_runtime` and
`verdict=approved`. It is never labeled as an automated test pass. A technical
failure is evaluated first and cannot be overridden by this gate.

`VERIFY_MANUAL` and `MERGE_GATE` are intentionally separate: permission to
merge is not evidence that a manual check happened, and a manual check is not
permission to merge.

## Expiry and compatibility

`--ttl-seconds` accepts 1 through 2,678,400 seconds and is valid only with
`APPROVED`. AEH derives an absolute UTC `expires_at`; an expired record no
longer satisfies its gate.

Older approval records have no expiry. They remain schema-valid and effective
to avoid an unsafe implicit migration, but AEH emits an explicit no-expiry
warning whenever such a record is consumed.

## Revocation

Revoke an existing approval through the same trusted mutation path:

```text
aeh change approve CHG-2026-0001 \
  --gate VERIFY_MANUAL --status REVOKED --actor security-reviewer \
  --evidence-ref INC-001
```

AEH preserves the original approver and decision time, then adds the revoker,
revocation time, and optional evidence reference. A missing or non-approved
record cannot be revoked.

## CRITICAL plan gate

CRITICAL changes must declare at least one `integration` or `contract`
verification entry before TEST_DESIGN can pass. Rejection occurs before AEH
installs test files or writes `test-plan.yaml`. VERIFY repeats the check for
legacy plans and defense in depth.

## Boundary

Approval is still an honest attestation, not cryptographic identity. OIDC/IAM,
signatures, isolated command execution, and strong credential management remain
M5 concerns. AEH still stops at `MERGE_READY`.
