# 07 · AEH 总体架构

> **章节类型**：HOW  
> **状态**：H2_ARCHITECTURE_SKELETON  
> **注意**：本章首先定义概念架构；源码文件级映射将在 H3/H4 中定点补证。

---

# 1. 本章解决什么问题

在明确：

```text
AEH = Change Assurance
```

之后，需要回答：

> 一个 Change Assurance System 内部到底需要哪些责任组件？

本章不按：

```text
change.py
doctor.py
approval.py
```

逐文件解释。

因为文件布局会变化。

本章按长期责任组织：

```text
Change Contract Engine
Evidence Engine
Integrity Engine
Traceability Engine
Risk / Governance Engine
External Validator
```

---

# 2. 总体结构

```text
                      Change Intent
                           │
                           ▼
                ┌────────────────────┐
                │ Change Contract    │
                │ Engine             │
                └─────────┬──────────┘
                          │
                normalized contract
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
┌────────────────┐ ┌──────────────┐ ┌────────────────┐
│ Evidence Engine│ │Integrity     │ │Risk/Governance │
│ provenance     │ │Engine        │ │Engine          │
│ freshness      │ │oracle/scope  │ │depth/approval  │
└───────┬────────┘ └──────┬───────┘ └───────┬────────┘
        │                 │                 │
        └──────────┬──────┴─────────┬───────┘
                   │                │
                   ▼                ▼
         ┌────────────────┐ ┌────────────────┐
         │ Traceability   │ │External        │
         │ Engine         │ │Validator       │
         └───────┬────────┘ └───────┬────────┘
                 │                  │
                 └────────┬─────────┘
                          ▼
                   Assurance Verdict
                  /                  \
          MERGE_READY              BLOCKED
```

---

# 3. Change Contract Engine

## 3.1 职责

回答：

> **当前 Validator 到底在验证什么？**

Contract 至少需要表达：

```text
Change ID
Risk
Requirements
Acceptance Criteria
Constraints
Allowed scope
Required verification
Approval requirements
```

Spec 可以来自：

```text
OpenSpec
Spec Kit
Issue
PRD
Native AEH minimal spec
```

Contract Engine 的目标不是替代这些 Authoring Tool，而是转成 AEH 可验证的规范化 IR。

---

## 3.2 Architecture Invariant

[NORMATIVE]

> **Validator 不得依赖只有自然语言、没有稳定 ID 和结构的关键 Acceptance 条件。**

这不意味着所有内容必须 YAML 化。

只意味着：

> 参与机器 Gate 的事实必须有机器可判定表示。

AEH V0.1 P-05 已规定核心机器真值使用 YAML/JSON + Schema，Markdown 不能成为唯一 Gate 真值。

来源：`AEH-ARCH-6513102`

---

# 4. Evidence Engine

## 4.1 职责

Evidence Engine 不只是“存日志”。

它管理：

```text
Provenance
Freshness
Hash
Command result
Environment
Output reference
Replay inputs
```

回答：

```text
这个事实是谁观察的？
基于什么代码版本？
证据后来是否失效？
我能不能重新检查？
```

---

## 4.2 Evidence Presence vs Validity

必须区分：

```text
artifact_present = true
```

和：

```text
evidence_valid = true
```

[EVAL] Phase 1 RUN-D004 已经暴露：

```text
.aeh artifacts present
但
external validator replay = BLOCKED_CHANGE_STATE
```

来源：`EVAL-P1-D004`

因此：

[NORMATIVE]

> **Evidence Engine MUST NOT infer trust from file existence.**

---

# 5. Integrity Engine

Integrity Engine 是 AEH 差异化最强的候选组件。

它至少包含：

```text
Oracle Integrity
Scope Integrity
Artifact Integrity
Machine Truth Integrity
```

---

## 5.1 Oracle Integrity

回答：

> 实现者有没有改变“什么叫正确”？

典型机制：

```text
VALID_RED
→ hash/freeze oracle
→ implementation
→ compare oracle
```

AEH V0.1 已冻结：

```text
VALID_RED → LOCK_TEST → GREEN
```

来源：`AEH-ARCH-6513102`

如果测试在 GREEN 阶段变化：

```text
BLOCKED_TEST_CHANGED
```

---

## 5.2 Scope Integrity

回答：

```text
authorized paths
vs
actual diff
```

这不是 Sandbox 替代品。

Sandbox 限制技术能力。

Scope Integrity 限制 Change 合法性。

---

## 5.3 Artifact Integrity

AEH 的：

```text
runtime/core
schemas
manifest
profile
effective-workflow
approval
state
verification
```

本身也是攻击面。

因此 V0.1 P-21 建立了 Trusted Mutation Boundary。

来源：`AEH-ARCH-6513102`

---

# 6. Traceability Engine

Traceability Engine 建立：

```text
REQ
→ AC
→ TEST
→ CODE
→ VER
```

它有两个方向。

## 6.1 Forward Trace

```text
REQ-001
最终由什么代码实现？
由哪些 Tests 验证？
```

## 6.2 Backward Trace

```text
这段 Code / Test
服务哪条 Requirement？
还是 Agent 自己扩 Scope？
```

Traceability 不是所有低风险 Change 都要同样深。

它应受 Risk Engine 控制。

---

# 7. Risk / Governance Engine

## 7.1 为什么需要 Risk

如果：

```text
改一个注释
```

和：

```text
修改支付/奖励/持久化
```

都要求完整：

```text
Ground
Spec
RED
Lock
Trace
Human Approval
```

AEH 会变成工程税。

V0.1 已存在：

```text
DIRECT
LIGHTWEIGHT
STANDARD
CRITICAL
EXPLORE
```

来源：`AEH-README-6513102`

当前手册保留“风险分层”原则，但不把具体五级命名视为永久架构。

---

## 7.2 Governance

高风险 Change 可以增加：

```text
deeper evidence
integration verification
contract verification
approval
stricter traceability
```

低风险 Change 可以降低仪式成本。

---

# 8. External Validator

这是整个 AEH 的核心。

Validator 不是：

```text
读取 Agent 写的 PASS
```

而是：

```text
读取 Contract
读取可信 Evidence
读取实际 Repo 状态
重算 Hash / Diff / Test / Trace
检查 Authority
产生 Verdict
```

AEH V0.1 架构中明确：

```text
Schema 定义合法性
Validator 独立执行判定
```

来源：`AEH-ARCH-6513102`

---

# 9. Machine Truth 与 Trusted Mutation Boundary

一个系统即使有 Schema，也可能没有真正 Enforcement。

如果 Agent 能：

```text
把 change.yaml.state 改成 DONE
把 verification.yaml 改成 PASS
把 approvals.yaml 改成 APPROVED
```

Validator 又直接读取这些值：

> Validator 只是“读一个自报结果”。

因此：

```text
Machine Truth
+
Validator
+
Trusted Mutation Boundary
=
Enforcement
```

这已经是 AEH V0.1 P-21 的冻结原则。

来源：`AEH-ARCH-6513102`

---

# 10. Runtime Flow

概念流：

```text
1. Change Created

2. Establish Contract
   Intent → normalized Requirement / AC / constraints

3. Establish Evidence
   Grounding / source facts / provenance

4. Establish Oracle
   Test design → VALID RED

5. Freeze Critical Truth
   test/oracle lock
   change scope
   contract revision

6. Generator Implements

7. Recompute Integrity
   tests unchanged?
   scope respected?
   artifacts intact?

8. Verify Outcome
   GREEN / regression / declared verification

9. Close Trace
   REQ→AC→TEST→CODE→VER

10. External Acceptance
   MERGE_READY / BLOCKED
```

---

# 11. AEH 内部五层架构与本章概念组件的关系

V0.1 冻结架构：

```text
Core
Bootstrap
Project Profile
Adapter
Runtime
```

来源：`AEH-ARCH-6513102`

它与本章：

```text
Contract Engine
Evidence Engine
Integrity Engine
Traceability Engine
Risk Engine
External Validator
```

不是竞争关系。

前者回答：

> 代码/配置应该放在哪一层？

后者回答：

> 系统有哪些长期责任？

例如：

```text
Integrity Engine
可能由：
Core contract
+ schemas
+ Runtime validator
共同实现。
```

所以后续源码导读必须同时提供：

```text
Conceptual responsibility
→ Concrete package/module mapping
```

---

# 12. Failure Modes

## FM-01 Agent Self-report Accepted

错误：

```text
Agent says PASS
→ system PASS
```

正确：

```text
Agent claim
→ evidence
→ validator recompute
→ verdict
```

---

## FM-02 Artifact Existence = Trust

错误：

```text
verification.yaml exists
→ VERIFIED
```

正确：

```text
provenance
+ authorized writer
+ schema
+ actual state replay
→ VALID / INVALID
```

---

## FM-03 Validator Rule Tamper

错误：

```text
Agent changes validator/schema
→ new rules say PASS
```

正确：

```text
manifest/digest check
→ BLOCKED_CONTRACT_TAMPER
```

---

## FM-04 Over-governance

错误：

```text
Every change = CRITICAL workflow
```

正确：

```text
Risk-based Assurance
```

---

# 13. 当前实现状态

[AEH][FACT]

V0.1 已实现/公开声明覆盖：

```text
bootstrap
doctor
change lifecycle
ground
spec
test-design
red
green
refactor
verify
approve
review
evidence model
test lock
traceability
risk-based verification
Codex / Claude adapters
```

来源：`AEH-README-6513102`

但本章不会在尚未进行源码逐模块复核前，宣称所有概念组件已经达到完整生产强度。

特别是：

```text
strong identity
deep CI
OS sandbox
repair/upgrade
```

仍属于已知限制或后续候选。

---

# 14. References

- `AEH-ARCH-6513102`
- `AEH-README-6513102`
- `EVAL-P1-D004`
- `INT-DEEP-RESEARCH-20260818`
