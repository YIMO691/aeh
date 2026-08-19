# AEH Engineering & Architecture Handbook v0.2

> **中文名**：《AEH 工程与架构手册》  
> **研究截点**：2026-08-19  
> **AEH 源码基线**：`YIMO691/aeh @ 6513102`  
> **AEH 软件版本**：`v0.1.0`（本手册 v0.2 不是软件 v0.2.0）  
> **证据基线**：Phase 1.1 / protocol v1.6  
> **战略状态**：`CONTINUE_BUT_NARROW — conditional`  
> **产品有效性**：`NOT_YET_PROVEN`

## 核心定义

> **AEH 是一个 vendor-neutral Change Assurance system：它在生成 Agent 的权限之外，对某次软件 Change 的 Contract、Evidence、Oracle、Scope、Traceability 与 Verification 进行独立检查/重算，并产生接受或阻断判定。**

普通工程师版：

> **AI 负责干活，AEH 负责让过程可见、证据可查、结果可验。**

最高架构原则：

> **Generator 可以越来越自由；Acceptance Authority 必须独立。**

## 五部结构

1. **WHY** — Agentic Coding 的可信性问题；
2. **WHERE** — AEH 在工程生态中的位置；
3. **HOW** — Evidence、Oracle、Scope、Traceability、Risk 与 Truth Ownership；
4. **BUILD** — Bootstrap、Doctor、Adapter、CI、Audit、Recovery；
5. **PROVE** — PoV、Adversarial Assurance、案例、Friction 和战略裁决。

## 当前诚实边界

```text
Problem Need: HIGH CONFIDENCE
AEH Mechanism: SUBSTANTIAL
Phase 1.1 Protocol/Mechanism: VALIDATED
AEH Product Efficacy: NOT YET PROVEN
AEH Uniqueness: NOT YET PROVEN
Current Verdict: CONTINUE_BUT_NARROW — conditional
Phase 2 / 72-run: NOT AUTHORIZED
```

Phase 1.1 已完成冻结协议与 External Runner 最小机制验证，但未改变产品有效性边界。
正式是否长期继续，仍要等待：

```text
72-run
→ A01–A08
→ Economics
→ Uniqueness
→ C#/.NET
→ Unity / brownfield
```

## 入口

- `AEH_Engineering_Architecture_Handbook_v0.2.md`：由分章确定性生成的单文件总稿；
- `part-*`：分章权威编辑源；
- `appendices/`：术语、矩阵、竞品、攻击、错误码、引用、ADR；
- `references/`：机器可读 Source / Claim / Decision Registry；
- `CONSISTENCY_REVIEW.*`：成书一致性审查；
- `FILE_MANIFEST.sha256`：文件完整性清单；
- `tools/handbook.py`：总稿生成与一致性/完整性检查。
