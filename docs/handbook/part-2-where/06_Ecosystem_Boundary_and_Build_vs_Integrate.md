# 06 · 生态能力边界与 Build-vs-Integrate

> **章节类型**：WHERE  
> **核心问题**：哪些能力 AEH 应该自己做，哪些应该集成，哪些邻近项目正在逼近？

---

## 1. 不能用功能数量做竞品判断

错误：

```text
AEH 30 个功能
ProofAgent 20 个
→ AEH 更强
```

正确问题：

```text
这个能力的主要对象是谁？
谁拥有 Authority？
是否能独立 BLOCK？
证据是否可复现？
```

---

## 2. 当前生态责任分布

### Context / Repository Intelligence

代表：

```text
AGENTS.md
Project Skills
Context Engineering
Repository Legibility
```

回答：

> Agent 需要知道什么？

来源：`EXT-AGENTS-MD`、`EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`、`EXT-OPENAI-HARNESS-ENGINEERING-2026`。

### Spec

代表：

```text
OpenSpec
GitHub Spec Kit
```

回答：

> 这次要改变什么？

来源：`EXT-OPENSPEC`、`EXT-GITHUB-SPEC-KIT`。

### Agent / Harness

代表：

```text
Codex
Claude Code
Gemini
mini-SWE-agent
```

回答：

> 谁负责完成工作？

### Runtime / Policy

代表：

```text
Sandbox
Permissions
Hooks
MCP
Policy Engine
```

回答：

> Agent 技术上可以做什么？

### Evaluation / Governance Neighbors

代表：

```text
ProofAgent
Better Harness
```

回答：

> Agent/Harness 系统表现、证据、治理和对比实验如何？

---

## 3. Better Harness 需要特别重新关注

截至 2026-08-18 的 pinned snapshot：

`QoderAI/better-harness @ a550746e...`

最新 commit 已合入：

```text
Harness-as-Code DSL
comparison / execution contracts
Harness UI
Harness Studio
run evidence bridge
checkpoint-backed compare
experiment lifecycle
```

来源：`EXT-BETTER-HARNESS-SNAPSHOT-20260818`。

这意味着 Better Harness 已不只是早期“Harness Auditor”，而在向：

> **可执行 Harness、实验控制面、证据与比较基础设施**

扩展。

因此 AEH 不能把“我们有 Harness DSL / Experiment / Evidence UI”当独特方向。

AEH 更应坚守：

> **单次 Change Acceptance Authority。**

---

## 4. ProofAgent 也在快速演进

Pinned snapshot：

`ProofAgent-ai/proofagent-harness @ ce6f821c... (v0.12.1)`

它的公开定位仍集中于：

```text
auditable agent evaluation
context
compliance
governance
adversarial evaluation
```

来源：`EXT-PROOFAGENT`、`EXT-PROOFAGENT-SNAPSHOT-0_12_1`。

与 AEH 当前候选区别：

```text
ProofAgent:
Agent/System reliability & governance

AEH:
Specific Change acceptance & assurance
```

但这不是永久边界，必须定期复核。

---

## 5. BUILD

AEH 当前值得自己拥有：

```text
Normalized Change Contract IR
Evidence provenance/freshness
Oracle integrity
Scope integrity
Artifact integrity
Traceability
External validator
Assurance verdict
CI acceptance interface
Audit/replay bundle
```

---

## 6. INTEGRATE

默认集成：

```text
Spec Authoring
Repository Context
Project Skills
Agent Loop
MCP Runtime
OS Sandbox
Tool Policy
Enterprise Identity
```

---

## 7. COMPLEMENT

与 AEH 并行、可组合：

```text
ProofAgent
Better Harness
Agent Eval systems
Harness diagnosis
```

---

## 8. OUT OF SCOPE

```text
General Coding Agent
General Planner
Project RAG
General Memory
IDE
Generic Multi-Agent Orchestrator
Full Spec Authoring Product
```

---

## 9. Uniqueness Gate

即使 AEH PoV PASS，也必须构造替代组合：

```text
Agent
+ Context
+ Spec Kit/OpenSpec
+ Native Sandbox/Policy
+ CI
+ ProofAgent/Better Harness
+ small glue
```

如果它能以明显更低成本提供接近 Assurance：

```text
Verdict = INTEGRATE
```

---

## 10. Architecture Invariant

[NORMATIVE]

> **AEH SHOULD build only those capabilities whose long-term authority belongs to Change Assurance; all other mature capabilities default to integration.**

---

## 11. References

- `EXT-AGENTS-MD`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`
- `EXT-OPENAI-HARNESS-ENGINEERING-2026`
- `EXT-OPENSPEC`
- `EXT-GITHUB-SPEC-KIT`
- `EXT-PROOFAGENT`
- `EXT-PROOFAGENT-SNAPSHOT-0_12_1`
- `EXT-BETTER-HARNESS`
- `EXT-BETTER-HARNESS-SNAPSHOT-20260818`
- `INT-DEEP-RESEARCH-20260818`
