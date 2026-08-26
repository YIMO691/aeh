# AEH v0.2.1 Candidate Readiness Checklist

Review date: 2026-08-26

Current verdict: `LOCAL_ZERO_MODEL_READY_REVIEW_PENDING`

This checklist prepares a review candidate only. Merge, tag, GitHub Release,
wheel publication, PyPI, model reruns, and A01–A08 require separate authority.

## R0 Provenance

- [x] Base is GitHub `main` merge commit `cd449c8575b5d1bb9e353ec6cd79b2e1ca00f569`.
- [x] Integrity remediation is PR #7 head `bd01ca1f7a11ff424c81d107d9d687bc73dccb90`.
- [x] Package candidate version is `0.2.1`.

## R1 Scope

- [x] Candidate is bounded to CD-117–124 and release-state documentation.
- [x] M4 features, evaluation redesign, model reruns, and attacks are excluded.
- [x] Frozen v0.2.0 release evidence is preserved unchanged.

## R2 Regression and package

- [x] Full local zero-model regression passes: 289 tests, 3 platform skips.
- [x] Python compileall passes.
- [x] Handbook deterministic check passes: 27 chapters, 7 appendices.
- [x] Wheel builds successfully and contains version `0.2.1`.
- [x] Fixed-epoch repeat wheels are byte-identical.
- [x] Clean-room wheel lifecycle passes for the fixed-epoch wheel.
- [ ] GitHub push/PR Windows/Linux matrix passes.

## R3 Public safety

- [x] Diff contains no secrets, machine-specific absolute paths, or retained raw runs.
- [x] Public docs distinguish candidate, release, and frozen evaluation evidence.
- [x] Release claims do not overstate product effectiveness.

## R4 Independent Gates

- [ ] Review PR receives separate Owner merge authorization.
- [ ] Any tag/GitHub Release receives separate Owner release authorization.
- [ ] PyPI remains unperformed unless separately authorized.
- [ ] Model reruns and A01–A08 remain unperformed unless separately authorized.
