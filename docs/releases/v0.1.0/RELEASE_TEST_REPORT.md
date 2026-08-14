# AEH V0.1.0 Release Test Report

automated_tests:
  command: python -m unittest discover -s tests -p "test_*.py"
  environment: Windows 10/11, Python 3.11.15, PyYAML 6.0.3, jsonschema 4.26.0
  total: 232
  passed: 232
  failed: 0
  verdict: PASS

suites:
  adapters: 16
  bootstrap: 15
  compiler: 22
  contract: 21
  discovery: 8 + 13
  doctor: 21
  interview: 10
  runtime_change: 17
  grounding: 18
  specification: 16
  red: 19
  green: 14
  verify: 22
