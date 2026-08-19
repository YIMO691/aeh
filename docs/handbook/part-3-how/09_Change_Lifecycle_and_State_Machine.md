# 09 · Change 生命周期与状态机

> **章节类型**：HOW  
> **核心问题**：AEH 为什么需要状态机，以及哪些部分是长期不变量、哪些只是当前实现形式？

---

## 1. 状态机不是目的

AEH V0.1 的典型路径：

```text
Change Created
→ Ground
→ Spec
→ Test Design
→ RED
→ LOCK_TEST
→ GREEN
→ optional REFACTOR
→ VERIFY
→ Approval / Review
→ MERGE_READY
```

来源：`AEH-README-6513102`、`AEH-ARCH-6513102`。

但：

> `GROUND / RED / GREEN` 这些名字不是长期护城河。

真正不变量是：

```text
先建立 Contract
先建立可信 Oracle
实现后不得偷偷改 Oracle
实际 Diff 必须受 Scope 约束
Acceptance 前必须重算 Evidence/Verification
```

---

## 2. 为什么需要状态

如果没有状态边界：

```text
Agent 可以先改代码
再补一个 RED
再改测试
再填一个 PASS
```

所有 Artifact 都存在，但因果关系失真。

状态机的价值：

> **把“先后关系”变成可验证 Contract。**

---

## 3. VALID_RED → LOCK_TEST → GREEN

这是当前最重要的时序约束。

[AEH][FACT] Architecture P-15 冻结：

```text
VALID_RED → LOCK_TEST → GREEN
```

来源：`AEH-ARCH-6513102`。

`red.py` 只有所有 required test 都是 `VALID_RED` 后才创建 Test Lock 并迁移到 `LOCK_TEST`。来源：`AEH-RUNTIME-RED-6513102`。

---

## 4. Repair 不是绕过状态机

测试或 Spec 确实可能错误。

因此需要：

```text
TEST_REPAIR
SPEC_REPAIR
```

原则：

```text
改变成功标准
→ 新的可信路径
→ 重新 RED / 重新 Lock
```

而不是：

```text
GREEN 阶段直接编辑 Test
```

---

## 5. VERIFY 是重新计算，不是汇总

V0.1 Verify 会：

```text
重新检查 Test Lock
重新检查 Stale Evidence
重跑 target tests
重跑 regression
执行附加 verification
检查 CRITICAL requirement
检查 approval
建立 traceability
```

来源：`AEH-RUNTIME-VERIFY-6513102`。

因此 VERIFY 不是：

> “把前面的 PASS 再打印一次。”

---

## 6. MERGE_READY 不是 Merge

[AEH][FACT] AEH 停止在：

```text
MERGE_READY
```

真正：

```text
merge
push
PR
release
```

属于外部系统。

来源：`AEH-README-6513102`。

这是 Authority Separation 的一部分。

---

## 7. EXPLORE 路径

不是所有任务都适合预先有确定答案。

V0.1 保留：

```text
EXPLORE
```

用于：

```text
Hypothesis
→ Experiment
→ Evidence
→ Decision
```

说明 AEH 状态机不应把所有研发活动都强制伪装成 TDD。

---

## 8. 状态机与 Machine Truth

`change.yaml.state` 只有在：

```text
Validator-mediated transition
+
Trusted Mutation Boundary
```

存在时才有 Authority。

直接手写：

```yaml
state: DONE
```

不能等价于真实迁移。

RUN-D004 的 External Replay 体现了这种区别。来源：`EVAL-P1-D004-RAW`。

---

## 9. Architecture Invariants

### LIFE-INV-01

> **Acceptance-relevant state transitions MUST preserve causal ordering.**

### LIFE-INV-02

> **A repair that changes Contract or Oracle MUST establish a new auditable validation chain.**

### LIFE-INV-03

> **Final verification MUST recompute critical facts rather than trust cached gate fields alone.**

### LIFE-INV-04

> **MERGE_READY is an assurance verdict, not SCM mutation authority.**

---

## 10. References

- `AEH-README-6513102`
- `AEH-ARCH-6513102`
- `AEH-RUNTIME-RED-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `EVAL-P1-D004-RAW`
