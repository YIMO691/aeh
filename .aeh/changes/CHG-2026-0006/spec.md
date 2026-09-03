# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Publication uses a normal protected pull request and normal merge only.
- AC-001-01 (invariant) No SCM administration mutation, bypass, force push, tag, Release, or PyPI operation occurs.
## REQ-002 [DESIRED] Current public documentation consistently states that M1 through M6 and M6.3A/B/C are merged and complete while 0.3.0.dev0 remains unreleased and PyPI remains unpublished.
- AC-002-01 (automated) The documentation checker passes and emits roadmap=M1-M6_MERGED; README and docs/status.md contain M1–M6 and contain none of the retired M6 planned, candidate, under-final-assurance, or in-progress claims.
- AC-002-02 (invariant) Current documentation does not turn M6 completion into a tag, GitHub Release, PyPI, cross-host coordination, network-filesystem, scheduler, administrator-proof, or OS-isolation claim.
## REQ-003 [DESIRED] Documentation validation guards the new milestone truth without changing AEH runtime, schemas, core governance, GitHub workflows, tests outside the documentation contract test, or release artifacts.
- AC-003-01 (automated) The focused documentation unit test, documentation checker, diff check, and required GitHub checks pass on the exact proposed head.
- AC-003-02 (invariant) The final pull-request diff is limited to the declared current documentation, documentation checker, documentation test, and CHG-2026-0006 machine artifacts.
## REQ-004 [DESIRED] The documentation contract, navigation, GitHub assurance page, roadmap, changelog, and contributor guidance describe the exact completed implementation and current immutable verifier pin.
- AC-004-01 (automated) Local links validate, M6 is listed as MERGED in docs/status.md and documentation-contract.yaml, the M6.3 boundary is linked from docs/README.md, and the current policy pin is documented as m6.3b-dogfood-1.
- AC-004-02 (invariant) docs/releases, docs/archive, and the version-bound handbook remain unchanged.
