# 04 · Agentic Software Engineering 参考架构

> **章节类型**：WHERE  
> **状态**：H2_ARCHITECTURE_SKELETON  
> **目标**：把 Context、Spec、Agent、Runtime、Assurance、Evaluation 放到正确责任边界，防止 AEH 变成“大而全 Harness”。

---

## 1. 为什么不能再画成一条简单流水线

一个常见模型是：

```text
User
 ↓
Spec
 ↓
Coding Agent
 ↓
Tests
 ↓
Merge
```

这个模型对解释单次执行流程有帮助，但不适合定义系统责任。

原因是：

- Context 会在 Agent 推理全过程持续输入；
- Sandbox/Policy 会在每次 Tool Call 上生效；
- Verification 可以在 RED、GREEN、VERIFY 等多个点阻止迁移；
- Evaluation 测的是整个 Agent/Harness 的长期表现，不是某一个 Change；
- Evidence 横跨所有阶段。

因此本手册采用：

# 六平面 + 两条横切底座

---

## 2. 六平面

```text
┌─────────────────────────────────────────────────────────────┐
│                    Intent / Spec Plane                      │
│ User · PRD · Issue · OpenSpec · Spec Kit                    │
│                  “究竟要改变什么？”                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│             Repository Intelligence / Context Plane         │
│ AGENTS.md · CLAUDE.md · Skills · References · Architecture  │
│ Repository Index · Domain Knowledge · Project Context       │
│                  “Agent 必须知道什么？”                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                Agent Reasoning / Harness Plane              │
│ Codex · Claude Code · Gemini · Kimi · SWE/mini-SWE          │
│ Plan · Search · Reason · Generate · Recover                 │
│                    “谁负责把活干完？”                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 Execution / Tool Plane                      │
│ Shell · Filesystem · MCP · Browser · Unity-MCP              │
│ Sandbox · Policy · Hooks · Permissions                      │
│                     “Agent 能做什么？”                       │
└─────────────────────────────────────────────────────────────┘

╔═════════════════════════════════════════════════════════════╗
║              Verification / Governance Plane               ║
║                 AEH candidate boundary                    ║
║ Evidence · Scope · Oracle Integrity · Traceability          ║
║ Artifact Integrity · Approval · Acceptance Gate             ║
║                    “凭什么接受这次变更？”                    ║
╚═════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│                    Evaluation Plane                         │
│ Evals · PoV · Benchmarks · Regression · Adversarial Tests   │
│                 “整个系统真的变好了吗？”                     │
└─────────────────────────────────────────────────────────────┘
```

[DECISION] 这六个 Plane 是责任域，不是严格的 1→2→3→4→5→6 串行步骤。

---

# 3. Plane 1 — Intent / Spec

## 3.1 它负责什么

回答：

> **我们到底要改变什么？**

典型输入：

```text
User Intent
PRD
Issue
Bug report
OpenSpec
GitHub Spec Kit
Architecture Decision
```

典型输出：

```text
Requirement
Acceptance Criteria
Constraints
Design assumptions
Tasks
```

[FACT][EXT] GitHub Spec Kit 以 Spec → Plan → Tasks → Implement 为核心 SDD 路线，并把 Intent 作为主要组织对象。  
来源：`EXT-GITHUB-SPEC-KIT`

[FACT][EXT] OpenSpec 提供 proposal/specs/design/tasks 等工件，并允许更灵活地组合依赖。  
来源：`EXT-OPENSPEC`

## 3.2 对 AEH 的影响

AEH 不应该重新竞争：

```text
完整 PRD 编辑器
Spec brainstorming UX
完整 planning product
```

AEH 只需要能够消费一个规范化表示，例如：

```text
REQ
AC
Constraint
Risk hint
```

然后回答：

> 这些 Requirements 是否被后续 Test、Code、Verification 实际闭合？

因此：

```text
Spec Authoring = Integration
Spec Assurance = AEH candidate Core
```

---

# 4. Plane 2 — Repository Intelligence / Context

## 4.1 它负责什么

回答：

> **Agent 为了完成任务，必须知道什么？**

典型资产：

```text
AGENTS.md
CLAUDE.md
Skills
Project references
Architecture docs
Repository index
Domain knowledge
Code search
RAG / memory
```

[FACT][EXT] AGENTS.md 的公开定位就是“README for agents”，提供可预测的项目上下文和指令位置。  
来源：`EXT-AGENTS-MD`

[FACT][EXT] Anthropic 将 Context Engineering 视为有限 Context 中信息的策展问题。  
来源：`EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`

## 4.2 与 AEH 的区别

Context Plane 问：

> Agent 知不知道？

AEH 问：

> Agent 的结论依据能不能被证明仍然成立？

例如：

```text
Context:
“奖励领取逻辑在 RewardService.cs。”

Assurance:
“这个结论来自 commit X / hash Y；
在进入实现前是否已经 stale？”
```

因此：

```text
Knowledge delivery
≠
Evidence provenance
```

---

# 5. Plane 3 — Agent Reasoning / Harness

## 5.1 它负责什么

回答：

> **谁负责把事情做完？**

能力：

```text
Plan
Search
Reason
Edit
Recover
Use tools
Iterate
```

Codex、Claude Code、Gemini、Kimi、mini-SWE-agent 等都属于这一平面。

[FACT][EXT] Codex Harness 公开包含 Agent Loop 和工具执行能力。  
来源：`EXT-OPENAI-CODEX-HARNESS-2026`

[FACT][EXT] mini-SWE-agent 明确将 model / agent / environment / run 分离，并追求极简控制流。  
来源：`EXT-MINI-SWE-AGENT`

## 5.2 AEH 为什么不应该成为 Agent Loop

如果 AEH 自己承担：

```text
planner
executor
tool loop
memory
multi-agent scheduler
```

它就会与 Coding Agent 平台直接竞争，并把大量模型时代性的假设固化进自己的架构。

[FACT][EXT] Anthropic 已经指出 Harness 假设会随着模型能力变化而过期。  
来源：`EXT-ANTHROPIC-MANAGED-AGENTS-2026`

因此 AEH 应尽量保持：

> **Model-independent / Harness-adjacent**

---

# 6. Plane 4 — Execution / Tool

## 6.1 它负责什么

回答：

> **Agent 实际能做什么？**

典型能力：

```text
Shell
Filesystem
Browser
MCP
Network
Sandbox
Tool Policy
Hooks
Permissions
```

[FACT][EXT] MCP 2026-07-28 定义 Host/Client/Server，以及 Resources、Prompts、Tools 等协议能力。  
来源：`EXT-MCP-SPEC-20260728`

[FACT][EXT] Gemini CLI Policy Engine 能对 Tool Call 做 allow / deny / ask_user，并允许 Hooks 在 Agent Loop 中同步拦截。  
来源：`EXT-GEMINI-POLICY-ENGINE`、`EXT-GEMINI-HOOKS`

[FACT][EXT] Gemini CLI Sandbox 负责隔离 Shell/File 修改等执行。  
来源：`EXT-GEMINI-SANDBOX`

## 6.2 AEH 的策略

AEH 可以声明：

```yaml
git_push: deny
destructive_shell: ask
production_network: deny
```

但真正的执行控制应优先映射到 Native Enforcement Surface。

AEH 的职责更接近：

```text
Policy intent
→ adapter/capability mapping
→ native enforcement
→ AEH verifies whether the declared control is actually available
```

而不是自研 OS Sandbox。

---

# 7. Plane 5 — Verification / Governance

这是 AEH 的候选核心边界。

它回答：

> **凭什么接受这一次具体软件变更？**

候选能力：

```text
Change Contract
Evidence provenance
Freshness / staleness
Test Oracle Integrity
Test Lock / Oracle Freeze
Scope Integrity
Artifact Integrity
Traceability
Approval provenance
External Validator
Acceptance Verdict
```

这一层最大的特征不是“测试多”。

而是：

> **Acceptance Authority 与 Generator 分离。**

---

# 8. Plane 6 — Evaluation

Evaluation 回答：

> **整套 Agent + Harness + Policy + AEH 是否真的越来越好？**

Anthropic 的定义包括：

```text
Task
Trial
Trajectory
Outcome
Graders
Evaluation Harness
```

来源：`EXT-ANTHROPIC-AGENT-EVALS-2026`

AEH PoV 属于这一层：

```text
G0
G1
G2
G3
72-run
A01–A08
Cross-domain
```

需要强调：

```text
AEH = Change-level Assurance candidate

aeh-evals = Evaluation Plane
```

AEH 不能自己用“我的 Validator PASS”证明“AEH 产品有价值”。

---

# 9. 两条横切底座

## 9.1 Evidence Substrate

```text
Git SHA
Diff
Hash
Test logs
Command result
Artifact
Timestamp
Environment fingerprint
Provenance
```

所有 Plane 都可能产生 Evidence。

AEH 的职责不是拥有所有日志，而是判断：

```text
哪些 Evidence 可作为 Acceptance 输入？
Evidence 是否新鲜？
Evidence 是否被可信路径产生？
能否重放？
```

---

## 9.2 Policy / Identity Substrate

```text
User identity
Repository permissions
CI identity
Approval authority
Credential boundary
Policy revision
Release authority
```

AEH V0.1 当前的 human approval 仍是 attestation，不是强身份系统。

来源：`AEH-README-6513102`

因此企业 Identity/IAM 更合理的长期策略是：

> Integration。

---

# 10. Context Complexity 与 Engineering Risk 必须正交

一个任务可能：

```text
Context Complexity = HIGH
Risk = LOW
```

例如：

> 大型渲染模块的无行为重构。

也可能：

```text
Context Complexity = MEDIUM
Risk = CRITICAL
```

例如：

> 一处只有十几行的重复扣费逻辑。

所以：

```text
Context Plane
决定“Agent 需要知道多少”

Assurance Plane
决定“需要多强的独立验证”
```

不得用一个 L1–L4 同时表达两者。

---

# 11. Reference Architecture 中 AEH 的最终位置

```text
                 HUMAN / INTENT
                       │
                       ▼
              SPECIFICATION PLANE
          PRD / Issue / OpenSpec / Spec Kit
                       │
                       ▼
             REPOSITORY INTELLIGENCE
          Skills / AGENTS / Docs / Context
                       │
                       ▼
               CODING GENERATOR
          Codex / Claude / Gemini / Kimi
                       │
                       ▼
               EXECUTION RUNTIME
          Shell / MCP / Sandbox / Hooks
                       │
                       │
        ───────── Evidence ─────────
                       │
                       ▼
        ╔═══════════════════════════╗
        ║            AEH            ║
        ║     CHANGE ASSURANCE      ║
        ║ Contract · Provenance     ║
        ║ Oracle · Scope · Trace    ║
        ║ Integrity · Verification  ║
        ╚═════════════╤═════════════╝
                      │
             independent recompute
                      │
               ┌──────┴──────┐
               ▼             ▼
          MERGE_READY       BLOCKED
```

---

# 12. Architecture Invariant

[NORMATIVE]

> **AEH MUST NOT become the owner of capabilities whose primary responsibility belongs to another Plane unless independent Change Assurance requires a minimal integration surface.**

换句话说：

> **AEH 不是六层平台；AEH 只需要理解六层。**

---

# 13. 当前实现状态与限制

[AEH][FACT] AEH V0.1 的冻结架构已经明确：

```text
Core
Bootstrap
Project Profile
Adapter
Runtime
```

同时区分：

```text
Guidance
Normative Contract
Enforcement Engine
```

来源：`AEH-ARCH-6513102`

但本章的“六平面”是对整个 Agentic Engineering 生态的参考架构，不等于 AEH V0.1 的内部五层目录架构。

二者必须保持区别：

```text
六平面
= 生态责任架构

AEH 五层
= AEH 内部架构
```

---

# 14. References

- `EXT-OPENAI-HARNESS-ENGINEERING-2026`
- `EXT-OPENAI-CODEX-HARNESS-2026`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`
- `EXT-ANTHROPIC-MANAGED-AGENTS-2026`
- `EXT-ANTHROPIC-AGENT-EVALS-2026`
- `EXT-GITHUB-SPEC-KIT`
- `EXT-OPENSPEC`
- `EXT-AGENTS-MD`
- `EXT-MCP-SPEC-20260728`
- `EXT-GEMINI-POLICY-ENGINE`
- `EXT-GEMINI-HOOKS`
- `EXT-GEMINI-SANDBOX`
- `AEH-ARCH-6513102`
