# 05 · AEH North Star 与系统边界

> **章节类型**：WHERE  
> **状态**：H2_ARCHITECTURE_SKELETON  
> **当前战略裁决**：`CONTINUE_BUT_NARROW — conditional`

---

# 1. 本章解决什么问题

AEH V0.1 最初以：

> Machine-enforced SDD + TDD harness

对外描述。

来源：`AEH-README-6513102`

这个描述在 V0.1 语境下成立，但如果把它当长期产品定位，会遇到三个问题：

1. `Harness` 已经成为覆盖 Agent Loop、Tools、Context、Sandbox、Session 等非常宽的概念；
2. `Spec` 已经有 OpenSpec / GitHub Spec Kit 等成熟生态；
3. `TDD / RED / GREEN` 本身不是独占能力，也不应该成为长期护城河。

因此当前研究需要重新回答：

> **AEH 最不能被替代的职责到底是什么？**

---

# 2. North Star

[DECISION][NORMATIVE]

> # **Generator 可以越来越自由；Acceptance Authority 必须独立。**

AEH 候选定位：

> **AEH is a vendor-neutral Change Assurance system for agentic software engineering.**

中文：

> **AEH 是一个与 Coding Agent 厂商无关的软件变更可信保证系统：它在生成 Agent 的权限之外，对某次 Change 的契约满足性、证据来源、测试 Oracle 完整性、变更范围、追溯关系和验证结果进行独立重算，并产生机器可执行的接受或阻断判定。**

来源：

- `INT-DEEP-RESEARCH-20260818`
- `ADR-HB-001`
- `ADR-HB-002`

---

# 3. 最简单的产品语言

面向普通工程师：

> **AI 负责干活，AEH 负责让过程可见、证据可查、结果可验。**

但必须避免误解成纯监控系统。

更准确：

```text
AI 到底在做什么
        ↓
Observability

为什么这样做
        ↓
Evidence / Provenance

功能对不对
        ↓
Task Verification

这次工程变更能不能信
        ↓
Change Assurance

是否允许进入下一工程状态
        ↓
Acceptance Authority
```

AEH 的核心集中在后两层。

---

# 4. AEH Core 的判断标准

任何新功能进入 AEH Core 前，应回答三个问题：

```text
Q1
即使模型能力提升十倍，
这个能力仍然需要吗？

Q2
它是否必须由“执行 Change 的 Generator 之外”
的系统拥有最终权威？

Q3
它是否对 Codex / Claude / Gemini / Kimi 等
保持 vendor-neutral 的长期价值？
```

只有大部分答案为 YES，才应优先进入 Core。

---

# 5. 当前 Candidate Core

## 5.1 Change Contract

定义：

```text
这次允许改变什么？
必须实现什么？
有哪些 Acceptance Criteria？
有哪些约束？
风险等级是什么？
```

AEH 不一定拥有 Spec Authoring，但必须知道自己在验证什么。

---

## 5.2 Evidence Provenance

回答：

```text
证据来自哪里？
基于哪个 Git SHA？
由哪个命令产生？
由谁产生？
什么时候产生？
是否可重放？
```

---

## 5.3 Evidence Freshness

Grounding 得出的事实不是永久真理。

例如：

```text
Ground:
RewardService.cs hash = H1

之后有人修改：
RewardService.cs hash = H2
```

如果后续 Spec 仍声称基于旧 Evidence：

> Evidence 已 stale。

这是 Assurance 问题，而不是 Context Retrieval 问题。

---

## 5.4 Test Oracle Integrity

核心问题：

> 实现者能否单方面改变“什么叫正确”？

如果一个 Agent 同时：

```text
写代码
写测试
改测试
判断测试
宣布完成
```

那么 GREEN 的含义依赖 Agent 自律。

AEH 的长期核心不是“喜欢 TDD”，而是：

# Oracle Ownership Separation

---

## 5.5 Scope Integrity

AEH 应独立比较：

```text
authorized scope
vs
actual diff
```

这是 Change-level Scope。

它不同于 Sandbox：

```text
Sandbox:
进程技术上能不能写某路径？

Change Scope:
即使技术上能写，
这次任务是否被授权修改？
```

---

## 5.6 Artifact Integrity

AEH 的 Validator 依赖的：

```text
core
schemas
manifest
test lock
evidence
verification
```

不能被 Generator 无痕替换。

V0.1 架构已经用 Trusted Mutation Boundary 正式表达这一点。

来源：`AEH-ARCH-6513102`

---

## 5.7 Traceability

核心链：

```text
REQ
→ AC
→ TEST
→ CODE
→ VER
```

AEH 不只是问：

> Test PASS 吗？

还要能够问：

> 这条 Requirement 到底被什么 Test 和 Verification 覆盖？

---

## 5.8 Independent Validator

这是最核心的执行实体：

```text
Generator produces candidate change
        ↓
Validator recomputes
        ↓
MERGE_READY / BLOCKED
```

Validator 不能只相信 Agent 写的：

```yaml
status: PASS
```

它必须能够根据可信输入重新判定。

---

# 6. Build / Integrate / Complement / Out of Scope

## 6.1 BUILD

当前建议自己拥有：

```text
Normalized Change Contract IR
Evidence provenance
Evidence staleness
Oracle integrity
Test lock / equivalent
Scope integrity
Artifact integrity
Traceability
External validator
Assurance verdict
CI acceptance interface
Audit bundle
```

---

## 6.2 INTEGRATE

### Spec Authoring

推荐所有者：

```text
OpenSpec
GitHub Spec Kit
PRD / Issue
```

AEH 只消费规范化 Contract。

来源：

- `EXT-OPENSPEC`
- `EXT-GITHUB-SPEC-KIT`

### Repository Context

推荐所有者：

```text
AGENTS.md
CLAUDE.md
Project Skills
Repository Intelligence
```

来源：

- `EXT-AGENTS-MD`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`

### Runtime / Sandbox / Tool Policy

推荐所有者：

```text
Codex native runtime
Claude native runtime
Gemini Policy / Hooks / Sandbox
MCP ecosystem
```

来源：

- `EXT-GEMINI-POLICY-ENGINE`
- `EXT-GEMINI-HOOKS`
- `EXT-GEMINI-SANDBOX`
- `EXT-MCP-SPEC-20260728`

---

## 6.3 COMPLEMENT

### Agent Evaluation / Governance

邻近：

```text
ProofAgent
```

它更偏：

```text
Agent behavior
adversarial evaluation
governance
CI gate
observability
```

来源：`EXT-PROOFAGENT`

### Harness Diagnosis

邻近：

```text
Better Harness
```

它更偏：

```text
how the coding workflow works
session/project evidence
finding → improvement
```

来源：`EXT-BETTER-HARNESS`

当前 AEH 候选差异：

```text
ProofAgent:
“这个 Agent / deployment 是否可靠？”

Better Harness:
“这个 Harness / workflow 哪里需要改善？”

AEH:
“这一份具体 Change 是否可以接受？”
```

这是当前研究归纳，不是对其他项目未来边界的永久断言。

---

# 7. Non-goals

[DECISION]

默认不做：

```text
Coding Model
Coding Agent
General Planner
General Agent Loop
Project RAG
General Project Memory
General Skill Framework
MCP Runtime
OS Sandbox
IDE
Full Spec Authoring Product
General Multi-Agent Orchestrator
```

原因不是“这些不重要”。

而是：

> **这些重要问题已经有更自然的责任所有者。**

---

# 8. AEH 与 SDD/TDD 的新关系

旧理解容易变成：

```text
AEH
=
SDD + TDD Workflow Product
```

建议调整为：

```text
Spec Provider
  ↓
Requirement / AC
  ↓
AEH Contract normalization
  ↓
Test / Oracle evidence
  ↓
AEH verifies integrity and closure
```

因此：

```text
SDD / TDD
= 可产生重要 Assurance Evidence 的工程方法

AEH
= 对这些 Evidence 的可信性和完整性做独立验证
```

这会显著降低 AEH 与 Spec Kit / OpenSpec 的正面重叠。

---

# 9. 为什么“不做 Harness”反而更稳定

[FACT][EXT] OpenAI 的 Codex Harness 已覆盖 Agent Loop、工具、会话等执行基础。

来源：`EXT-OPENAI-CODEX-HARNESS-2026`

[FACT][EXT] Anthropic 明确提醒 Harness 中针对当前模型弱点的假设会过期。

来源：`EXT-ANTHROPIC-MANAGED-AGENTS-2026`

因此 AEH 不应以：

```text
当前 Agent 不会 X
```

作为长期价值。

更稳定的问题是：

```text
即使 Agent 非常聪明，
最终 Acceptance 是否仍应由独立权威重算？
```

---

# 10. 什么时候 AEH 应该停止独立扩张

[DECISION]

即使 PoV 表现不错，也要经过 Uniqueness Gate：

```text
Spec Kit / OpenSpec
+
Native Sandbox / Policy
+
CI
+
ProofAgent / existing governance
+
small glue code
```

是否能够以明显更低成本提供近似相同保证？

如果 YES：

```text
INTEGRATE
```

如果 AEH 无显著 Assurance 增益：

```text
STOP / REPOSITION
```

因此本手册不以“维护 AEH 项目存在”为目标。

---

# 11. 当前战略裁决

截至 2026-08-18：

```text
CONTINUE_BUT_NARROW — conditional
```

继续：

```text
PoV
External Validator
Evidence Integrity
Oracle Integrity
Scope Integrity
Traceability
Attack Testing
```

暂停横向扩张：

```text
RAG
Memory
Web UI
Multi-Agent
Self-built Sandbox
Large Spec Authoring
```

来源：

- `INT-DEEP-RESEARCH-20260818`
- `ADR-HB-008`

---

# 12. Architecture Invariants

[NORMATIVE]

### INV-01

> **Generator MUST NOT own the final Acceptance Verdict.**

### INV-02

> **Machine Truth MUST be independently checkable and protected by a Trusted Mutation Boundary.**

### INV-03

> **Artifact Presence MUST NOT be treated as Evidence Validity.**

### INV-04

> **AEH MUST prefer integration over reimplementation outside Change Assurance.**

### INV-05

> **AEH product efficacy MUST remain HYPOTHESIS until PoV gates pass.**

---

# 13. References

- `AEH-README-6513102`
- `AEH-ARCH-6513102`
- `INT-DEEP-RESEARCH-20260818`
- `EXT-GITHUB-SPEC-KIT`
- `EXT-OPENSPEC`
- `EXT-AGENTS-MD`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`
- `EXT-ANTHROPIC-MANAGED-AGENTS-2026`
- `EXT-GEMINI-POLICY-ENGINE`
- `EXT-GEMINI-HOOKS`
- `EXT-GEMINI-SANDBOX`
- `EXT-MCP-SPEC-20260728`
- `EXT-PROOFAGENT`
- `EXT-BETTER-HARNESS`
