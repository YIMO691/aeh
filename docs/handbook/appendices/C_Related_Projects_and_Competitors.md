# 附录 C · 相关项目与竞争边界

## 1. OpenAI Codex / Harness Engineering

关注：

```text
Agent loop
repository legibility
tools
sandbox
approvals
session/runtime
```

AEH 不应与其竞争 Agent Runtime；更适合在旁边提供 Change Acceptance。  
来源：`EXT-OPENAI-HARNESS-ENGINEERING-2026`、`EXT-OPENAI-CODEX-HARNESS-2026`、`EXT-OPENAI-CODEX-CONFIG`。

## 2. Anthropic Harness / Context / Evals

贡献三条重要边界：

1. Context 是有限资源，需要工程化策展；
2. long-running harness 可分 planner / generator / evaluator；
3. Evals 要区分 Task/Trial/Trajectory/Outcome/Grader。

来源：`EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`、`EXT-ANTHROPIC-HARNESS-DESIGN-2026`、`EXT-ANTHROPIC-AGENT-EVALS-2026`。

## 3. GitHub Spec Kit

定位：Spec-driven development。  
与 AEH 重叠最大的不是 Runtime，而是：

```text
Spec
Test-first discipline
analysis / quality gates
extensions
```

Pinned repo snapshot：`13344409786a29f631c24ee49e9f307e7b588465`。  
来源：`EXT-GITHUB-SPEC-KIT`。

## 4. OpenSpec

定位：轻量变化工件、proposal/spec/design/tasks、apply/validate/archive 等。  
Pinned snapshot：`2826b8889e5223a9a8095d4428b60b56597e1020`（1.9.0 release line）。  
来源：`EXT-OPENSPEC`。

## 5. AGENTS.md

定位：给 Coding Agent 的项目级说明格式。它属于 Context/Guidance，不是独立 Enforcement。  
Pinned snapshot：`d1ac7f063d20e70015ed6732664049ae4ba9d74e`。  
来源：`EXT-AGENTS-MD`。

## 6. MCP

定位：Context/Tool Connectivity Protocol，不负责 Change Acceptance。  
来源：`EXT-MCP-SPEC-20260728`。

## 7. Gemini CLI Policy / Hooks / Sandbox

说明 Native Agent Runtime 已有：

```text
allow / deny / ask_user
hooks
sandbox
```

AEH 更适合声明/映射/验证能力，而非自研 OS Sandbox。  
Pinned repo snapshot：`24cc26ccb15522b55c4f8a63b2f894fb99b8e82a`。  
来源：`EXT-GEMINI-POLICY-ENGINE`、`EXT-GEMINI-HOOKS`、`EXT-GEMINI-SANDBOX`。

## 8. mini-SWE-agent

极简 scaffold 说明模型能力增强后，过重 Harness 假设可能失去价值。  
Pinned snapshot：`25941c89cfbc91eb40b3f8756348c91d9977d57e`。  
来源：`EXT-MINI-SWE-AGENT`。

## 9. ProofAgent

邻近方向：

```text
auditable agent evaluation
context
compliance
governance
adversarial evaluation
```

Pinned version snapshot：`ce6f821cebefa6330c9f1f3f1817713740b5f40d`（v0.12.1）。  
来源：`EXT-PROOFAGENT`、`EXT-PROOFAGENT-SNAPSHOT-0_12_1`。

## 10. Better Harness

这是目前变化最快的邻近对象之一。

2026-08-18 snapshot `a550746e...` 已合入：

```text
Harness-as-Code DSL
comparison/execution contracts
Harness UI / Studio
checkpoint-backed compare
experiment lifecycle
run evidence bridge
```

因此 Better Harness 已从“诊断 Harness”继续向 Harness Control/Evaluation Infrastructure 演进。  
AEH 不应靠 Harness UI、实验框架、Evidence 展示本身建立差异。

来源：`EXT-BETTER-HARNESS`、`EXT-BETTER-HARNESS-SNAPSHOT-20260818`。

## 11. AEH 当前候选差异

```text
Spec Kit / OpenSpec:
What should be built?

Coding Agent:
Who builds it?

Native Runtime:
What can the agent do?

ProofAgent / Better Harness:
How good / governed / observable is the agent or harness?

AEH candidate:
Can this specific Change be independently accepted?
```

这是当前研究定位，不是不可变化的市场边界。
