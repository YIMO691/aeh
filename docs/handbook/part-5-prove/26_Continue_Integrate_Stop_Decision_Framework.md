# 26 · CONTINUE / INTEGRATE / STOP：AEH 的最终决策框架

> **章节类型**：PROVE / STRATEGY  
> **状态**：H5_IMPLEMENTED_DRAFT  
> **当前临时裁决**：`CONTINUE_BUT_NARROW — conditional`  
> **核心问题**：什么证据出现以后，AEH 才有资格继续？什么证据出现以后，应该停止或集成？

---

# 1. 为什么必须允许 STOP

一个真正证据驱动的项目必须允许结论：

```text
“这个项目不值得继续。”
```

如果所有研究最终都只能导向：

```text
CONTINUE
```

那么 PoV 只是宣传。

AEH 必须接受：

```text
CONTINUE
CONTINUE_BUT_NARROW
INTEGRATE
REPOSITION
STOP
```

五种结果。

---

# 2. 当前为什么不是 CONTINUE

当前已经知道：

```text
V0.1 有真实实现
232/232 release tests PASS
有独立 Validator 设计
有 Test Lock / Scope / Trace
Phase 1 Dry Run 可执行
RUN-D004 暴露 Task vs Assurance 分离
Phase 1.1 v1.6 冻结协议已完成重放
G3 External Runner 到 VERIFY_COMPLETE / overall MERGE_READY
direct_machine_truth_mutation=true 被显式记录
```

但还不知道：

```text
G3 是否显著优于 G2
Integrity attacks 是否稳定被 BLOCK
Overhead 是否可接受
已有工具组合能否廉价替代
C#/Unity 是否有效
```

所以不能：

```text
CONTINUE unconditional
```

Phase 1.1 让“协议与最小机制”从未验证变成已验证，但没有回答 G3 相对 G2 的统计增益，
也没有执行攻击、经济性或跨领域验证。来源：`CLM-051`、`CLM-053`。

---

# 3. 当前为什么也不是 STOP

因为：

1. Agentic Change Assurance 问题本身是真实的；
2. 现有公开生态尚未在本次研究中显示出完全等价的统一 Change Acceptance System；
3. RUN-D004 已出现机制性信号；
4. V0.1 已有足够实现基础，可以低成本做 PoV 而不是从零构建。

来源：`INT-DEEP-RESEARCH-20260818`

因此当前：

```text
CONTINUE_BUT_NARROW — conditional
```

---

# 4. Gate 1 — Assurance Gain

先问：

> G3 = G2 + External AEH Assurance 后，是否出现明确增量？

指标：

```text
False Completion
Scope Violation
Test Mutation
Evidence Reproducibility
Task Success
Regression
```

如果：

```text
没有显著 Assurance Gain
```

进入：

```text
STOP / REPOSITION
```

---

# 5. Gate 2 — Integrity Attack

如果普通任务有增益，再问：

> A01–A08 能不能稳定被系统自身 BLOCK？

如果：

```text
Critical Escape
```

例如：

```text
改 Test 仍 MERGE_READY
伪造 Approval 仍 MERGE_READY
改 Validator Contract 仍 MERGE_READY
```

则：

```text
REPOSITION / CORE REDESIGN
```

不能靠继续加外围功能解决。

---

# 6. Gate 3 — Economics

如果 Assurance 和 Attack 都好，再问：

> 成本是否合理？

测：

```text
wall time
tokens
tool calls
human intervention
false escalation
repair burden
```

如果：

```text
增益小
成本大
```

优先：

```text
INTEGRATE
```

或：

```text
risk narrow
```

---

# 7. Gate 4 — Uniqueness

[DECISION] `ADR-HB-028`

构建一个替代组合：

```text
Coding Agent
+
AGENTS/Skills
+
OpenSpec / Spec Kit
+
Native Sandbox / Policy
+
normal CI
+
ProofAgent / existing governance
+
small glue
```

问：

> 能否用明显更低成本提供近似 Assurance？

如果 YES：

```text
INTEGRATE
```

不是：

```text
继续维护重复能力
```

---

# 8. Gate 5 — Cross-domain

Python Pilot 即使 PASS：

```text
还需要 C#/.NET
还需要 Unity / large brownfield
```

因为：

```text
test tooling
build system
repo size
generated assets
runtime verification
platform behavior
```

都不同。

如果：

```text
Python strong
Unity fails badly
```

可能 Verdict：

```text
CONTINUE_BUT_NARROW
```

而不是 CONTINUE。

---

# 9. 决策树

```text
                    PoV
                     │
          有明确 Assurance 增益？
              ┌──────┴──────┐
             NO             YES
             │               │
      STOP / REPOSITION    A01–A08
                             │
                      Critical escape?
                      ┌──────┴──────┐
                     YES            NO
                      │              │
             REPOSITION/REDESIGN   Economics
                                      │
                               acceptable?
                               ┌──────┴──────┐
                              NO             YES
                              │               │
                         INTEGRATE        Uniqueness
                                             │
                              existing stack cheaper/equal?
                                      ┌──────┴──────┐
                                     YES            NO
                                      │              │
                                 INTEGRATE       Cross-domain
                                                     │
                                              ┌──────┴──────┐
                                             FAIL           PASS
                                              │              │
                                  CONTINUE_BUT_NARROW    CONTINUE
```

---

# 10. Verdict 定义

## CONTINUE

条件：

```text
Assurance Gain strong
Attack Boundary strong
Economics acceptable
No cheap substitute
Cross-domain signal strong
```

意味着：

> AEH 的独立产品层基本成立。

---

## CONTINUE_BUT_NARROW

条件：

```text
Change Assurance 有价值
但只在部分 Risk / Domain / Repository 类型成立
```

行动：

```text
收紧 Core
减少低价值 Ceremony
只做高风险 Assurance
```

---

## INTEGRATE

条件：

```text
问题真实
但成熟生态组合已经能更便宜解决
```

行动：

```text
AEH 变成薄 Integration / Adapter
或贡献能力到现有系统
```

---

## REPOSITION

条件：

```text
某些机制有价值
但“独立 Change Assurance 产品”定位不成立
```

可能变成：

```text
CI verifier
test-integrity plugin
traceability tool
evaluation package
```

---

## STOP

条件：

```text
增益小
成本高
替代品成熟
核心 Attack 也不能可靠处理
```

停止不是失败。

它是：

> 证据驱动项目应有的正常结论。

---

# 11. 不允许的决策方式

### Feature Count

```text
AEH 有 30 个功能
别人只有 20 个
→ CONTINUE
```

无效。

### Sunk Cost

```text
已经写了很多代码
→ 必须继续
```

无效。

### Anecdote

```text
Dogfood 抓到一个真实 Bug
→ 已证明产品价值
```

不够。

### Architecture Beauty

```text
六平面很漂亮
→ 产品成立
```

无效。

---

# 12. 真正的 North Star Test

最终只问：

> # **如果删除 AEH，会失去哪一种其他层无法可靠提供的工程保证？**

当前最有希望的答案：

> **一种 vendor-neutral、在 Generator 权限之外可独立重算的 Change Acceptance Verdict：它验证冻结 Contract、Evidence Freshness、Oracle Integrity、Scope Integrity、Traceability 和 Verification Closure，并在证据不足时机器阻断。**

这仍然是：

```text
Hypothesis under evaluation
```

不是最终已证明事实。

---

# 13. 当前 Roadmap 应如何受决策框架约束

在 PoV 完成前：

## 继续

```text
PoV
External Validator correctness
Evidence integrity
Attack testing
Self CI / packaging reliability
```

## 暂停

```text
RAG
Memory
Web UI
General Multi-Agent
Own Sandbox
Large Spec Authoring
```

这就是：

```text
CONTINUE_BUT_NARROW
```

的实际含义。

---

# 14. 何时恢复 V0.2 M1

M1 的：

```text
relocatable wheel
AEH self CI
```

属于：

> Verifier 自身可信度基础设施。

因此即使继续 narrow，这两项大概率仍然合理。

Handbook v0.2 将 Phase 1.1 证据收口定义为 `V02-0 Design & Evidence Baseline`。
只有 V02-0 的 Registry、总稿、完整性清单和证据 closure 全部通过，M1 才进入独立
SPEC/PLAN；这不是 M1 已实现，也不是软件 `v0.2.0` 已发布。

但正式恢复时应明确：

```text
它们不是“扩大 AEH 产品边界”
```

而是：

```text
让当前验证核心更可部署、可回归
```

---

# 15. 决策必须有版本

最终裁决需要记录：

```yaml
decision:
  date:
  aeh_version:
  protocol_version:
  task_distribution:
  competitor_versions:
  evidence_refs:
  verdict:
  limitations:
```

因为 2026 的 Agent/Harness 生态变化很快。

今天的 Gap：

```text
未来可能被 Spec Kit / ProofAgent / native platform
快速填补。
```

所以：

> Strategic Verdict 也需要版本化。

---

# 16. 当前 Verdict

截至本手册 H5：

```yaml
problem_need:
  independent_change_assurance: HIGH_CONFIDENCE

market_gap:
  complete_vendor_neutral_change_assurance: PROVISIONAL

aeh_mechanism:
  technically_substantial: YES

aeh_product_efficacy:
  proven: NO

aeh_uniqueness:
  proven: NO

current_verdict:
  CONTINUE_BUT_NARROW_CONDITIONAL
```

---

# 17. 最终原则

> **Generator 可以越来越自由；Acceptance Authority 必须独立。**

但项目层面还需要第二句：

> **如果独立 Acceptance 可以由现有生态更便宜、更可靠地提供，AEH 就不应该为了自身存在而继续扩张。**

---

# 18. References

- `INT-DEEP-RESEARCH-20260818`
- `EVAL-P11-VERDICT-3267E8A`
- `EVAL-P11-RESULT-20260819`
- `EVAL-P1-PACKAGE-20260818`
- `EVAL-P1-D004-RAW`
- `EVAL-P0-USER-REPORTED-20260818`
- `EXT-PROOFAGENT`
- `EXT-GITHUB-SPEC-KIT`
- `EXT-OPENSPEC`
- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-ROADMAP-V02-6513102`
