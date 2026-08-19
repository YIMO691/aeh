# 附录 E · 状态与关键错误码参考

> 本表是当前手册中已验证/引用的关键状态与阻断码，不声称覆盖 AEH 源码的全部返回字符串。

## 1. 高层 Verdict

| Code | 含义 |
|---|---|
| `READY` | Doctor 全部关键检查通过 |
| `READY_WITH_WARNINGS` | 可运行但有非阻断风险 |
| `BLOCKED` | 不允许进入目标操作 |
| `MERGE_READY` | AEH 技术/治理条件满足，可交给外部 SCM 决策 |
| `READY_WITH_WARNINGS` | Verify 完成但带警告 |
| `VERIFY_COMPLETE` | Verify 流程完成；具体 overall 仍需看 verification artifact |

## 2. RED

| Code | 含义 |
|---|---|
| `VALID_RED` | 失败与冻结 expected failure 匹配 |
| `NO_RED_ALREADY_GREEN` | 测试未证明修复前失败 |
| `INVALID_RED_TEST_DEFECT` | Test 本身缺陷 |
| `INVALID_RED_SPEC_MISMATCH` | Test 与 Spec 不一致 |
| `INVALID_RED_ENVIRONMENT` | 环境错误 |
| `INVALID_RED_FIXTURE` | Fixture 错误 |
| `INVALID_RED_UNEXPECTED_FAILURE` | 未匹配的失败 |
| `BLOCKED_PRODUCTION_CHANGED_DURING_RED` | RED 期间生产代码发生变化 |
| `BLOCKED_STALE_EVIDENCE` | Grounding Evidence 已过期 |

## 3. GREEN / Scope / Oracle

| Code | 含义 |
|---|---|
| `BLOCKED_TEST_CHANGED` | Test Lock 不一致 |
| `BLOCKED_SCOPE_VIOLATION` | Changed file 越界或 Hash 不一致 |
| `BLOCKED_RUNTIME_CONTEXT_STALE` | Protected context / Evidence stale |
| `GREEN_FAILED` | Required/Regression Test 未通过 |

## 4. Trace / Verify

| Code | 含义 |
|---|---|
| `BLOCKED_TRACEABILITY_INCOMPLETE` | REQ/AC/Test/Code/VER 链不完整 |
| `BLOCKED_VERIFICATION_PLAN_INSUFFICIENT` | CRITICAL 缺 integration/contract verification |
| `BLOCKED_MANUAL_VERIFICATION_PENDING` | Manual verification 仍 pending |
| `BLOCKED_VERIFICATION_FAILED` | 实际 Verification 失败 |
| `BLOCKED_HUMAN_APPROVAL_REQUIRED` | CRITICAL 缺 MERGE_GATE approval |
| `BLOCKED_HUMAN_MERGE_REJECTED` | 人类明确拒绝 |
| `BLOCKED_INVALID_APPROVALS` | Approval Artifact Schema/可信性检查失败 |
| `BLOCKED_CHANGE_STATE` | 当前状态不允许执行目标操作 |

## 5. Doctor / Harness Integrity

| Code | 含义 |
|---|---|
| `BLOCKED_INCOMPLETE_INSTALL` | 有 staging/rollback 残留 |
| `BLOCKED_RUNTIME_INTEGRITY` | Runtime digest 与 Manifest 不一致 |
| `BLOCKED_VERSION_INCOMPATIBLE` | Harness/Schema version 不兼容 |
| `BLOCKED_PROFILE` | Profile 不可用 |
| `BLOCKED_POLICY_CONFLICT` | 同优先级政策冲突 |

来源：`AEH-RUNTIME-RED-6513102`、`AEH-RUNTIME-GREEN-6513102`、`AEH-RUNTIME-TRACE-6513102`、`AEH-RUNTIME-VERIFY-6513102`、`AEH-RUNTIME-DOCTOR-6513102`。
