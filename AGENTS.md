<!-- AEH:BEGIN MANAGED -->
# AEH Managed Section (Codex)

This project uses Adaptive Engineering Harness (AEH).

Before implementation:
1. Read .aeh/profile.yaml and .aeh/effective-workflow.yaml.
2. Classify the change; follow the workflow for that classification.
3. Do not bypass required gates. Change artifacts live in .aeh/changes/CHG-*.

Effective constraints:
- git_commit: ask
- git_push: deny
- modify_source: allow
- shell: ask
- web_access: deny
- review.human_required_for: critical
- testing.tdd: risk_based
- team.code_review_policy: major
- developer.plan_before_code: risk_based

Workflow default level: STANDARD

Trusted mutation boundary - do NOT modify:
- .aeh/runtime/core/**
- .aeh/runtime/schemas/**
- .aeh/manifest.yaml
- .aeh/profile.yaml
- .aeh/effective-workflow.yaml
- Critical approvals.yaml APPROVED records
<!-- AEH:END MANAGED -->
