# 13 · Traceability 与 Acceptance

> **章节类型**：HOW / CORE ASSURANCE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **核心链路**：`REQ → AC → TEST → CODE → VER`

---

## 1. 为什么“所有测试都绿”还不够

假设 1000 tests PASS，仍可能出现：某条新 Requirement 没测试、某个 AC 被遗漏、Agent 顺手改了无关代码、某个 Verification 没对应任何需求。

所以 Test Result 回答“测到的东西是否 PASS”，Traceability 回答：

> **应该测的东西是否真的被覆盖？每个实际变更为什么存在？**

## 2. Traceability 的基本模型

```text
REQ-001
  ↓
AC-001-01
  ↓
TEST-001
  ↓
CODE-001
  ↓
VER-001
```

链不必严格线性。核心是：

> **每个需要接受的 Claim 都能找到对应 Verification Path。**

## 3. AEH V0.1 Traceability Schema

V0.1 Schema 以 Requirement 为主索引：

```yaml
requirements:
  - id: REQ-001
    acceptance: []
    tests: []
    tasks: []
    code: []
    verification: []
```

Code 可记录 `path / code_id`。来源：`AEH-SCHEMA-TRACE-6513102`。

## 4. Forward Trace

Forward Trace 回答：`REQ-001 最终怎么被证明？`

V0.1 runtime：

1. 从 Spec 读取 REQ / AC；
2. 从 Test Plan 建立 `AC → Tests`；
3. 根据 Test Targets 把 changed code 关联回 Test；
4. 从 Verification 的 `verifies` 关联 VER；
5. 生成 `traceability.yaml`。

来源：`AEH-RUNTIME-TRACE-6513102`。

## 5. Uncovered Acceptance Criteria

V0.1 对 `automated / invariant` 类型 AC，如果没有 Test，则产生 `uncovered AC`；除非列入 `non_automatable` 且给出理由。来源：`AEH-RUNTIME-TRACE-6513102`。

这比“测试数量很多”更重要，因为它直接问：

> 需求闭合了吗？

## 6. Backward Trace 与 Orphan Detection

V0.1 会检查：

```text
orphan test
orphan code
orphan verification
```

来源：`AEH-RUNTIME-TRACE-6513102`。

- Orphan Test：没有对应已知 AC；
- Orphan Code：changed code 不被任何 Requirement 通过 Test Target 链接；
- Orphan Verification：VER 不属于任何 Requirement。

这使 Traceability 同时具备前向覆盖和反向越界检测能力。

## 7. Traceability 与 Verification 的循环关系

V0.1 `verify.py` 流程：

```text
运行 target/regression/additional verification
        ↓
写 verification.yaml
        ↓
build_traceability()
        ↓
如果不完整：
  BLOCKED_TRACEABILITY_INCOMPLETE
        ↓
只有完整：
  verify gate = PASS
```

来源：`AEH-RUNTIME-VERIFY-6513102`。

因此 Traceability 不是最后生成一份漂亮报告，而是 Acceptance Gate 的组成部分。

## 8. Verification 类型

V0.1 Verification Schema 支持：

```text
target_test
regression
integration
contract
runtime
platform
manual
```

方法包括：

```text
static_review
build
automated_test
breakpoint
log
manual_runtime
visual_review
relogin
persistence_check
```

来源：`AEH-SCHEMA-VERIFY-6513102`。

这说明 Trace Model 不只针对 Unit Test。

## 9. CRITICAL 的额外 Verification

V0.1 VERIFY 对 CRITICAL 要求 verification plan 至少声明 `integration` 或 `contract`，否则返回 `BLOCKED_VERIFICATION_PLAN_INSUFFICIENT`。来源：`AEH-RUNTIME-VERIFY-6513102`。

体现：

```text
Risk → Verification Depth
```

## 10. Manual Verification 的诚实边界

V0.1 遇到 manual verification，会记录 pending 并返回 `BLOCKED_MANUAL_VERIFICATION_PENDING`。来源：`AEH-RUNTIME-VERIFY-6513102`。

这是正确的“诚实失败”：没有自动证据时，不应该伪造 PASS。

## 11. Approval 不能推翻技术失败

V0.1 VERIFY 明确让 technical failure 优先，approval 只能解除治理阻塞，不能把失败测试变成功。来源：`AEH-RUNTIME-VERIFY-6513102`。

架构原则：

> **Human Authority 可以批准风险承担，但不能改写客观技术失败。**

## 12. MERGE_READY 的含义

V0.1 Verification Schema：

```text
MERGE_READY
READY_WITH_WARNINGS
BLOCKED
```

来源：`AEH-SCHEMA-VERIFY-6513102`。

README 明确 AEH stops at MERGE_READY；merge/push/PR/release remain external。来源：`AEH-README-6513102`。

因此 `MERGE_READY` 是 AEH 的 Acceptance Verdict，不是实际 Merge。

## 13. Traceability 强度是否固定

不应该。[DECISION] `ADR-HB-014`。

对于 typo/comment/small formatting，完整 REQ→AC→TEST→CODE→VER 可能成本过高；对于 payment/reward/persistence/protocol/authorization，强 Traceability 很有价值。

长期模型应是：

```text
Risk → Required Trace Depth
```

而不是所有 Change 都产生相同数量的 ID。

## 14. Traceability 与 Documentation 的区别

Markdown Review：便于人类理解。

机器 Trace：用于机器检查、孤儿检测、Acceptance Gate。

V0.1 `traceability.py` 已明确：`traceability.yaml = machine truth`，`review.md = human narrative projection`。来源：`AEH-RUNTIME-TRACE-6513102`。

## 15. Architecture Invariants

### TR-INV-01
> **For assurance-relevant requirements, Acceptance MUST be traceable to concrete verification evidence.**

### TR-INV-02
> **Changed production code SHOULD be explainable by the Change Contract; unjustified orphan code is an assurance defect.**

### TR-INV-03
> **Traceability completeness MAY be risk-weighted, but high-risk Change acceptance MUST NOT rely on untraceable narrative claims.**

### TR-INV-04
> **Human-readable review text MUST NOT replace machine traceability truth.**

## 16. 当前实现事实与限制

已支持：REQ→AC→TEST→CODE→VER mapping、uncovered AC、orphan test/code/verification、traceability incomplete blocks Verify、多 verification types。

需要后续研究：大型 C#/Unity 项目 symbol-level Trace、generated code/config/assets Trace、低风险 Trace 最小集、多 Spec Provider IR 映射。

## 17. References

- `AEH-SCHEMA-TRACE-6513102`
- `AEH-RUNTIME-TRACE-6513102`
- `AEH-SCHEMA-VERIFY-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `AEH-README-6513102`
- `AEH-CORE-CLASSIFICATIONS-6513102`
