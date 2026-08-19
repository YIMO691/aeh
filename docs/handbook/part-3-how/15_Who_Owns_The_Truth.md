# 15 · Who Owns The Truth?

> **章节类型**：HOW / ARCHITECTURE CORE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **这是本手册最重要的架构章节之一。**

---

## 1. 核心问题

如果一个 Agent 同时可以：

```text
定义需求
定义测试
修改实现
修改测试
修改 Evidence
修改 Gate
写 Approval
最后宣布 COMPLETED
```

那么即使整个流程拥有 YAML、Schema、State Machine、Tests，也可能仍然没有真正的独立 Assurance。

因此 AEH 最核心的问题不是“机器真值放在哪个 YAML”，而是：

> # **谁有权修改真值？谁有权判定真值？**

## 2. File Format 不创造 Authority

错误理解：

```text
Markdown 不可信
YAML 可信
```

并不是这样。普通 Agent 同样可以写：

```yaml
state: DONE
gate: PASS
approval: APPROVED
```

YAML 本身没有安全属性。

真正结构是：

```text
Machine-readable Contract
+ Trusted Mutation Boundary
+ Independent Validator
+ Integrity / Replay
= Authoritative Engineering State
```

[DECISION] `ADR-HB-016`。

## 3. AEH V0.1 已冻结 Trusted Mutation Boundary

V0.1 Architecture P-21 规定：

```text
.aeh/runtime/core/**       → Bootstrap / Upgrade trusted path
.aeh/runtime/schemas/**    → Bootstrap / Upgrade trusted path
manifest.yaml              → Installer / Compiler
profile.yaml               → Profile Compiler
effective-workflow.yaml    → Workflow Compiler
approvals APPROVED         → Trusted Human Approval Path
change.yaml.state          → State Transition / Validator-mediated path
spec.yaml                  → SPEC / SPEC_REPAIR
test files                 → RED / TEST_REPAIR；GREEN 只读
production code            → GREEN / REFACTOR allowlist
verification.yaml          → VERIFY path
```

来源：`AEH-ARCH-6513102`。

这已经非常接近 Change Assurance 的核心思想。

## 4. Generator 应该拥有什么

Generator 是工作执行者，可以拥有：

```text
Reasoning
Search
Implementation
Allowed production writes
Temporary files
Tool usage within policy
```

也就是：

```text
Generator can propose reality.
```

但不应该独立拥有：Final gate truth、Approval authority、Frozen oracle mutation、Validator contracts、Final acceptance verdict。

## 5. Acceptance Authority 应该拥有什么

Acceptance Authority 不一定是一个人，可以由 AEH Validator、CI、SCM protected branch rule、Human approval、Formal prover、Policy engine 组合形成。

核心不是实体名字，而是：

> **它处于被验证 Generator 的权限之外，并能够基于可信状态重算 Acceptance。**

## 6. 三层 Truth

### T1 — Claimed Truth

Agent 自己说：`COMPLETED / tests pass / scope respected`。

### T2 — Recorded Truth

文件里有：`green.yaml / verification.yaml / change.yaml`。

### T3 — Authoritative Truth

外部机制确认：这些文件来自正确路径、Hash/State 一致、实际 Tests 可重跑、Scope 一致、Trace 完整、Approval 来源满足要求。

只有 T3 才能作为最终 Acceptance。

## 7. RUN-D004 为什么重要

[EVAL] RUN-D004：Agent 写入 `.aeh` artifacts、没有调用 AEH CLI、声称 COMPLETED，且 Task Tests PASS；但 External Validator Replay 得到 `BLOCKED_CHANGE_STATE`。来源：`EVAL-P1-D004`。

这说明：

```text
Recorded Truth != Authoritative Truth
```

这是目前 PoV 最重要的机制性发现。

## 8. Generator 不是“敌人”

Trusted Mutation Boundary 不是基于“AI 会故意作弊”。同样原则适用于人类开发者、Build Script、CI Job、Plugin、Compromised Tool、Buggy Automation。

工程上分权的目的不是怀疑人格，而是：

> **减少一个组件错误时能够同时破坏对象和裁判的机会。**

## 9. Test Oracle 的 Ownership

Generator 在 Test Design 阶段可以帮助创建 Oracle；但进入实现阶段后，Oracle ownership 应从“可编辑工作资产”转换为“受控验收资产”。

这就是：

```text
VALID_RED → LOCK_TEST
```

的真正意义。来源：`AEH-RUNTIME-RED-6513102`、`AEH-RUNTIME-GREEN-6513102`。

## 10. Scope 的 Ownership

Scope 不应该由 Generator 在事后无限扩张。正确模型：

```text
Contract / Grounding / Human
→ establish allowed scope

Generator
→ writes inside scope

Validator
→ compares actual mutation
```

如确需扩 Scope，应走 Scope Repair / Contract Revision，而不是“我需要，所以我改了”。

## 11. Approval 的 Ownership

V0.1 Schema 对 APPROVED 要求 `actor.type = human`。来源：`AEH-SCHEMA-APPROVAL-6513102`。

但 actor 当前仍只是 attestation。来源：`AEH-README-6513102`。

所以长期 Approval Authority 应由外部 Identity / SCM / CI 证明，AEH 消费其结果，而不是自己变成企业 IAM。

## 12. Validator 的 Ownership

Validator 自己也必须被保护，否则：

```text
Agent 修改 Validator
→ 新 Validator 说 Agent PASS
```

P-21 要求关键 Gate 前检查 runtime/core/schema 与 manifest digest/source manifest 的一致性。来源：`AEH-ARCH-6513102`。

这相当于：

> **不能让被验证对象换掉裁判规则，再继续审判。**

## 13. Schema 的正确角色

```text
Schema    → 定义数据结构是否合法
Validator → 判断当前真实状态是否满足 Contract
Trusted Mutation Boundary → 控制谁能改变关键状态
```

因此：

```text
Schema ≠ Enforcement
```

V0.1 P-02 已明确冻结。来源：`AEH-ARCH-6513102`。

## 14. Authority Matrix

| Asset / Decision | Generator | AEH Validator | Human/Org | Native Runtime |
|---|---:|---:|---:|---:|
| 搜索/推理 | Primary | No | Input | Tools |
| 生产代码实现 | Authorized | Verify | May constrain | Enforce capability |
| Spec proposal | Can assist | Validate | Own intent | — |
| Test proposal | Can assist | Validate | May review | — |
| Frozen Oracle | No unilateral mutation | Verify | Repair authority | May enforce RO |
| Scope expansion | No unilateral | Verify | Authorize | May enforce |
| Evidence claim | Produce candidate | Verify | May attest | Produce logs |
| Gate truth | No | Primary | Policy input | — |
| Approval | No | Validate | Primary | — |
| MERGE_READY | No | Compute | May add governance | — |
| Actual merge | No by AEH contract | No | SCM/Org | SCM |

## 15. “独立”不等于“完全不同进程”

独立性的核心是 Authority，而不一定是进程拓扑。同一个 CLI 进程也可以读取受保护输入并执行 deterministic validator，只要 Generator 无法修改 Validator、Contract、Frozen Input 或伪造外部身份。

所以：

```text
Independent
= Authority-separated and independently recomputable
```

不一定等于 `always separate server`。

## 16. CI 为什么最终重要

本地 AEH 可以验证 Change，但如果 Generator 与本地 Workspace 拥有相同 OS 权限，最终 Trust Boundary 仍有限。

更强模式：

```text
Developer / Agent
    ↓ pushes candidate
Protected CI
    ↓ clean checkout
AEH verify
    ↓
SCM branch protection
```

这样 Acceptance Authority 进一步移出本地 Generator 环境。

V0.2 roadmap 中 AEH self CI 与 user-project CI integration 因此具有长期价值。来源：`AEH-ROADMAP-V02-6513102`。

## 17. Architecture Invariants

### TRUTH-INV-01
> **Machine-readable format alone does not create authority.**

### TRUTH-INV-02
> **The Generator MUST NOT have unilateral write authority over all inputs and outputs used to establish final acceptance.**

### TRUTH-INV-03
> **Acceptance-critical state transitions MUST be validator-mediated or externally recomputable.**

### TRUTH-INV-04
> **Validator rules and contracts MUST themselves be integrity-protected.**

### TRUTH-INV-05
> **Human approval MUST be treated as authority evidence, not as a mechanism to override deterministic technical failure.**

## 18. 当前最大未决问题

PoV 需要证明当前 Trusted Mutation Boundary 是真正 Enforcement，还是主要依赖 Agent 遵守 Guidance，尤其是：

```text
A01 Test Mutation
A02 Gate Forgery
A03 Evidence Forgery
A07 Approval Forgery
A08 Contract Tamper
```

只有这些正式 Attack 结果出来后，才能评价 AEH Authority Boundary 到底有多硬。

## 19. References

- `AEH-ARCH-6513102`
- `AEH-SCHEMA-APPROVAL-6513102`
- `AEH-RUNTIME-RED-6513102`
- `AEH-RUNTIME-GREEN-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `AEH-ROADMAP-V02-6513102`
- `AEH-README-6513102`
- `EVAL-P1-D004`
