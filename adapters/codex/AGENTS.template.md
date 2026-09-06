# AEH Managed Section (Codex)

This project uses Adaptive Engineering Harness (AEH).

Drive the workflow for the user:
1. Read .aeh/profile.yaml and .aeh/effective-workflow.yaml.
2. Infer the lightest safe workflow from the actual scope, reversibility, side effects, and uncertainty.
3. Keep a task-scoped authority envelope outside the repository and use `aeh change continue`
   internally to distinguish routine work from a real decision boundary.
4. Continue within the active authority; stop only for missing authority, a human Gate, a failed
   check, or material scope expansion.

Do not ask the user to choose a workflow level or repeat approval for work already covered by the
authority envelope. Never invent permission or a Gate credential. Change artifacts remain in
.aeh/changes/CHG-* and required Gates must not be bypassed.

Effective constraints:
{{PERMISSION_SUMMARY}}

Workflow default level: {{DEFAULT_LEVEL}}

Trusted mutation boundary - do NOT modify:
{{TCB_NOTICE}}
