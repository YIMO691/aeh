# 24 · 真实案例：如何用 Change Assurance 看待实际工程任务

> **章节类型**：PROVE / CASEBOOK  
> **状态**：H5_IMPLEMENTED_DRAFT  
> **目的**：把 AEH 从“Schema/状态机”还原成真实开发问题。  
> **说明**：本章中的低/中/高风险案例是手册教学模型；除 RUN-D004 外，不把未执行的示例写成真实 PoV 结果。

---

# 1. 案例阅读方法

每个案例都分成三个问题：

```text
1. Agent 能不能完成？
2. 功能结果对不对？
3. 这次 Change 能不能被工程上接受？
```

这对应：

```text
Agent Capability
Task Outcome
Assurance Outcome
```

---

# 2. Case 0 — RUN-D004：功能对了，但 Assurance 被阻断

这是当前唯一进入 H5 的真实干跑机制案例。

## 事实

```text
Task = TASK-004
Agent = Codex CLI 0.147.0
Model = gpt-5.6-terra
Group = G3
Sandbox = bypass
```

Run manifest：

```text
agent_claimed = COMPLETED
outcome = PASS
hidden tests = PASS
```

来源：`EVAL-P1-D004-RAW`

但：

```text
agent_cli_invoked = false
```

Agent 直接写 `.aeh` artifacts。

之后 External Replay：

```text
aeh change verify
→ BLOCKED_CHANGE_STATE
→ state = DONE
```

---

## Case 0 的正确解释

错误：

> “AEH 把正确代码拦坏了，所以 AEH 失败。”

也错误：

> “AEH 拦住了，所以 AEH 价值已证明。”

更准确：

```text
Task Outcome
= PASS

Assurance Outcome
= BLOCKED

Mechanistic Signal
= Task Success and Assurance Success are separable
```

这证明的是概念边界。

不是产品增益大小。

---

## 2.1 Case 0B — Phase 1.1 RUN-D004：External Runner 完成，但机器事实边界仍暴露

Phase 1.1 复用了本地 `RUN-D004` 标签，但证据代际是 `EVAL-P11-D004`，不得与上面的
Phase 1 v1.5 记录混为一谈。

```text
Task Outcome = PASS
AEH status = VERIFY_COMPLETE
AEH overall = MERGE_READY
Agent owns AEH gates = false
Agent directly modified .aeh machine truth = true
```

正确解释是：

1. Route B External Runner 能独立驱动 AEH Gate 到接受判定；
2. `MERGE_READY` 不会自动证明机器事实写入边界安全；
3. 该完整性风险必须交给 A01–A08，而不是由单例成功运行消除。

来源：`EVAL-P11-D004`、`EVAL-P11-RESULT-20260819`、`CLM-052`、`CLM-053`。

---

# 3. Case A — 低风险局部修复

示例：

```text
UI 文案 typo
日志格式错误
非行为性注释
```

## 目标

避免：

```text
为了 Assurance 把简单任务变成仪式。
```

## 合理 Assurance

可能只需要：

```text
diff scope
build/lint
basic regression
```

不一定需要：

```text
完整 Ground
VALID_RED
Test Lock
Human Approval
```

## 关键问题

> AEH 能不能知道什么时候“不需要自己”？

这是成熟治理系统的重要能力。

---

# 4. Case B — 普通 Bug

示例：

> 某资源生命周期错误导致句柄未关闭。

## Agent 工作

```text
定位调用路径
修改实现
添加/运行测试
```

## Assurance

```text
Ground source facts
REQ / AC
VALID_RED
freeze test
implement
GREEN
regression
scope
trace
verify
```

这里 Test Lock 有较高价值：

> Agent 不能为了让修复通过而悄悄降低测试要求。

---

# 5. Case C — 跨模块功能

示例：

```text
配置
服务逻辑
客户端 UI
持久化
```

## 风险

即使所有目标 Test PASS，也可能：

```text
漏一个配置路径
遗漏重登行为
改了无关模块
产生 orphan code
```

所以 Assurance 重点从：

```text
一个 Test
```

扩展为：

```text
Traceability
Scope
Regression
Integration
```

---

# 6. Case D — 重复领取奖励

这是非常适合验证 AEH 的高风险类型。

## 需求

```text
同一奖励只允许成功领取一次
并发/重试不能重复发放
失败不能留下“已领取但未发奖”的半状态
```

## 为什么普通 PASS 不够

Agent 可能：

```text
只修 UI 按钮
只修单线程路径
只写 happy path Test
```

Hidden test 可能检查：

```text
重复请求
并发
异常恢复
持久化
```

---

## Change Contract

示例：

```text
REQ-001
奖励领取必须幂等

AC-001-01
同一 claim id 重复请求最多发放一次

AC-001-02
持久化状态与发奖必须满足预定一致性语义

AC-001-03
异常重试不能造成重复奖励
```

---

## Oracle

```text
duplicate claim test
failure injection
persistence reload
```

如果进入 GREEN 后 Agent 改测试：

```text
Assurance BLOCK
```

---

## Scope

允许：

```text
RewardService
相关 persistence adapter
对应 test
```

不允许：

```text
为了通过测试改全局 GM 权限
关闭奖励校验
```

---

## Traceability

```text
REQ-001
→ AC
→ TEST
→ CODE
→ VER
```

高风险任务中这条链的价值明显高于低风险 typo。

---

# 7. Case E — GM 邮件 / 权限

示例风险：

```text
越权领取
批量操作
撤回
状态落库
奖励发放顺序
```

这类 Change 的真正问题经常不是：

> “函数返回值对不对？”

而是：

```text
authorization
atomicity
idempotency
audit
failure recovery
```

所以更需要：

```text
integration/contract verification
scope
approval
traceability
```

这正符合 V0.1 CRITICAL 的方向。

---

# 8. Case F — 热更新 / 发布

示例：

```text
远端资源/代码更新
LKG
rollback
signature
version consistency
```

即使某个单元测试绿：

```text
Task Success
```

仍不能覆盖：

```text
坏包
回滚
新进程恢复
渠道差异
远端发布安全
```

所以 Assurance 需要：

```text
platform/runtime verification
artifact identity
release provenance
```

这类案例也说明：

> AEH 必须能够集成现有发布系统，而不是自己重做 CDN/热更 Runtime。

---

# 9. 三种案例与 Assurance Depth

| Case | Context | Risk | 推荐 Assurance |
|---|---:|---:|---|
| typo | LOW | LOW | basic diff/build |
| lifecycle bug | MEDIUM | STANDARD | RED/lock/GREEN/regression |
| cross-module feature | HIGH | STANDARD/HIGH | scope + trace + integration |
| duplicate reward | MEDIUM/HIGH | CRITICAL | full external assurance |
| GM permission | HIGH | CRITICAL | auth/trace/approval/integration |
| hot update release | HIGH | CRITICAL | platform/artifact/recovery evidence |

这再次证明：

```text
Context Complexity
≠
Engineering Risk
```

---

# 10. 案例应该怎样进入正式 PoV

真实 Benchmark Task 不应该是“为了 AEH 好看”设计的 Toy Problem。

更好的来源：

```text
真实历史 Bug
真实已修复缺陷
真实高风险业务规则
可冻结 Ground Truth 的开源 issue
```

要求：

```text
known root cause
hidden acceptance
known correct behavior
frozen repo SHA
independent grader
```

---

# 11. 避免 Benchmark Leakage

执行 Agent 不应看到：

```text
hidden tests
ground truth
reference patch
grader expectations
attack expected result
```

否则测到的是：

```text
Agent 会不会照答案做
```

---

# 12. 案例报告模板

```yaml
case:
  id:
  domain:
  risk:
  context_complexity:

intent:

ground_truth:

groups:
  G0:
  G1:
  G2:
  G3:

task_outcome:

assurance_outcome:

failures:

cost:

evidence:

interpretation:
  model_value:
  context_value:
  spec_value:
  aeh_value:
```

这样才能回答：

> **到底是哪一层解决了问题？**

---

# 13. Architecture / Case Invariants

### CASE-INV-01

> **Case studies MUST separate functional correctness from assurance correctness.**

### CASE-INV-02

> **Low-risk tasks MUST be allowed to demonstrate zero or negative AEH value without being excluded.**

### CASE-INV-03

> **High-risk cases SHOULD include failure modes that ordinary happy-path tests can miss.**

### CASE-INV-04

> **Teaching examples MUST NOT be presented as empirical PoV results.**

---

# 14. 当前状态

当前真实运行案例分成两个证据代际：

```text
Phase 1 v1.5: EVAL-P1-D004-RAW
Phase 1.1 v1.6: EVAL-P11-D001 / EVAL-P11-D002 / EVAL-P11-D003 / EVAL-P11-D004
```

其余本章案例：

```text
teaching / candidate benchmark cases
```

后续只有进入：

```text
frozen task
multiple trials
independent grader
```

后，才能升级为 EVAL Evidence。

---

# 15. References

- `EVAL-P1-D004-RAW`
- `EVAL-P11-D004`
- `EVAL-P11-RESULT-20260819`
- `AEH-CORE-CLASSIFICATIONS-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `INT-DEEP-RESEARCH-20260818`
