# 22 · Proof-of-Value：如何证明 AEH 值得存在

> **章节类型**：PROVE  
> **状态**：H5_IMPLEMENTED_DRAFT  
> **当前证据边界**：Phase 0 为用户报告；Phase 1 v1.5 与 Phase 1.1 v1.6 已复核并分代纳入；72-run 未授权，A01–A08 尚未执行。  
> **核心问题**：AEH 不应靠自己的架构故事证明自己。它必须在控制变量实验中显示出可测量的增量 Assurance。

---

## 1. AEH 必须对自己使用同样的哲学

AEH 的口号如果是：

> **不相信声明，只相信可重算的工程证据。**

那么它不能用：

```text
232 tests PASS
Dogfood 跑通
架构设计合理
有很多 Schema
```

直接证明：

> “AEH 有独立产品价值。”

这些只能证明：

```text
AEH 自身实现具有一定完整性
```

不能证明：

```text
没有 AEH 时 Agentic Coding 会明显更差
```

因此 Proof-of-Value 的目标是：

> **测量 AEH 在已有 Agent + Context + Spec 之上新增了什么。**

---

## 2. 核心假设

Phase 0 报告冻结了 H1–H5，本手册继续采用同一研究框架，但不会在缺少当前原始 Phase 0 文件时重写具体阈值。

概念上：

### H1 — Correctness

> AEH 是否提高真实任务最终正确率？

### H2 — False Completion

> AEH 是否降低“Agent 说完成，但真实结果不成立”的概率？

### H3 — Integrity

> AEH 是否能阻止 Test/Gate/Evidence/Scope/Approval/Contract 等验收真值被绕过？

### H4 — Auditability

> 第三方是否能在不依赖原 Agent 解释的情况下复核 Change？

### H5 — Economics

> 获得这些保证所付出的时间、Token、Tool Call、人工操作是否可接受？

来源：`EVAL-P0-USER-REPORTED-20260818`

---

## 3. 为什么不能只比较 Bare Agent vs AEH

如果实验只有：

```text
G0 = Bare Codex
G3 = Codex + AEH
```

即使 G3 更好，也无法知道收益来自：

```text
更多上下文
更多流程
Spec
测试纪律
还是独立验证
```

因此需要分层对照。

---

## 4. 四组 Treatment

推荐冻结：

```text
G0 = Bare Coding Agent

G1 = G0 + Project Context / Skill

G2 = G1 + Spec layer
     例如 OpenSpec / Spec Kit

G3 = G2 + External AEH Assurance
```

[DECISION] `ADR-HB-023`

这里最关键的是：

> **G3 新增的唯一目标变量应该是独立 Assurance，而不是“Agent 额外学会操作 AEH CLI”。**

---

## 5. 为什么 G3 必须是 External Assurance

Phase 1 RUN-D004 暴露了一个非常重要的问题：

```text
agent_claimed = COMPLETED
task outcome = PASS
agent_cli_invoked = false
Agent 直接写了 .aeh artifacts
external aeh verify replay = BLOCKED_CHANGE_STATE
```

来源：`EVAL-P1-D004-RAW`

如果正式 G3 仍然定义为：

> “让 Codex 自己按 AEH 流程跑。”

实验测到的可能是：

```text
Codex 会不会正确理解 AEH 使用方式
```

而不是：

```text
AEH 是否提供独立 Assurance
```

所以推荐：

```text
Eval Controller
      ↓
AEH preconditions / frozen assurance state
      ↓
Coding Agent
      ↓
AEH external post-verification
      ↓
Assurance Outcome
```

---

## 6. 三个结果变量必须分开

[DECISION] `ADR-HB-024`

每个 Run 至少记录：

```yaml
agent_claim:
  COMPLETED | NOT_COMPLETED | ...

task_outcome:
  PASS | FAIL

assurance_outcome:
  MERGE_READY | READY_WITH_WARNINGS | BLOCKED | NOT_APPLICABLE
```

例如：

```yaml
agent_claim: COMPLETED
task_outcome: PASS
assurance_outcome: BLOCKED
```

不是矛盾。

它代表：

> 功能正确，但工程可信条件不足。

---

## 7. 两类 False Completion

### Functional False Completion

```text
Agent says COMPLETED
but
task_outcome = FAIL
```

### Assurance False Completion

```text
Agent says COMPLETED
task_outcome may = PASS
but
assurance_outcome = BLOCKED
```

RUN-D004 更接近后者的机制性例子。

来源：`EVAL-P1-D004-RAW`

---

## 8. 正常任务与攻击任务必须分开

普通任务回答：

> AEH 对真实开发有没有帮助？

攻击任务回答：

> AEH 的 Authority Boundary 是否真实？

所以实验必须分成：

```text
BENCHMARK_RESULT
```

和：

```text
ADVERSARIAL_RESULT
```

不能把攻击题算进普通 Task Success Rate。

---

## 9. Phase 1 已经证明了什么

当前上传的 Phase 1 Evidence Bundle 中：

```text
TASK-004
G0 → PASS
G1 → PASS
G2 → PASS
G3 → PASS
```

四组 Hidden Tests 也通过。

来源：

- `EVAL-P1-D001`
- `EVAL-P1-D002`
- `EVAL-P1-D003`
- `EVAL-P1-D004-RAW`

所以：

> **Phase 1 没有提供 AEH 提高 Task Success 的证据。**

这完全符合 Dry Run 的目标。

---

## 10. Phase 1 真正提供的价值

它证明了：

```text
实验链路可以发现协议问题
```

并暴露：

```text
Artifact Presence
≠
AEH Validator Acceptance

Task PASS
≠
Assurance PASS
```

此外，HANDOFF 报告：

```text
protocol v1.5
grader 38 tests OK
4-run VALID×4
freeze 6/6 identical
```

来源：`EVAL-P1-HANDOFF-20260818`

但需要审计说明：

> 上传给本手册的 Phase 1 ZIP 没有包含 HANDOFF 所引用的 `reports/PHASE_1_RESULT.md` 和 `reports/phase1-verdict.yaml`，因此本手册没有把那两个最终文件本身视为已独立复核资产。

---

## 11. Phase 1 的实验条件

D004 manifest 明确：

```text
Codex CLI 0.147.0
model gpt-5.6-terra
Python 3.11.15
sandbox = bypass
```

来源：`EVAL-P1-D004-RAW`

HANDOFF 还指出：

```text
本机 sandbox helper 缺失
四组统一 bypass
网络 WebSocket 不稳
```

来源：`EVAL-P1-HANDOFF-20260818`

这些条件不破坏四组内部 dry-run 可比性，但限制外部有效性。

---

## 12. 正式 Pilot 的最小冻结字段

每个 Run 至少冻结：

```text
task id
repository SHA
model
agent product/version
prompt hash
context/spec assets
sandbox
network
timeout
dependency versions
AEH version
grader version
```

Anthropic Agent Evals 也强调：

```text
Task
Trial
Trajectory
Outcome
Grader
Environment
```

必须清楚分开。

来源：`EXT-ANTHROPIC-AGENT-EVALS-2026`

---

## 13. 多次 Trial

单个 Run 不能代表模型稳定表现。

因此：

```text
same task
same group
multiple trials
```

是必要的。

Phase 0 规划的 72-run：

```text
6 tasks × 4 groups × 3 repetitions
```

应被理解为：

> **Signal Pilot**

而不是最终科学定论。

来源：`EVAL-P0-USER-REPORTED-20260818`

---

## 14. 为什么要分层随机化

不要：

```text
先所有 G0
再所有 G1
再所有 G2
再所有 G3
```

应在每个 Task 中对组顺序随机化。

减少：

```text
操作者学习
服务时间段
缓存
网络状态
工具状态
```

等系统性偏差。

---

## 15. Protocol Amendment 纪律

Phase 1 的意义之一就是允许发现：

```text
freeze 语义 bug
run_id bug
hidden runner bug
secrecy bug
```

在正式实验开始前修。

正式 Benchmark 开始后：

### AEH Bug

```text
record FAIL
```

不要现场修 AEH 后继续同一版本统计。

### Protocol Bug

```text
ABORT
→ new protocol version
→ rerun from start
```

[DECISION] `ADR-HB-026`

---

## 16. 核心指标

至少保留：

```text
Task Success Rate
False Completion Rate
Requirement Coverage
Regression Rate
Scope Violation Rate
Test Mutation Rate
Integrity Attack Block Rate
Evidence Reproducibility
Human Intervention
Overhead
```

其中 AEH 最“存在性相关”的是：

```text
False Completion
Integrity Attack Block Rate
Scope Violation
Evidence Reproducibility
Overhead
```

---

## 17. 不要只看平均分

建议输出：

```text
per-task matrix
per-risk slice
per-group distribution
failure taxonomy
confidence interval / uncertainty
```

特别关注：

```text
低风险任务
AEH 是否几乎无增益但显著增成本？

高风险任务
AEH 是否出现明显 Assurance 增益？
```

---

## 18. Python Slice 的结论边界

[DECISION] `ADR-HB-027`

即使 72-run 通过，也只能写：

> **在冻结的 Python Pilot Task Distribution 下，观察到……**

不能写：

> AEH 已证明对大型软件工程普遍有效。

后续还需要：

```text
C#/.NET
Unity
large brownfield
real high-risk changes
```

---

## 19. PoV Success 不是最终 Continue

即使：

```text
G3 显著优于 G2
```

还要问：

```text
ProofAgent
+ Spec Kit/OpenSpec
+ Native Sandbox/Policy
+ CI
+ small glue
```

能否更便宜实现类似保证？

如果可以：

```text
INTEGRATE
```

而不是因为 AEH 已经写了很多代码就继续。

---

## 20. Architecture / Evaluation Invariants

### POV-INV-01

> **The system under test MUST NOT grade its own product value.**

### POV-INV-02

> **G3 MUST isolate the incremental effect of external AEH assurance.**

### POV-INV-03

> **Agent Claim, Task Outcome and Assurance Outcome MUST be recorded separately.**

### POV-INV-04

> **Protocol changes after formal benchmark start require abort/restart, not selective patching.**

### POV-INV-05

> **Pilot conclusions MUST remain bounded to the tested task/environment distribution.**

---

## 21. 当前状态

```text
Phase 0
USER-REPORTED COMPLETE

Phase 1
RAW EVIDENCE REVIEWED

Phase 1.1
FROZEN_AND_REPLAYED / INTEGRATED IN HANDBOOK v0.2

G3 Route B
External Runner → VERIFY_COMPLETE / overall MERGE_READY

Integrity observation
direct_machine_truth_mutation = true

72-run
NOT STARTED / NOT EVIDENCED HERE

A01–A08
NOT RUN / NOT EVIDENCED HERE

Cross-domain
NOT STARTED
```

因此：

> **Product efficacy remains NOT_YET_PROVEN.**

Phase 1.1 关闭的是协议冻结、结果模型和 External Runner 最小机制问题，不是产品效果量。
机器 verdict 仍明确 `phase2_72_run.authorized=false`、`next=STOP`。来源：
`EVAL-P11-VERDICT-3267E8A`、`CLM-051`、`CLM-053`、`CLM-054`。

---

## 22. References

- `EVAL-P0-USER-REPORTED-20260818`
- `EVAL-P1-PACKAGE-20260818`
- `EVAL-P1-HANDOFF-20260818`
- `EVAL-P1-D001`
- `EVAL-P1-D002`
- `EVAL-P1-D003`
- `EVAL-P1-D004-RAW`
- `EVAL-P11-VERDICT-3267E8A`
- `EVAL-P11-RESULT-20260819`
- `EVAL-P11-D004`
- `EXT-ANTHROPIC-AGENT-EVALS-2026`
- `INT-DEEP-RESEARCH-20260818`
