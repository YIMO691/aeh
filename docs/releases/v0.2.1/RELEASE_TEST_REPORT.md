# AEH v0.2.1 Candidate Test Report

Review date: 2026-08-26

Status: `LOCAL_ZERO_MODEL_PASS_GITHUB_PENDING`

The candidate test matrix will record only zero-model engineering checks in
this task. Model remediation runs and A01–A08 are outside the authorization.

## Local regression

- Targeted integrity and upgrade suites: 85 tests, PASS, 3 platform skips.
- Full command: `python -m unittest discover -s tests -p "test_*.py"`
- Result: 289 tests, PASS, 3 platform skips.
- Skips: Windows environment did not grant symlink creation; Linux CI retains
  coverage of the same boundaries.
- Existing test-only `ResourceWarning` messages remain non-fatal P2 debt.

## Static and documentation checks

- `python -m compileall -q src tests scripts`: PASS.
- `python docs/handbook/tools/handbook.py --check`: `HANDBOOK_CHECK_PASS`
  (27 chapters, 7 appendices).
- `git diff --check`: PASS.
- Candidate diff secret scan: 0 findings.
- Candidate diff machine-specific absolute-path scan: 0 findings.
- Pyproject/Bootstrap/Doctor/Discovery versions: consistently `0.2.1`.

## Package and clean-room checks

- PEP 517 wheel: `adaptive_engineering_harness-0.2.1-py3-none-any.whl`.
- Wheel metadata Name/Version: `adaptive-engineering-harness` / `0.2.1`.
- Fixed build epoch: `SOURCE_DATE_EPOCH=1787702400`.
- Two fixed-epoch builds: byte-identical.
- Fixed-epoch wheel SHA-256:
  `867CBCD3D8F97ECBB136A590112934D987F72B3E97F723C7A702F0DF045C9E14`.
- Clean-room lifecycle: `SMOKE_PASS`.
- Final clean-room Doctor: `READY_WITH_WARNINGS` for accepted capability and
  environment warnings.
- Repair, v0.1-shaped upgrade, and first-change smoke steps: PASS.

## Pending GitHub evidence

- Push and pull-request Windows/Linux × Python 3.10/3.11 regression jobs.
- Push and pull-request Windows/Linux clean-room wheel jobs.

No model invocation, remediation benchmark, or A01–A08 attack run was used to
produce this report.
