# 11 · Test Oracle 与 Test Integrity

> **章节类型**：HOW / CORE ASSURANCE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **核心概念**：`Oracle Ownership Separation`

---

## 1. 为什么本章不是“TDD 教程”

AEH V0.1 有 `Test Design → RED → VALID_RED → LOCK_TEST → GREEN`，这很容易让人误以为 AEH 的价值就是强制 TDD。

真正的问题是：

> **谁有权定义“什么叫正确”？**

测试只是最常见的 Oracle。

## 2. 什么是 Oracle

Oracle 是判断实现是否满足预期的外部成功标准，可以是：

```text
Unit Test
Integration Test
Contract Test
Property
Invariant
Static analysis rule
Runtime observation
Manual acceptance procedure
Formal proof obligation
```

所以：

```text
Oracle Integrity > Test File Integrity
```

Test Lock 只是 Oracle Integrity 的一种工程实现。

## 3. 同一个 Agent 写测试不是原罪

错误结论是“AI 写的测试都不能信”。Agent 完全可以有效地理解需求、写测试、执行测试，并根据外部失败反馈修复代码。

真正边界是：

> **当实现进入被验证阶段后，是否还能无条件改写 Oracle，并仍然保持原 Assurance 状态。**

```text
Who authored the test?       不是核心
Who can mutate the oracle?   才是核心
```

## 4. VALID RED 的作用

一个测试在实现前失败，并不自动证明它是正确 Oracle。

V0.1 RED runtime 会区分：

```text
VALID_RED
INVALID_RED_TEST_DEFECT
INVALID_RED_SPEC_MISMATCH
INVALID_RED_ENVIRONMENT
INVALID_RED_FIXTURE
INVALID_RED_UNEXPECTED_FAILURE
NO_RED_ALREADY_GREEN
```

来源：`AEH-RUNTIME-RED-6513102`。

所以：

```text
RED ≠ 任何失败
VALID_RED = 与冻结 expected failure 相匹配的失败
```

## 5. RED Evidence

V0.1 RED Schema 要求：

```text
test_id
command
exit_code
output_ref
output_hash
expected_failure
actual_failure
base_commit
changed_files_hash
test_files_hash
verdict
```

来源：`AEH-SCHEMA-RED-6513102`。

这让 RED 具备“可检查失败 + 可绑定 Repository State + 可比对测试内容”的基础。

## 6. RED 阶段还保护生产代码

[AEH][FACT] V0.1 `red.py` 在 RED 前后对目标仓库做快照；如果 RED 执行期间生产区发生变化，会返回 `BLOCKED_PRODUCTION_CHANGED_DURING_RED`。来源：`AEH-RUNTIME-RED-6513102`。

意义是：RED Evidence 应描述“修复前”的真实状态，而不是 Agent 一边修改实现一边制造 RED。

## 7. 从 VALID_RED 到 Test Lock

冻结顺序：

```text
VALID_RED
   ↓
LOCK_TEST
   ↓
GREEN
```

来源：`AEH-ARCH-6513102`、`AEH-RUNTIME-RED-6513102`。

Test Lock Schema 记录：

```yaml
files:
  - path:
    hash:
protected:
  spec.yaml: <sha256>
  evidence.yaml: <sha256>
  .aeh/profile.yaml: <sha256>
  .aeh/effective-workflow.yaml: <sha256>
```

来源：`AEH-SCHEMA-TESTLOCK-6513102`。

因此 V0.1 实际冻结的不只有测试文件，还保护部分运行上下文。

## 8. GREEN 如何检查 Oracle

[AEH][FACT] GREEN runtime 在执行测试前重新计算 Test File Hash，与 Lock 对比；不一致返回 `BLOCKED_TEST_CHANGED`。之后运行 required tests 和 regression，最后再次重新计算 Lock。来源：`AEH-RUNTIME-GREEN-6513102`。

这比“Agent 请不要改测试”更强，因为它把 Guidance 升级为可重算 Gate。

## 9. Oracle Ownership Separation

[DECISION] `ADR-HB-012`

长期原则：

> **一旦某个 Oracle 被用于证明实现正确，被验证实现不得在不重新建立可信验证流程的情况下单方面改变该 Oracle。**

正确路线：

```text
Oracle O0
Implementation I0
VALID_RED(O0, I0)
        ↓
Freeze O0
        ↓
Implementation I1
        ↓
Verify(O0, I1)
```

错误路线：

```text
O0 + I0
 ↓ RED
改 I，同时改 O0 → O1
 ↓
GREEN(O1, I1)
```

此时无法知道是实现满足原目标，还是目标被改了。

## 10. Test Repair 为什么必须显式

Oracle 不应该永远不可修改，测试可能真的错。正确体系不是“测试永远只读”，而是：

```text
GREEN 阶段不可直接改

如需修改：
TEST_REPAIR
→ 说明原因
→ 更新 Oracle
→ 重新 VALID_RED
→ 新 Lock
```

AEH V0.1 冻结架构 P-15 已预留 `TEST_REPAIR / SPEC_REPAIR`。来源：`AEH-ARCH-6513102`。

> Oracle 可以演进，但不能偷偷演进。

## 11. Hidden Tests 与 Test Lock 的区别

Hidden Tests 防止 Generator 针对可见测试刷答案；Test Lock 防止 Generator 在已经建立 Oracle 后修改成功标准。

```text
Hidden Test ≠ Test Lock
```

PoV 中 Hidden Tests 属于 Evaluation Plane；Test Lock 属于 Change Assurance Plane。

## 12. Mutation Testing 的位置

Mutation Testing 回答 Test Oracle 是否对错误实现足够敏感，测的是 `Oracle Strength`；Test Lock 测的是 `Oracle Integrity`。

所以未来更合理的边界是：

```text
Mutation Testing = Integration / optional evidence
Oracle Integrity = AEH Core
```

## 13. Failure Modes

### FM-OR-01 — Test Mutation During GREEN

期望：`BLOCKED_TEST_CHANGED`。对应 PoV `A01 Test Mutation`。

### FM-OR-02 — Fake RED

测试红是因为 ImportError / Fixture / Environment，却标成 VALID_RED。V0.1 已有 RED taxonomy，但 Attack Suite 仍需验证能否绕过。对应 `A06 Fake RED`。

### FM-OR-03 — Weak Oracle

测试一开始就 GREEN。V0.1 返回 `NO_RED_ALREADY_GREEN`，这可能代表需求已经满足、测试太弱或 Spec mismatch，不能直接进入正常 GREEN。

## 14. Architecture Invariants

### OR-INV-01
> **A failed test is not a VALID_RED unless its failure matches the expected pre-fix behavior.**

### OR-INV-02
> **Once an Oracle is frozen for implementation, the Generator MUST NOT unilaterally mutate it and retain the same assurance chain.**

### OR-INV-03
> **Oracle repair MUST create a new auditable validation path.**

### OR-INV-04
> **Test Lock is replaceable as an implementation mechanism; Oracle Ownership Separation is not.**

## 15. 当前实现事实与限制

已支持：RED taxonomy、output hash、RED 前后 production snapshot、VALID_RED→Test Lock、test path/hash lock、protected context hash、GREEN 前后 Lock 检查、`BLOCKED_TEST_CHANGED`。

尚不能宣称：所有 Oracle 类型已支持、Mutation Testing 已集成、Test Lock 绝对不可绕过、A01/A06 已通过正式攻击实验。

## 16. References

- `AEH-ARCH-6513102`
- `AEH-SCHEMA-RED-6513102`
- `AEH-SCHEMA-TESTLOCK-6513102`
- `AEH-RUNTIME-RED-6513102`
- `AEH-RUNTIME-GREEN-6513102`
- `INT-DEEP-RESEARCH-20260818`
