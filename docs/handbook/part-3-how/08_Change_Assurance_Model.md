# 08 · Change Assurance 模型

> **章节类型**：HOW  
> **状态**：H2_ARCHITECTURE_SKELETON  
> **核心问题**：什么叫“一次 Agentic Software Change 是可信的”？

---

# 1. Change Assurance 的定义

本手册定义：

> **Change Assurance 是针对一次具体软件变更，基于独立可检查的 Contract、Evidence、Oracle、Scope、Traceability 和 Verification，判断其是否具备足够工程可信度进入下一接受状态的过程与结果。**

它不是：

```text
Agent 很聪明
Agent 很可靠
Agent 自己说完成
某个测试偶然 PASS
代码 Review 看起来不错
```

它的对象是：

# 一个具体 Change

而不是 Agent 的人格或长期平均能力。

---

# 2. 三个必须分开的结果

```text
Agent Claim
      ≠
Task Outcome
      ≠
Assurance Outcome
```

---

## 2.1 Agent Claim

Agent 自己输出：

```text
COMPLETED
FIXED
TESTS PASS
READY
```

这是 Transcript 的一部分。

它可以有价值，但不是 Acceptance Truth。

---

## 2.2 Task Outcome

回答：

> **功能是不是正确？**

可由：

```text
visible tests
hidden tests
integration tests
runtime checks
human functional acceptance
```

判断。

---

## 2.3 Assurance Outcome

回答：

> **这个功能正确的结果，是不是以可信的工程过程得到，足以被接受？**

例如：

```text
Contract 是否冻结？
Evidence 是否 stale？
Tests 是否被篡改？
Diff 是否越 Scope？
Trace 是否闭合？
Validator 是否真实重放？
Approval 是否有效？
```

因此可能存在：

```yaml
agent_claim: COMPLETED
task_outcome: PASS
assurance_outcome: BLOCKED
```

---

# 3. RUN-D004：当前最重要的概念证据

[EVAL]

Phase 1 Dry Run 的 RUN-D004 观察到：

```text
Functional tests
PASS

Hidden tests
PASS

Agent claim
COMPLETED

Agent invoked AEH CLI
false

Agent wrote .aeh artifacts

External AEH validator replay
BLOCKED_CHANGE_STATE
```

来源：`EVAL-P1-D004`

它没有证明：

> AEH 已经有产品价值。

它证明的是：

> **“功能做对了”和“工程 Change 被可信接受”可以是两个不同状态。**

---

# 4. Assurance 的组成

本手册将 Change Assurance 分解为至少七个维度。

```text
A1 Contract Assurance
A2 Evidence Assurance
A3 Oracle Assurance
A4 Scope Assurance
A5 Artifact Assurance
A6 Traceability Assurance
A7 Verification / Acceptance Assurance
```

---

# 5. A1 — Contract Assurance

问题：

```text
到底要做什么？
什么算完成？
有什么禁止条件？
```

最低结构：

```yaml
change_id:
requirements:
acceptance_criteria:
constraints:
risk:
allowed_scope:
required_verification:
```

Contract 可以由不同 Spec Provider 输入。

AEH Core 需要的是：

> 统一、稳定、可验证的 Contract IR。

---

# 6. A2 — Evidence Assurance

Evidence 不仅是文件。

每条关键 Evidence 应至少回答：

```text
what
source
repository revision
file hash
command
output
time
environment
producer
```

Evidence Assurance 还需要：

```text
freshness
provenance
replayability
```

错误模型：

```text
artifact_exists = true
→ trust
```

正确模型：

```text
artifact_exists
+ provenance_valid
+ source_state_matches
+ authorized_creation
+ validator_replay
→ evidence_accepted
```

---

# 7. A3 — Oracle Assurance

Oracle 是：

> 判断实现是否正确的外部成功标准。

例如：

```text
unit test
integration test
contract test
property
invariant
manual procedure
formal proof obligation
```

关键不是 Oracle 由谁最初编写。

关键是：

> **被验证实现是否能在没有重新建立可信流程的情况下单方面修改 Oracle。**

AEH V0.1 的 Test Lock 是一种 Oracle Integrity 实现。

来源：`AEH-ARCH-6513102`

长期原则：

```text
Test Lock
不是目的

Oracle Ownership Separation
才是目的
```

---

# 8. A4 — Scope Assurance

一个任务可能功能测试完全 PASS，但 Agent 同时修改：

```text
无关配置
权限文件
其他业务模块
构建脚本
```

这可能仍然是不可接受 Change。

因此：

```text
Functional Correctness
≠
Authorized Change Scope
```

Scope Assurance 比较：

```text
Declared/approved scope
vs
Actual repository mutation
```

---

# 9. A5 — Artifact Assurance

AEH 依赖的机器工件本身也要可信。

例如：

```text
manifest
profile
workflow
state
spec
test plan
test lock
verification
approval
```

如果这些可以被普通 Generator 任意重写：

> 它们不能天然构成 machine truth。

所以需要：

```text
Trusted Mutation Boundary
+
Digest / provenance
+
Validator recomputation
```

来源：`AEH-ARCH-6513102`

---

# 10. A6 — Traceability Assurance

核心闭环：

```text
REQ
→ AC
→ TEST
→ CODE
→ VER
```

Assurance 不只关心：

```text
所有测试绿
```

还关心：

```text
有没有 Requirement 没 Test？
有没有 Test 没 Requirement？
有没有 Code change 没对应 Requirement？
有没有 AC 只有手工声明没有 Verification？
```

Traceability 的强度应风险分级。

---

# 11. A7 — Verification / Acceptance Assurance

最终 Validator 需要基于实际状态重新计算：

```text
Contract valid?
Evidence fresh?
Oracle unchanged?
Scope respected?
Tests pass?
Regression pass?
Trace closed?
Approvals valid?
Critical verification present?
```

然后产生：

```text
MERGE_READY
READY_WITH_WARNINGS
BLOCKED
```

具体状态名可以演化。

长期不变量是：

> **Verdict 不是 Generator 自报字段，而是 Authority 计算结果。**

---

# 12. 一个候选 Assurance Record

以下为手册层概念结构，不声明是当前 AEH v0.1 已有 Schema：

```yaml
change_id: CHG-2026-0042

agent_claim:
  status: COMPLETED

task_outcome:
  status: PASS
  visible_tests: PASS
  hidden_tests: PASS

assurance:
  contract:
    status: PASS

  evidence:
    status: PASS
    freshness: PASS
    provenance: PASS

  oracle:
    status: PASS
    mutation_detected: false

  scope:
    status: PASS

  artifacts:
    status: PASS

  traceability:
    status: PASS

  verification:
    status: PASS

assurance_outcome:
  status: MERGE_READY

validator:
  authority: external
  replayable: true
```

如果功能正确但 Test 被实现者修改：

```yaml
task_outcome:
  status: PASS

assurance:
  oracle:
    status: BLOCKED
    reason: TEST_CHANGED

assurance_outcome:
  status: BLOCKED
```

---

# 13. Assurance 不是所有任务同样重

低风险：

```text
normal test
lint
build
```

可能已经足够。

高风险：

```text
经济系统
支付
持久化
权限
协议
数据迁移
```

可能需要：

```text
strong grounding
oracle freeze
scope verification
integration/contract verification
traceability
approval
external replay
```

因此：

> Change Assurance 是风险自适应的能力，不是统一仪式。

---

# 14. 与 Evaluation 的区别

## Change Assurance

对象：

```text
CHG-2026-0042
```

输出：

```text
MERGE_READY / BLOCKED
```

## Evaluation

对象：

```text
Codex + Context + Spec + AEH
在 72 个 trials 上表现如何？
```

输出：

```text
task success rate
false completion rate
attack block rate
cost
overhead
```

来源：`EXT-ANTHROPIC-AGENT-EVALS-2026`

所以：

```text
AEH
不能用一次自己的 verify PASS
证明 AEH 系统有价值。

AEH 的价值
必须由独立 PoV / Eval 证明。
```

---

# 15. Assurance False Completion

当前研究建议新增概念：

```text
Functional False Completion:
Agent says completed
but task_outcome FAIL

Assurance False Completion:
Agent says completed
task_outcome may PASS
but assurance_outcome BLOCKED
```

RUN-D004 更接近第二种。

这是后续 PoV 中值得专门记录的指标。

---

# 16. Architecture Invariants

[NORMATIVE]

### CA-INV-01

> **Agent Claim MUST NOT be used as a substitute for Task Outcome.**

### CA-INV-02

> **Task Outcome MUST NOT be used as a substitute for Assurance Outcome.**

### CA-INV-03

> **Evidence Presence MUST NOT imply Evidence Validity.**

### CA-INV-04

> **The Generator MUST NOT have unilateral authority to mutate the Oracle and still obtain acceptance without a repair/re-approval path.**

### CA-INV-05

> **The final Assurance Verdict MUST be independently recomputable.**

---

# 17. 当前已证明与尚未证明

## 已观察/已有契约支持

```text
✓ AEH V0.1 有独立 Validator 概念
✓ AEH V0.1 有 Test Lock / Trusted Mutation Boundary
✓ RUN-D004 观察到 Task PASS + Assurance BLOCKED
✓ Artifact existence 与 Validator acceptance 可发生分离
```

来源：

- `AEH-ARCH-6513102`
- `AEH-README-6513102`
- `EVAL-P1-D004`

## 尚未证明

```text
? AEH 是否显著提高 Task Success
? 是否显著降低 False Completion
? 是否能稳定挡住 A01–A08
? 成本是否可接受
? 是否优于已有工具组合
? 是否能跨 Python → C#/.NET → Unity brownfield
```

这些全部保留为：

```text
HYPOTHESIS
```

---

# 18. References

- `AEH-ARCH-6513102`
- `AEH-README-6513102`
- `EVAL-P1-D004`
- `EXT-ANTHROPIC-AGENT-EVALS-2026`
- `INT-DEEP-RESEARCH-20260818`
