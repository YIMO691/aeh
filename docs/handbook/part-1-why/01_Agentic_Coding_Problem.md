# 01 · Agentic Coding 时代的问题

> **章节类型**：WHY  
> **状态**：H2_ARCHITECTURE_SKELETON  
> **核心问题**：当 AI 从“代码生成器”变成能够自主修改仓库的工程执行者后，软件工程新增了什么问题？  
> **主要证据**：`EXT-OPENAI-HARNESS-ENGINEERING-2026`、`EXT-OPENAI-CODEX-HARNESS-2026`、`EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`、`EXT-ANTHROPIC-LONG-RUNNING-HARNESS-2025`、`EXT-MINI-SWE-AGENT`

---

## 1. 本章解决什么问题

早期 AI Coding 的核心问题是：

> 模型会不会生成正确的代码？

Agentic Coding 把问题扩大了。

现代 Coding Agent 不只是返回一个代码片段。它可以读取代码库、搜索符号、形成计划、编辑多个文件、执行 Shell、调用工具、运行测试、观察失败，再继续修复。

因此软件工程的主要问题从单一的“代码生成质量”，扩展为：

```text
AI 在做什么？
为什么这么做？
它基于什么事实？
改了哪些范围？
跑了什么验证？
它说完成是真的吗？
人是否能复核全过程？
最终谁有权说“可以合并”？
```

[FACT][EXT] OpenAI 对 Codex Harness 的公开描述已经把 agent loop、thread lifecycle、工具执行和客户端集成视为 Harness 的组成部分，而不是简单文本补全。  
来源：`EXT-OPENAI-CODEX-HARNESS-2026`

[FACT][EXT] Anthropic 的长任务 Harness 研究关注的是跨 Context Window 持续执行、状态交接和结构化工件，而不是单轮代码生成。  
来源：`EXT-ANTHROPIC-LONG-RUNNING-HARNESS-2025`

这意味着：

> **软件开发对象没有变，但“执行开发的人”开始变成一个具有自主行为、工具权限和状态的系统。**

---

## 2. Coding Agent 已经解决了很多过去需要 Harness 补偿的问题

AEH 不能建立在“Agent 永远做不到某件事”的假设上。

mini-SWE-agent 的公开设计给出了一个强烈信号：随着模型能力增强，过去大量专门为模型设计的复杂工具接口和 scaffold 并不一定继续必要；项目甚至以极简 Agent Loop 作为主要设计目标。

来源：`EXT-MINI-SWE-AGENT`

Anthropic 进一步明确指出：

> Harness 会编码关于模型能力的假设，而这些假设可能随着模型进步过期。

来源：`EXT-ANTHROPIC-MANAGED-AGENTS-2026`

因此，本手册不把下面这些问题当作 AEH 的长期存在理由：

```text
“Agent 不会规划”
“Agent 不会搜索大型代码库”
“Agent 不会执行命令”
“Agent 不会自己测试”
“Agent 不会多文件修改”
“Agent 不会跨会话继续工作”
```

这些问题仍可能出现，但它们属于：

```text
Model Capability
+
Agent Harness
+
Context Engineering
```

而不是 AEH 最稳定的产品边界。

---

## 3. Repository 本身开始成为 Agent 的工作环境

[FACT][EXT] OpenAI 的 Harness Engineering 把 Repository Knowledge、Application Legibility、Agent Legibility 和架构约束提升到 Agent-first Engineering 的核心位置。

来源：`EXT-OPENAI-HARNESS-ENGINEERING-2026`

传统人类工程师进入代码库时，可以通过：

```text
README
团队口头知识
IDE 导航
经验
会议
代码评审
历史背景
```

逐步形成上下文。

Agent 依赖的是它当前可访问的：

```text
System Instructions
AGENTS.md / CLAUDE.md
Skills
Repository files
Search results
Tool outputs
History
External context
```

这就是为什么 Context Engineering 成为独立工程问题。

[FACT][EXT] Anthropic 将 Context Engineering 定义为对有限 Context 中信息的选择、维护与策展，而不仅是写一个更好的 Prompt。

来源：`EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`

因此：

> “如何让 Agent 更懂项目”是一个真实问题，但它属于 Repository Intelligence / Context Plane。

它不能自动推出：

> “AEH 应该自己做 RAG、Memory、Skills 和 Repository Index。”

---

## 4. 从“看代码”升级为“看行为”

传统静态代码审查主要关心最终 Diff：

```text
Before
→ Diff
→ After
```

Agentic Coding 增加了执行轨迹：

```text
读取什么
→ 推断什么
→ 调用什么工具
→ 修改什么
→ 测试什么
→ 失败后怎么恢复
→ 最后为什么宣布完成
```

于是产生一个新的工程对象：

# Agentic Change

它不仅包含代码结果，还包含：

```text
Intent
Context
Tool Actions
Repository Mutation
Tests
Evidence
Approvals
Final State
```

这也是 Better Harness、ProofAgent、Agent Evals 等体系开始关注 Session Evidence、Trajectory、Outcome 和 Governance 的原因。

但需要区分：

```text
Observability:
“我看到了什么发生。”

Assurance:
“这些事实足以证明该 Change 可以被接受。”
```

两者不是一回事。

---

## 5. 为什么 Observability 不足以解决 Acceptance

假设系统可以完整展示：

```text
Agent 阅读了 A.cs
Agent 修改了 B.cs
Agent 跑了 test_x
test_x PASS
Agent 输出 COMPLETED
```

这已经有较好的动态掌控能力。

但仍然没有回答：

```text
test_x 是不是正确的验收标准？
test_x 是否在实现过程中被改过？
是否还有未覆盖的 Requirement？
B.cs 是否在允许范围？
Agent 是否使用了过期源码事实？
PASS 的输出是否可复现？
机器状态是不是 Agent 自己写的？
```

所以：

> **可观察性是可信验证的必要输入，但不是充分条件。**

[DECISION] AEH 可以消费 Observability / Session Evidence，但 AEH Core 不应该退化成单纯 Session Viewer。

---

## 6. Agent Claim 不是工程事实

Anthropic 的 Agent Eval 定义提供了一个非常重要的区分：

```text
Transcript / Trajectory
≠
Outcome
```

一个 Agent 可以在文字里说：

> “任务完成了。”

但真实环境可能并没有形成正确结果。

来源：`EXT-ANTHROPIC-AGENT-EVALS-2026`

这与软件工程中的经典原则一致：

```text
声明
不能代替
可检查的系统状态
```

因此 AEH 的基本态度不是“不相信 AI”，而是：

> **任何参与生成的主体，都不能仅凭自己的声明完成验收闭环。**

---

## 7. 问题真正变成了“谁拥有工程真值”

Agentic Coding 的关键风险不是 Agent 一定会故意作弊。

风险来自所有权集中：

```text
同一个 Agent
  ├─ 理解需求
  ├─ 定义测试
  ├─ 修改实现
  ├─ 修改测试
  ├─ 写 Evidence
  ├─ 写 Gate 状态
  └─ 宣布完成
```

如果这些权力完全属于同一个执行主体，那么即使 Agent 大多数时候表现很好，工程系统依然缺少独立 Acceptance Boundary。

这就是后续章节要解决的核心问题：

> **Generator 能够越来越自主，但最终 Acceptance Authority 应该如何独立存在？**

---

## 8. AEH 从哪里切入

AEH 不负责回答：

```text
如何让 Agent 更聪明？
如何让 Agent 规划？
如何让 Agent 搜索代码？
如何实现 Agent Loop？
如何实现 MCP？
如何做完整 Spec Authoring？
```

AEH 候选核心回答：

```text
这次 Change 的目标是什么？
依据的源码事实仍然有效吗？
验收 Oracle 是否可信？
实现过程中 Test 是否被改变？
Diff 是否越授权 Scope？
REQ→AC→TEST→CODE→VER 是否闭合？
验证结果是否能独立重放？
谁产生最终 Acceptance Verdict？
```

因此当前候选定位：

> **Change Assurance**

而不是：

> General Agent Harness。

---

## 9. Architecture Invariant

[NORMATIVE]

> **任何“已完成”状态都不得仅由 Generator 的声明产生。**

进一步：

> **Final Acceptance MUST be derived from independently checkable evidence and an authoritative validation path.**

---

## 10. 当前实现状态

[AEH][FACT] AEH V0.1 已在架构契约中正式区分：

```text
Guidance
Normative Contract
Enforcement Engine
```

以及：

```text
LLM
Contract
Validator
Evidence
```

来源：

- `AEH-ARCH-6513102`
- `AEH-README-6513102`

这说明 AEH V0.1 已经不是纯 Prompt/Markdown 方法论。

但：

[HYPOTHESIS] AEH 是否因此实际显著改善真实 Agentic Coding 可靠性，尚未被正式 PoV 证明。

---

## 11. 已知限制

本章不主张：

- 所有 Agent 都会错误声称完成；
- AI Self-Verification 无效；
- 所有 Change 都需要强 Assurance；
- AEH 是唯一可能的解决方案。

真正需要后续证明的是：

> **在高风险或需要可审计接受的 Change 中，引入独立 Assurance 是否产生足够增量收益。**

---

## 12. References

- `EXT-OPENAI-HARNESS-ENGINEERING-2026`
- `EXT-OPENAI-CODEX-HARNESS-2026`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`
- `EXT-ANTHROPIC-LONG-RUNNING-HARNESS-2025`
- `EXT-ANTHROPIC-MANAGED-AGENTS-2026`
- `EXT-ANTHROPIC-AGENT-EVALS-2026`
- `EXT-MINI-SWE-AGENT`
- `AEH-ARCH-6513102`
