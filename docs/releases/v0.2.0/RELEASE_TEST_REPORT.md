# AEH v0.2.0 Release Test Report

Review date: 2026-08-19

## Integrated local validation

- Command: `python -m unittest discover -s tests -p "test_*.py"`
- Result: 273 tests, PASS, 1 local skip
- Duration: 537.279 seconds
- Skip: Windows denied symlink creation; both Linux CI jobs executed the
  symlink boundary test successfully.

## GitHub validation

- Repository: `YIMO691/aeh`
- Integrated candidate commit: `cc7d93fe7013b3c64982dcb3868caed1a3703ccf`
- Matrix: Ubuntu/Windows × Python 3.10/3.11
- Additional gates: clean-room wheel on Ubuntu and Windows
- Result: 6/6 PASS

## Handbook validation

- Command: `python docs/handbook/tools/handbook.py --check`
- Result: `HANDBOOK_CHECK_PASS`
- Contents: 27 chapters, 7 appendices

## Package validation

- PEP 517 wheel build: PASS
- Fixed-epoch repeatability: byte-identical
- Release wheel fixed build epoch: `SOURCE_DATE_EPOCH=1787184000`
- Release wheel SHA-256:
  `8FC11F9B42CD90FB4E4D1B64380E429D9AD19D80CACFC76396C0B46F59B3ED19`
- Dependency check: PASS
- Clean-room lifecycle: `SMOKE_PASS`
- Final Doctor: `READY_WITH_WARNINGS` for capability/environment warnings only

## Release channel

- GitHub tag/Release: `v0.2.0`
- Release asset: `adaptive_engineering_harness-0.2.0-py3-none-any.whl`
- PyPI: not published
