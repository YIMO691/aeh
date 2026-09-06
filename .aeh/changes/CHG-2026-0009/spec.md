# Spec

machine truth in spec.yaml

## REQ-001 [CONSTRAINT] Work stays within the approved documentation branch, checks, normal PR merge, and post-merge verification boundary.
- AC-001-01 (invariant) No SCM administration change, bypass, force push, tag, Release, PyPI publication, or Gate credential creation occurs.
## REQ-002 [CURRENT] PR #24 is merged into main as d167b3ad899159cec809ef1819671b03b3838ffc and exact-main regression run 34044290320 passed all six jobs.
- AC-002-01 (automated) Current status and documentation contract record PR #24, merge d167b3ad899159cec809ef1819671b03b3838ffc, and run 34044290320.
- AC-002-02 (invariant) Historical milestone and documentation evidence remains attributable and is not rewritten as current implementation evidence.
## REQ-003 [DESIRED] Current architecture explains the advisory Agent decision layer and its bounded relationship to AEH enforcement.
- AC-003-01 (automated) docs/architecture-current.md identifies scoped-fact classification and the CONTINUE, WAITING_FOR_AUTHORITY, BLOCKED, and COMPLETE outcomes.
- AC-003-02 (invariant) Documentation does not claim that the Agent decision layer transitions Changes, creates approvals, broadens authority, or replaces AEH validators.
## REQ-004 [DESIRED] Current status and changelog identify the Agent-driven flow as delivered after M6.3 and preserve exact production evidence.
- AC-004-01 (automated) docs/status.md and CHANGELOG.md record PR #24, merge d167b3ad899159cec809ef1819671b03b3838ffc, run 34044290320, and the 418/414/4 baseline.
- AC-004-02 (invariant) Agent-driven flow is described as a post-roadmap usability layer, not a new release or an automatic SCM publisher.
## REQ-005 [DESIRED] Documentation regression prevents the Agent-driven status, architecture, and validation facts from drifting.
- AC-005-01 (automated) tests.documentation.test_documentation fails before the documentation alignment and passes afterward without increasing the discovered test count.
- AC-005-02 (invariant) The final implementation diff is limited to the declared documentation, documentation regression, and CHG-2026-0009 artifacts.
## REQ-006 [DESIRED] Public landing pages report the merged Agent-driven flow and the exact 418-test baseline without changing installation or release boundaries.
- AC-006-01 (automated) README.md and README.zh-CN.md describe the merged Agent-driven flow and report 418 discovered, 414 passed, and 4 expected skips.
- AC-006-02 (invariant) The source remains 0.3.0.dev0, latest public release remains v0.2.0, and PyPI remains unpublished.
