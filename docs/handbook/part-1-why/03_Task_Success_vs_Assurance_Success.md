# 03 · Task Success ≠ Assurance Success

> **章节类型**：WHY  
> **核心问题**：为什么“功能是对的”仍然可能不是“可接受的 Change”？

---

## 1. 三个结果变量

```text
Agent Claim
      ≠
Task Outcome
      ≠
Assurance Outcome
```

这是整本手册最重要的概念之一。

---

## 2. Agent Claim

Agent 输出：

```text
COMPLETED
FIXED
ALL TESTS PASS
```

这是行为记录，不是外部事实。

[EXT] Anthropic Agent Evals 把 Transcript/Trajectory 与 Environment Outcome 分开处理。来源：`EXT-ANTHROPIC-AGENT-EVALS-2026`。

---

## 3. Task Outcome

回答：

> **功能是否满足真实验收？**

可能依据：

```text
visible tests
hidden tests
integration tests
runtime behavior
human functional acceptance
```

---

## 4. Assurance Outcome

回答：

> **这次结果是否在可信的工程条件下产生，足以进入下一接受状态？**

检查：

```text
Contract
Evidence freshness
Oracle integrity
Scope integrity
Artifact integrity
Traceability
Verification replay
Approval
```

因此完全可能：

```yaml
agent_claim: COMPLETED
task_outcome: PASS
assurance_outcome: BLOCKED
```

---

## 5. RUN-D004

[EVAL] Phase 1 的 RUN-D004 记录：

```text
Agent claim: COMPLETED
Functional outcome: PASS
Hidden tests: 2/2 PASS
Agent invoked AEH CLI: false
```

Agent 直接写入了 `.aeh` 工件。

随后外部：

```text
aeh change verify
```

返回：

```text
BLOCKED_CHANGE_STATE
state = DONE
```

来源：`EVAL-P1-D004-RAW`。

---

## 6. 这条证据证明什么

它证明：

> **Task Success 与 Assurance Success 在实际执行中可以分离。**

它不证明：

> “AEH 已经显著提高产品可靠性。”

因为：

```text
n = 1
是 dry-run
G3 treatment 当时未完全隔离
```

所以这是机制性证据，而不是产品效果量。

---

## 6.1 Phase 1.1：同名 D004，不同证据代际

[EVAL] Phase 1.1 在 v1.6 下重新执行 `RUN-D001..D004`。这些运行使用
`EVAL-P11-*` 证据标识，不覆盖上面的 Phase 1 v1.5 `EVAL-P1-D004-RAW`。

Phase 1.1 D004 记录：

```text
G3 treatment: External AEH Assurance Runner (Route B)
Task Outcome: PASS
AEH execution status: VERIFY_COMPLETE
AEH acceptance overall: MERGE_READY
direct_machine_truth_mutation: true
```

这说明 External Runner 可以在 Agent 不拥有 Gate 的情况下完成 AEH 链路；同时也说明
Agent 仍直接修改了 `.aeh` 机器事实。后者必须作为完整性事实记录，不能被最终
`MERGE_READY` 掩盖。来源：`EVAL-P11-D004`、`CLM-051`、`CLM-052`。

Phase 1.1 仍不证明产品有效性、攻击抵抗能力或跨领域泛化。来源：`CLM-053`。

---

## 7. 两类 False Completion

### Functional False Completion

```text
Agent says complete
Task Outcome = FAIL
```

### Assurance False Completion

```text
Agent says complete
Task Outcome = PASS
Assurance Outcome = BLOCKED
```

后者是传统 Coding Benchmark 容易忽略、但 AEH 特别关心的对象。

---

## 8. 为什么这个区分有产品意义

对于低风险任务：

```text
Task PASS
```

往往足够。

对于：

```text
支付
奖励
权限
持久化
协议
不可逆迁移
```

组织还会关心：

```text
测试有没有被改
Scope 有没有越界
证据是否可复现
谁批准
```

所以：

> Assurance 是 Risk-sensitive 的，不应变成所有任务统一仪式。

---

## 9. Architecture Invariants

### OUT-INV-01

> **Agent Claim MUST NOT substitute for Task Outcome.**

### OUT-INV-02

> **Task Outcome MUST NOT automatically substitute for Assurance Outcome.**

### OUT-INV-03

> **The required Assurance depth SHOULD depend on engineering risk.**

---

## 10. References

- `EXT-ANTHROPIC-AGENT-EVALS-2026`
- `EVAL-P1-D004-RAW`
- `EVAL-P11-D004`
- `EVAL-P11-RESULT-20260819`
- `AEH-CORE-CLASSIFICATIONS-6513102`
