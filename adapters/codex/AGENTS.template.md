# AEH Managed Section (Codex)

This project uses Adaptive Engineering Harness (AEH).

Before implementation:
1. Read .aeh/profile.yaml and .aeh/effective-workflow.yaml.
2. Classify the change; follow the workflow for that classification.
3. Do not bypass required gates. Change artifacts live in .aeh/changes/CHG-*.

Effective constraints:
{{PERMISSION_SUMMARY}}

Workflow default level: {{DEFAULT_LEVEL}}

Trusted mutation boundary - do NOT modify:
{{TCB_NOTICE}}