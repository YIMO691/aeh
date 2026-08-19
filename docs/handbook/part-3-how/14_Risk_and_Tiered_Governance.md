# 14 · Risk 与分级治理

> **章节类型**：HOW / GOVERNANCE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **核心原则**：`Assurance Strength ∝ Engineering Risk`

---

## 1. 为什么不能所有 Change 都走最强流程

如果修改一行注释也必须 Ground→Spec→Test Design→RED→Lock→Integration Test→Traceability→Human Approval，AEH 会变成高摩擦流程。

相反，如果奖励发放、支付、权限、数据迁移、协议兼容只跑一个 Unit Test 就直接 Merge，Assurance 可能过弱。

所以核心问题是：

> **这次 Change 值得多强的验证？**

## 2. Risk 与 Complexity 不相同

大型渲染系统重构可能 Context Complexity 很高，但 Risk 只是 STANDARD；十行重复扣费修复可能 Context Complexity 中等，但 Risk 是 CRITICAL。

因此：

```text
Context Complexity → Agent 要知道多少
Engineering Risk   → 系统要验证多严
```

[DECISION] `ADR-HB-015`。

## 3. AEH V0.1 Risk Dimensions

`core/classifications.yaml` 定义：

```text
business_impact
blast_radius
irreversibility
uncertainty
compatibility
data_sensitivity
```

来源：`AEH-CORE-CLASSIFICATIONS-6513102`。

并明确 `file_count / line_count` 不得作为唯一判据。

## 4. Hard Escalation

V0.1 强制升级到 CRITICAL 的领域：

```text
money_economy
persistence
save_migration
protocol_compatibility
authentication_authorization
security_boundary
irreversible_migration
destructive_data_operation
```

来源：`AEH-CORE-CLASSIFICATIONS-6513102`。

Keyword Hints 只是启发式，过度触发被设计为 fail-safe；关键词本身不是降级依据。

## 5. 五个当前 Workflow Level

V0.1：

```text
DIRECT
LIGHTWEIGHT
STANDARD
CRITICAL
EXPLORE
```

来源：`AEH-CORE-CLASSIFICATIONS-6513102`、`AEH-README-6513102`。

这些名称是当前实现，长期真正需要冻结的是 `risk-based assurance depth`。

## 6. Risk 应驱动什么

风险越高，应逐步增加：

```text
Grounding depth
Evidence requirements
Oracle strength
Test lock strength
Regression scope
Integration / contract verification
Traceability depth
Approval
Independent replay
Artifact retention
```

概念上：

```text
LOW      → normal tests
MEDIUM   → contract + target/regression verify
HIGH     → oracle freeze + scope + trace
CRITICAL → strong evidence + integration/contract + approval + external acceptance
```

## 7. V0.1 CRITICAL 的真实约束

[AEH][FACT] VERIFY runtime 要求 CRITICAL 必须声明 `integration` 或 `contract` verification，否则 `BLOCKED_VERIFICATION_PLAN_INSUFFICIENT`。之后还要求 `MERGE_GATE == APPROVED`，否则 `BLOCKED_HUMAN_APPROVAL_REQUIRED`。来源：`AEH-RUNTIME-VERIFY-6513102`。

## 8. Human Approval 的真实强度

Approval Schema 支持 `SPEC_REVIEW / RED_GATE / MERGE_GATE`，状态 `APPROVED / REJECTED / PENDING`，并要求 APPROVED 的 `actor.type = human`。来源：`AEH-SCHEMA-APPROVAL-6513102`。

但 README 明确：Human approval 是 attestation，不是 strong identity。来源：`AEH-README-6513102`。

所以：

```text
actor.type=human ≠ 已证明真实身份
```

未来强 Identity 更适合接入 SCM identity、CI identity、OIDC、IAM、signed approval。

## 9. Approval 的正确角色

Approval 可以表达：

> “技术检查通过，我作为有权主体同意承担这次风险。”

Approval 不应该表达：

> “测试失败，但我批准，所以算 PASS。”

[AEH][FACT] V0.1 verify.py 明确让技术失败优先，approval 不能推翻失败验证。来源：`AEH-RUNTIME-VERIFY-6513102`。

## 10. EXPLORE 为什么存在

不是所有任务都适合先写确定 Spec 和 RED。探索任务可能本质是：

```text
不知道答案
→ 假设
→ 实验
→ Evidence
→ Decision
```

V0.1 保留 EXPLORE 是合理信号：Workflow 应服务任务性质，而不是强迫所有任务成为伪 TDD。来源：`AEH-README-6513102`。

## 11. Risk 与 Friction 的产品平衡

AEH 最可能失败的方式之一是：Assurance 很强，但没人愿意用。

长期目标不应是 Maximum Governance，而应是：

> **Minimum Assurance Sufficient for Risk —— 最低足够可信度。**

这也是 PoV 必须测 wall time、token、tool calls、human intervention、false escalation 的原因。

## 12. False Escalation

Fail-safe Keyword Hint 可能把普通任务误升为 CRITICAL。这比静默降级安全，但可能导致不必要 Approval、额外 Verification 和更高 Friction。

未来应测：

```text
False Escalation Rate
```

并区分 Safety fail-safe 与 Usability tax。

## 13. Architecture Invariants

### RK-INV-01
> **Assurance depth MUST be risk-sensitive.**

### RK-INV-02
> **File count and line count MUST NOT be the sole risk classifier.**

### RK-INV-03
> **Hard-risk domains MUST NOT be silently downgraded by a weaker heuristic.**

### RK-INV-04
> **Approval MAY authorize risk acceptance, but MUST NOT rewrite deterministic technical failure into success.**

### RK-INV-05
> **Context complexity and engineering risk MUST remain orthogonal dimensions.**

## 14. 当前实现事实与限制

已支持：六个风险维度、五个 workflow level、hard escalation domains、CRITICAL integration/contract verification、CRITICAL human merge approval、技术失败不能被 approval 覆盖。

限制：Approval 仍是 attestation；Keyword hints 是 heuristic；跨领域 Risk Calibration、False Escalation 成本、Unity/C# 高风险分布仍未验证。

## 15. References

- `AEH-CORE-CLASSIFICATIONS-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `AEH-SCHEMA-APPROVAL-6513102`
- `AEH-README-6513102`
- `EXT-ANTHROPIC-CONTEXT-ENGINEERING-2025`
