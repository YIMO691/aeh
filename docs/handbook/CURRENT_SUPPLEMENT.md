# Handbook v0.2 Current-State Supplement

> Status: **CURRENT SUPPLEMENT FOR A VERSION-BOUND HANDBOOK**  
> Handbook evidence cutoff: 2026-08-19  
> Current source line: `0.3.0.dev0`

The Engineering & Architecture Handbook v0.2 is intentionally bound to
`v0.1.0 @ 6513102`. It remains useful for the problem statement, architecture
principles, truth ownership, assurance model, and evidence registries. It must
not be edited into a false history of later implementation or evaluation.

## What changed after the handbook cutoff

- Phase 2 completed 72 frozen runs and produced a `REPOSITION` recommendation:
  use AEH as selective independent assurance for high-risk changes rather than
  a mandatory unattended workflow for every coding task.
- The observed machine-truth integrity escape was fixed. A bounded remediation
  rerun blocked 3/3 laundering attempts, and A01–A08 were independently
  adjudicated blocked in 8/8 attempts. This closes the observed escape without
  proving general product efficacy.
- M1 delivered relocatable wheels and cross-platform regression CI.
- M2 delivered plan-first repair, journaling, recovery, and rollback.
- M3 delivered explicit version-bound upgrade and rollback.
- SCM inspection and deterministic AEW governance export were added without
  transferring AEH truth ownership to AEW.
- M4 delivered manual verification, approval TTL/expiry/revocation, and earlier
  CRITICAL plan validation.
- M5 delivered a portable constrained-process launch policy and
  credential-bound protected approvals, with explicit limits that do not claim
  OS isolation or enterprise identity.

## What has not changed

- Generator and acceptance authority must remain separate.
- Markdown is narrative, not machine truth.
- Evidence is version-bound and must not be promoted to current fact without
  current-source verification.
- Product efficacy and uniqueness must not be overstated.
- AEH is most defensible as selective Change Assurance, not as a replacement
  for SCM, CI, identity, deployment, or workspace orchestration.

## Current navigation

- [Documentation portal](../README.md)
- [About AEH](../about.md)
- [Current status](../status.md)
- [Current architecture](../architecture-current.md)
- [Engineering guide](../engineering-guide.md)
- [M5 security boundary](../m5-security.md)
- [Research narrative](../research/README.md)
- [Roadmap](../roadmap-v0.2.md)

The original `HANDBOOK_STATUS.yaml`, `STATUS.json`, consistency review, chapter
sources, appendices, and generated single-file master remain version-bound
evidence and are not current status authorities.
