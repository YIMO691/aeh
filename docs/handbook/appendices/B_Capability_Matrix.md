# 附录 B · 能力矩阵

> `●` 主责/强覆盖；`◐` 部分覆盖或可集成；`○` 非主要边界；`?` 公开资料不足。矩阵是 2026-08-19 的研究快照，不是永久排名。

| Capability | AEH candidate | Spec Kit | OpenSpec | ProofAgent | Better Harness | Native Coding Agent |
|---|---:|---:|---:|---:|---:|---:|
| Spec Authoring | ○ / adapter | ● | ● | ○ | ○ | ◐ |
| Repository Context | adapter | ◐ | ○ | ◐ | ● | ● |
| Agent Loop | ○ | ◐ | ○ | ○ | ◐ | ● |
| Runtime/Sandbox | adapter | ○ | ○ | ◐ | ◐ | ● |
| Tool Policy | adapter | ○ | ○ | ◐ | ◐ | ● |
| Agent Evaluation | PoV only | ◐ | ○ | ● | ● | ◐ |
| Harness Experiment | ○ | ◐ | ○ | ◐ | ● | ◐ |
| Change Contract | ● | ● | ● | ◐ | ◐ | ◐ |
| Evidence Provenance | ● | ◐ | ◐ | ● | ● | ◐ |
| Evidence Freshness | ● intended | ◐ ecosystem | ◐ | ◐ | ●/◐ | ◐ |
| Oracle Integrity | ● | ◐ | ○ | ◐/? | ◐/? | ◐ |
| Scope Integrity | ● | ◐ | ◐ | ◐ | ◐ | ● runtime capability |
| Traceability | ● | ●/◐ | ◐ | ◐ | ◐ | ◐ |
| Approval Governance | ◐ | ◐ | ○ | ●/◐ | ◐ | ● native |
| External Change Acceptance | ● intended | ◐ | ○ | ◐ | ◐ | ◐ |
| Audit/Replay Bundle | ● intended | ◐ | ◐ | ● | ● | ◐ |

## 关键观察

1. Spec Kit / OpenSpec 已使“有 Spec、Plan、Task、TDD 流程”不再是 AEH 的独特性。
2. Native Coding Agents 已拥有越来越强的 Sandbox/Policy/Approval，不应由 AEH 重造。
3. ProofAgent 与 Better Harness 快速进入 Evaluation/Governance/Evidence/Experiment 空间。
4. AEH 值得继续证明的窄核心是：**change-scoped, independently recomputable acceptance**。
5. Phase 1.1 已验证 External Runner 的最小机制，但没有把 `● intended` 升级为产品效果证明；
   G3 中的直接机器事实修改仍需 A01–A08 检验。

来源：`EXT-GITHUB-SPEC-KIT`、`EXT-OPENSPEC`、`EXT-PROOFAGENT`、`EXT-BETTER-HARNESS-SNAPSHOT-20260818`、`INT-DEEP-RESEARCH-20260818`、`EVAL-P11-RESULT-20260819`。
