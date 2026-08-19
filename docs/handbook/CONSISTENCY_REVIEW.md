# AEH Handbook v0.2 · 一致性审查报告

- **审查日期**：2026-08-19
- **总体结论**：`PASS_WITH_OPEN_EVIDENCE_GAPS`
- **Source/Claim/Decision ID**：定义 147；正文引用 98；缺失 0
- **章节序列**：00–26；附录 A–G；缺失 0
- **架构 ADR**：25 项 `ACCEPTED_V0_2`；G3 treatment 已冻结；研究裁决继续动态
- **当前战略裁决**：`CONTINUE_BUT_NARROW — conditional`
- **产品有效性**：`NOT_YET_PROVEN`
- **Phase 2 / 72-run**：`authorized=false`

## 已通过

1. Phase 1 v1.5 与 Phase 1.1 v1.6 使用不同证据命名空间；
2. Phase 1.1 四个 run、External Runner verdict 和直接机器事实修改均已纳入；
3. `Generator / Acceptance Authority` 与 `Task / Assurance Outcome` 边界一致；
4. `status=VERIFY_COMPLETE` 与 `overall=MERGE_READY` 未混为同一字段；
5. 00–26、A–G、三个 Registry、单文件总稿与 SHA-256 清单完整；
6. 没有把 Phase 1.1 机制验证写成产品有效性、攻击抵抗或跨领域证明。

## 仍开放的证据缺口

- 72-run Pilot 未启动且未授权；
- A01–A08 正式攻击结果未纳入；
- Economics、Uniqueness 尚未证明；
- C#/.NET、Unity 与大型 brownfield Cross-domain Validation 未纳入；
- Codex WebSocket 稳定性仍是未来实验环境风险；
- 部分外部 GitHub 来源仍需周期性重新复核。

## 结论

本版是 **AEH Design & Evidence Baseline v0.2**。它冻结设计与证据基线，但 AEH 软件
仍为 `v0.1.0 @ 6513102`；它不是软件 `v0.2.0` 发布，也不授权 M1 或 72-run 自动启动。
