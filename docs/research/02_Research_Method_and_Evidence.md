# Research Method and Evidence

## 1. Why the method matters

Architecture documents can easily become rationalizations for a preferred
tool. The AEW research was designed to permit the opposite conclusion: an
existing component could be wrong, a Role could be unnecessary, Multi-Agent
could cost more than it helps, and AEH/AEW overlap could require integration
rather than expansion.

The method used a gated sequence:

```text
Questions and evidence rules
  → concept boundaries
  → snapshot-bound case studies
  → cross-case capability comparison
  → target architecture
  → current-workspace audit
  → additive migration and Pilot design
```

Final architecture was deliberately not frozen before the comparative work.

## 2. Evidence levels

The research protocol used the following ladder:

| Level | Evidence |
| --- | --- |
| L0 | inference or secondary description |
| L1 | project overview / README |
| L2 | official documentation |
| L3 | configuration, Schema or protocol |
| L4 | source code |
| L5 | tests, issues, pull requests or observed runtime evidence |

General architecture claims required at least official documentation. Material
mechanism and maturity claims sought configuration/source plus tests or
counter-evidence. Popularity and feature count were not accepted as maturity.

## 3. Concepts were separated before products were compared

Phase 1 froze distinctions that prevent accidental architecture collapse:

```text
Model ≠ Agent
Agent ≠ Workflow
Workspace ≠ folder / repository / project
Harness ≠ Runtime
Prompt ≠ Context
Memory ≠ State ≠ Evidence
Role ≠ Skill ≠ Workflow
Policy ≠ Instruction
Worktree ≠ Sandbox
Task ≠ Run ≠ Session
Trace ≠ Trajectory ≠ Evidence
Self-report ≠ Verification
```

These invariants served as coding rules for later cases. They were not a
prediction that every concept must become a separate service or directory.

## 4. Case studies looked for success and failure

The provider/Harness cases studied Codex and Qwen Code in depth. Runtime cases
covered OpenHands, SWE-ReX, E2B and Daytona. Verification cases covered
SWE-agent, SWE-bench, OpenHands review, SWE-ReX and Trae. Workflow and
multi-agent cases included LangGraph, CrewAI, OpenAI Agents SDK, AutoGen and
MetaGPT.

Each case asked:

```text
What exists?
How does it work?
Which problem does it solve?
What does it cost?
How has it failed?
What is mature, experimental or actively hardening?
Which pattern transfers without copying the product?
```

The result was intentionally not a winner. Different systems supplied evidence
for different layers.

## 5. Important corrections made by the evidence

The research changed or narrowed early assumptions:

- A Workspace is a governed work system, not a directory layout.
- Harness/Runtime separation was retained, then Runtime was further decomposed
  into contract, deployment, sandbox, lifecycle and provider capabilities.
- Scope and Ownership were not added as two more feature silos; they became
  cross-cutting requirements for all major objects.
- Provider Session was rejected as the canonical Task/Run identity.
- Peer Multi-Agent organization was removed from the kernel and treated as an
  optional escalation.
- Full trajectories were rejected as universal evidence retention; minimal
  sufficient, claim-linked evidence became the default.
- AEW and AEH were explicitly separated after duplication analysis.

## 6. Verification of verification

The verification study distinguished two questions:

1. Is the implementation correct?
2. Did a trustworthy oracle actually test the intended artifact in the intended
   environment?

This led to Oracle Integrity checks, content/config-addressed verification,
failure classification and four-state verdicts. A zero exit code, a log, a
trajectory or an Agent completion event is not automatically proof.

## 7. Cost is part of architecture truth

Governance, evidence, isolation and coordination all consume time, context,
compute and human attention. The target architecture therefore treats Cost as
a first-class cross-cutting attribute.

Pilot evaluation should compare at least:

- task and defect success;
- rework;
- context and execution cost;
- human burden;
- recovery quality;
- auditability and evidence completeness;
- verification quality;
- multi-writer conflict rate.

An elegant architecture that does not improve real work should be downgraded.

## 8. Public claim discipline

The phase packages are dated research snapshots. They support historical
design lineage, not perpetual claims about rapidly changing third-party
products. Before asserting present behavior, readers and maintainers must
return to the current authoritative repository or documentation.

This public synthesis also distinguishes:

- **implemented in AEH** — code and contracts in this repository;
- **architecture candidate** — supported by research but not implemented here;
- **Pilot protocol** — a measurement design, not proof of benefit;
- **validated outcome** — evidence from an actually completed gate.
