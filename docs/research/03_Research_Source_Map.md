# Research Source Map and Current Limits

## 1. Phase lineage

The public narrative is derived from the following snapshot-bound research
phases. Artifact names are included for traceability; local archive paths and
operational workspace details are intentionally omitted.

| Phase | Research focus | Public conclusions carried forward |
| --- | --- | --- |
| P0 | protocol, questions, evidence standard, gates | research must be falsifiable, snapshot-bound and evidence-graded |
| P1 | concepts and theory | Harness/Runtime, Context/Memory/State/Evidence and Role/Skill/Workflow are distinct |
| P2 | Codex case | hierarchical context, progressive Skills, trust/policy layering and durable Harness state; no universal verification contract |
| P3 | Qwen Code case | Scope, Ownership, Lifecycle and Isolation must be explicit; broad Workspace capability creates real state-system failure modes |
| P5 | runtime architecture | Runtime is contract + adapter + deployment + sandbox + lifecycle; worktree is not a sandbox |
| P6 | verification and evidence | self-report is not verification; Oracle Integrity and claim-linked evidence are required |
| P7 | workflow and multi-agent | deterministic control belongs in Workflow; delegation differs from Handoff; one writer is the default |
| P8 | cross-case matrix | 12 capability dimensions survive; six cross-cutting attributes become mandatory |
| P9 | target architecture | Run-centric, provider-neutral, contract-based AEW; AEW integrates with governance Harnesses |
| P10 | current-workspace audit | the missing core is operational Task/Run ownership and evidence indexing, not more Markdown; duplicate truth is the primary risk |
| P11 | migration and Pilot design | use additive, reversible waves; shadow before cutover; stop on duplicate truth or excess bookkeeping |

Key phase artifacts included concept models, case verdicts, executive
syntheses, capability and confidence matrices, target architecture decisions,
duplication/ownership analyses, and migration/Pilot protocols.

## 2. Relationship to public AEH documents

| Question | Public document |
| --- | --- |
| Why independent acceptance is needed | [Handbook Part 1](../handbook/part-1-why/02_From_AI_Self_Verification_to_Independent_Acceptance.md) |
| Where AEH sits in Agentic Software Engineering | [Reference Architecture](../handbook/part-2-where/04_Agentic_Software_Engineering_Reference_Architecture.md) |
| AEH's stable product boundary | [AEH North Star](../handbook/part-2-where/05_AEH_North_Star_and_System_Boundary.md) |
| How AEH assurance works | [Change Assurance Model](../handbook/part-3-how/08_Change_Assurance_Model.md) |
| Evidence and provenance rules | [Evidence and Provenance](../handbook/part-3-how/10_Evidence_and_Provenance.md) |
| Test-oracle integrity | [Test Oracle and Test Integrity](../handbook/part-3-how/11_Test_Oracle_and_Test_Integrity.md) |
| When governance cost is justified | [Cost, Friction and Risk Tiering](../handbook/part-5-prove/25_Cost_Friction_and_Risk_Tiering.md) |
| AEH/AEW integration contract | [AEW Integration](../integrations/aew.md) |

## 3. What is implemented now

AEH currently implements Change-scoped engineering assurance, including
machine-readable state and gates, Ground/Spec/Test Design/RED/GREEN/REFACTOR/
Verify flows, test locks, traceability, approvals, artifact integrity,
bootstrap/doctor/repair/upgrade surfaces and provider instruction adapters.

The AEW-facing implementation is deliberately narrow:

- bounded, local, read-only SCM boundary inspection;
- deterministic export of AEH-owned Change state and verdicts;
- external Project/Task/Run references;
- artifact paths and hashes without evidence bodies;
- explicit Scope, Ownership, Authority, Lifecycle, Provenance and Cost fields.

It does not implement the proposed AEW State Store, general Runtime, memory,
sandbox fleet, recovery daemon or peer-agent organization.

## 4. Known gaps in the research record

This source set is not a completed AEW v1.0 proof:

- the available phase packages do not include a P4 package;
- P9 is a target architecture, not evidence of a deployed full system;
- P11 completed migration tooling and synthetic checks, but its recorded live
  apply and full Pilot A/B/C remained blocked/not verified at that snapshot;
- the later read-only SCM Pilot against a large mixed-SCM workspace validates
  the bounded inspector's no-write behavior, not the entire AEW architecture;
- P12 empirical evaluation and architecture freeze are not present;
- third-party product findings are bound to their recorded snapshots and may
  have changed.

Therefore the honest current statement is:

> AEH is an implemented Change Assurance system with a tested, narrow AEW
> integration boundary. AEW is a researched target architecture whose broader
> operational kernel still requires additive implementation and comparative
> Pilot evidence.

## 5. Why the raw archives are not committed

Uploading every phase archive verbatim would add duplicated prose, unfinished
proposals, local inventory and historical operational details to a public
software repository. It would also make it unclear which statement is current.

The maintainable publication model is:

```text
raw, immutable research evidence
  → reviewed public synthesis
  → architecture decisions
  → implementation contracts and tests
  → Pilot evidence
```

If a future release needs a complete research corpus, it should be published as
a separately versioned, sanitized research artifact with its own manifest,
checksums, license, sensitivity review and snapshot metadata—not copied into
the runtime source tree ad hoc.
