# 25 · 成本、Friction 与“工程税”

> **章节类型**：PROVE / ECONOMICS  
> **状态**：H5_IMPLEMENTED_DRAFT  
> **核心问题**：AEH 即使更安全，如果让正常开发成本失控，也不应继续扩张。

---

# 1. Assurance 不是免费的

AEH 增加的可能成本：

```text
更多输入
更多步骤
更多 Tool Calls
更多 Test Runs
更多 Artifact
更多等待
更多人工 Gate
更多 Token
```

所以不能只问：

> “能不能拦住错误？”

还要问：

> **值不值得？**

---

# 2. 需要测量的成本

至少：

```text
wall time
tokens
tool calls
human interventions
number of blocked retries
false escalation
repair burden
artifact burden
```

另外可以记录：

```text
prompt/context size
CI compute
storage
review time
```

---

# 3. Phase 1 当前看到的原始数字

当前单次 Dry Run：

```text
G0:
wall time 179s
tokens 13,577
tool calls 5

G1:
175s
28,572
3

G2:
173s
11,178
3

G3:
269s
31,665
10
```

这些数字来自 Phase 1 研究底稿与 Run Evidence。

D004 原始 manifest 明确：

```text
269s
31665 tokens
10 tool calls
0 human interventions
```

来源：`EVAL-P1-D004-RAW`

---

## 3.1 Phase 1.1 v1.6 原始指标

Phase 1.1 使用 `EVAL-P11-*` 独立证据代际，run.yaml 中的冻结指标为：

```text
G0: 189s / 13,435 tokens / 5 tool calls
G1: 179s / 22,889 tokens / 4 tool calls
G2: 180s / 29,798 tokens / 4 tool calls
G3: 217s / 52,465 tokens / 22 tool calls
```

tool-call 数以各 run 的 `result.metrics` 为准，不以报告作者对 transcript 的二次人工计数
覆盖。Phase 1.1 仍是每组单例，不能据此估计稳定 overhead。来源：
`EVAL-P11-D001`、`EVAL-P11-D002`、`EVAL-P11-D003`、`EVAL-P11-D004`。

---

# 4. 为什么不能把它写成“AEH +55% 成本”

因为：

```text
n = 1 per group
G3 treatment 不干净
Agent 没真正按预期驱动 AEH
模型随机性很高
网络不稳
sandbox bypass
Context payload 不同
```

所以：

[FACT][LIMITATION]

> **Phase 1 的成本数据只能证明“指标可以被采集”，不能估计稳定产品 overhead。**

来源：`CLM-050`

---

# 5. 成本应该比较什么

最关键不是：

```text
AEH 比 Bare Agent 多花多少
```

而是：

```text
G3 vs G2
```

因为：

```text
G2
已经拥有 Context + Spec
```

这样才能估计：

> **Independent Assurance 本身的增量成本。**

---

# 6. 成本必须按 Risk Slice 看

如果：

```text
LOW risk
AEH +40%
Assurance gain ≈ 0
```

应减少流程。

如果：

```text
CRITICAL
AEH +30%
False Completion -80%
Integrity Attack Escape → 0
```

可能非常值得。

因此：

```text
one global overhead number
```

可能误导产品设计。

---

# 7. Friction 不只是时间

## Cognitive Friction

用户要理解：

```text
Ground
Spec
RED
Lock
Scope
Trace
```

多少概念？

## Operational Friction

要运行多少：

```text
CLI commands
files
manual steps
```

## Failure Friction

系统 BLOCK 后：

```text
用户知道为什么吗？
有 remediation 吗？
是否容易恢复？
```

Doctor 当前提供：

```text
message
evidence
remediation
```

是好的方向。

来源：`AEH-SCHEMA-DOCTOR-6513102`

---

# 8. False Escalation 是重要成本

Risk Keyword Hint 可能：

```text
reward
money
db
```

把任务升级 CRITICAL。

来源：`AEH-CORE-CLASSIFICATIONS-6513102`

Fail-safe 对安全有利，但错误升级会增加：

```text
extra test
approval
integration verification
delay
```

所以未来应记录：

```text
False Escalation Rate
```

---

# 9. Friction Test

AEH 应专门有：

```text
LOW-RISK FRICTION BENCHMARK
```

例如：

```text
rename
comment
small log fix
localized UI change
```

看：

```text
是否被错误要求完整 Assurance
是否产生不必要 BLOCK
平均多几步
```

如果低风险体验很差：

> 风险分层失败。

---

# 10. Human Intervention

理想情况：

```text
AEH 更强
同时
人工纠正次数下降
```

最差情况：

```text
AEH 把 Agent 每一步都卡住
最后人类不停手动解锁
```

那只是把：

```text
AI 自动化
```

变成：

```text
人肉流程审批
```

不是目标。

---

# 11. Block Quality

每个 BLOCK 应至少回答：

```text
What failed?
Why?
What evidence?
Can it be repaired?
Who has authority?
```

例如：

```text
BLOCKED_TEST_CHANGED
```

比：

```text
Workflow failed
```

更有工程价值。

---

# 12. Economics Gate

Phase 0 报告已有预注册 Cost Gate。

本手册的原则是：

> **不要在结果出来后为了让 AEH PASS 而放宽成本阈值。**

如果正式 Pilot 显示：

```text
Reliability gain low
Cost high
```

合理 Verdict 就是：

```text
INTEGRATE
REPOSITION
STOP
```

---

# 13. Value Density

建议长期使用：

```text
Assurance Gain
──────────────
Overhead
```

而不是：

```text
Feature Count
```

例如：

```text
Test Lock
成本小
可拦严重 Test Mutation
→ value density high

Web UI
成本大
不直接增强 Assurance
→ value density low
```

这可以指导 Roadmap。

---

# 14. 与模型进步的关系

随着 Coding Agent 变强：

```text
普通任务成功率 ↑
```

AEH 若仍强迫：

```text
同样 Ceremony
```

相对成本会越来越明显。

所以 AEH 的长期优势不能依赖：

> 模型很笨，需要很多流程。

它应该依赖：

> **高自主系统仍需要独立 Acceptance。**

---

# 15. Minimum Sufficient Assurance

手册建议最终目标：

> # **不是 Maximum Governance，而是 Minimum Sufficient Assurance。**

对每个 Risk：

```text
选择最低足够的
Evidence
Oracle
Scope
Trace
Approval
Replay
```

达到可信要求。

---

# 16. Architecture / Economics Invariants

### COST-INV-01

> **AEH MUST measure the cost of assurance, not only its correctness benefits.**

### COST-INV-02

> **Overhead SHOULD be evaluated against G2, not only against a bare Agent baseline.**

### COST-INV-03

> **Low-risk tasks MUST have a lightweight path.**

### COST-INV-04

> **A safety mechanism with excessive false escalation is a product defect even if it is fail-safe.**

### COST-INV-05

> **Roadmap priority SHOULD favor assurance value density over feature breadth.**

---

# 17. 当前状态

已经有：

```text
✓ wall-time collection
✓ token collection
✓ tool-call collection
✓ human intervention field
```

还没有：

```text
✗ statistically meaningful overhead
✗ risk-sliced friction distribution
✗ false escalation benchmark
✗ repair burden measurement
```

因此：

> **AEH Economics remains UNPROVEN.**

Phase 1.1 增加了一组口径更清晰的采集记录，但没有改变这一结论。

---

# 18. References

- `EVAL-P1-D001`
- `EVAL-P1-D002`
- `EVAL-P1-D003`
- `EVAL-P1-D004-RAW`
- `EVAL-P1-HANDOFF-20260818`
- `EVAL-P11-D001`
- `EVAL-P11-D002`
- `EVAL-P11-D003`
- `EVAL-P11-D004`
- `AEH-CORE-CLASSIFICATIONS-6513102`
- `AEH-SCHEMA-DOCTOR-6513102`
- `INT-DEEP-RESEARCH-20260818`
