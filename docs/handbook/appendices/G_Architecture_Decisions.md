# 附录 G · 架构决策索引

> 本附录投影 `references/decision-registry.yaml`。Registry 是机器可读真值，本页是人类导航。
> 2026-08-19：架构类 ADR 已由 Owner 冻结为 v0.2；研究裁决 ADR-HB-008 与
> 产品有效性边界 ADR-HB-010 继续保持动态状态。

## ADR-HB-001 · Handbook North Star

- **Status**: `ACCEPTED_V0_2`
- **Decision**: The handbook defines AEH primarily as a vendor-neutral Change Assurance system, not as a general Agent Harness.

## ADR-HB-002 · Acceptance Authority Separation

- **Status**: `ACCEPTED_V0_2`
- **Decision**: The generating Agent MUST NOT be the final owner of machine acceptance truth.

## ADR-HB-003 · Task Outcome and Assurance Outcome

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Handbook and evaluation artifacts MUST distinguish agent_claim, task_outcome and assurance_outcome.

## ADR-HB-004 · Six-Plane Reference Architecture

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Agentic Software Engineering is described using Intent/Spec, Repository Intelligence/Context, Agent Reasoning/Harness, Execution/Tool, Verification/Governance, and Evaluation planes, with Evidence and Policy/Identity as cross-cutting substrates.


## ADR-HB-005 · Spec Provider Boundary

- **Status**: `ACCEPTED_V0_2`
- **Decision**: AEH should validate normalized requirements/acceptance constraints but should not compete as a full Spec Authoring product.

## ADR-HB-006 · Native Runtime Governance Boundary

- **Status**: `ACCEPTED_V0_2`
- **Decision**: AEH should not implement an OS sandbox as a core product capability; it should integrate with native runtime enforcement and verify declared capabilities.

## ADR-HB-007 · PoV G3 Treatment

- **Status**: `ACCEPTED_PHASE_1_1_TREATMENT`
- **Decision**: The clean experimental treatment for G3 is G2 + External AEH Assurance.

## ADR-HB-008 · Current Strategic Verdict

- **Status**: `ACTIVE_RESEARCH_VERDICT`
- **Decision**: CONTINUE_BUT_NARROW — conditional

## ADR-HB-009 · Integration Before Reimplementation

- **Status**: `ACCEPTED_V0_2`
- **Decision**: When a mature ecosystem owner exists outside Change Assurance, AEH defaults to integration rather than reimplementation.

## ADR-HB-010 · Do Not Overstate Product Efficacy

- **Status**: `ACTIVE`
- **Decision**: Until PoV decision gates pass, the handbook MUST describe AEH product efficacy as NOT_YET_PROVEN.

## ADR-HB-011 · Evidence Trust Model

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Artifact presence is only an observation; acceptance evidence requires provenance/freshness/integrity checks and, where applicable, external recomputation.

## ADR-HB-012 · Oracle Ownership Separation

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Test Lock is an implementation mechanism; the architecture invariant is that the implementation under validation cannot unilaterally redefine the acceptance oracle and retain the same assurance state.

## ADR-HB-013 · Scope Is Legality, Not Capability

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Change Scope verification remains separate from OS/runtime sandboxing. Native runtime controls capability; AEH verifies change authorization and actual diff integrity.

## ADR-HB-014 · Risk-weighted Traceability

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Traceability is a core assurance primitive, but its required depth should be risk-weighted rather than identical for every change.

## ADR-HB-015 · Context Complexity and Engineering Risk Are Orthogonal

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Context depth must not be used as a substitute for engineering risk. Risk governs assurance strength; context complexity governs how much project knowledge an agent needs.

## ADR-HB-016 · Truth Requires Trusted Mutation Boundary

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Machine truth is not defined by file format. Authoritative state requires constrained writers, integrity checks and validator-mediated transition/recomputation.

## ADR-HB-017 · Engineering Architecture Uses Responsibility-to-Code Mapping

- **Status**: `ACCEPTED_V0_2`
- **Decision**: The handbook describes stable conceptual responsibilities first and maps them to current modules second; current file layout is evidence, not the architectural definition itself.

## ADR-HB-018 · Doctor Is Observation and Admission Control, Not Repair

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Doctor remains read-only. Recovery/repair is a separate mutation capability and must not be silently embedded in health checks.

## ADR-HB-019 · Capability Honesty

- **Status**: `ACCEPTED_V0_2`
- **Decision**: AEH must represent control strength explicitly (e.g. ENFORCEABLE/GUIDANCE_ONLY/UNENFORCEABLE) and must not claim hard enforcement where only instructions exist.

## ADR-HB-020 · External CI as Stronger Acceptance Boundary

- **Status**: `ACCEPTED_V0_2`
- **Decision**: For stronger assurance, recomputation should be runnable in protected CI/SCM infrastructure outside the Generator workspace; AEH itself should stop at an acceptance verdict and not own merge/push/release.

## ADR-HB-021 · Audit Bundle Is Replay-Oriented

- **Status**: `ACCEPTED_V0_2`
- **Decision**: An audit bundle is defined by the questions it lets an independent reviewer answer and replay, not by a fixed archive format.

## ADR-HB-022 · Known Limitations Are Architecture Inputs

- **Status**: `ACCEPTED_V0_2`
- **Decision**: The handbook treats release limitations as explicit design boundaries and roadmap inputs; it must not describe planned repair/upgrade/CI/sandbox/identity features as current capabilities.

## ADR-HB-023 · PoV Measures Incremental Assurance, Not Agent Familiarity With AEH

- **Status**: `ACCEPTED_V0_2`
- **Decision**: G3 is defined conceptually as G2 + external AEH assurance; the experiment must not primarily measure whether the Coding Agent knows the AEH CLI.

## ADR-HB-024 · Task and Assurance Verdicts Are Separate Evaluation Outputs

- **Status**: `ACCEPTED_V0_2`
- **Decision**: PoV records agent_claim, task_outcome and assurance_outcome separately; functional PASS with assurance BLOCKED is a legitimate result, not a contradiction.

## ADR-HB-025 · Adversarial Results Are Reported Separately

- **Status**: `ACCEPTED_V0_2`
- **Decision**: A01-A08 results form an ADVERSARIAL_RESULT and must not be mixed into ordinary task-success metrics.

## ADR-HB-026 · Do Not Repair AEH Mid-Benchmark

- **Status**: `ACCEPTED_V0_2`
- **Decision**: After formal pilot execution begins, an AEH failure is recorded as a failure for that frozen version. Protocol defects require abort/new protocol/restart rather than hot-fixing a subset of runs.

## ADR-HB-027 · Signal Before Scale

- **Status**: `ACCEPTED_V0_2`
- **Decision**: The Python 72-run pilot is used to detect a meaningful signal before spending on cross-domain C#/.NET/Unity validation.

## ADR-HB-028 · Final Verdict Includes Uniqueness and Economics

- **Status**: `ACCEPTED_V0_2`
- **Decision**: Even a technically successful AEH must be integrated or stopped if comparable assurance can be obtained materially more cheaply from existing Spec/Policy/CI/Eval tooling.
