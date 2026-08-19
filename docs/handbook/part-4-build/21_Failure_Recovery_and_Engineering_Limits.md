# 21 · Failure Recovery 与工程限制

> **章节类型**：BUILD / HONEST LIMITS  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **核心原则**：Known Limitations 不是附录里的“免责声明”，而是 Architecture Input。

---

# 1. 为什么这一章必须是一等章节

一个治理/验证系统最危险的写法是：

```text
只介绍它能拦什么
不介绍它拦不住什么
```

AEH 的价值来自：

> **诚实描述 Assurance Strength。**

所以：

```text
Known Limitations
```

不能藏在 README 最后。

必须直接影响：

```text
产品定位
Risk
Doctor
Adapter
PoV
Roadmap
```

[DECISION] `ADR-HB-022`

---

# 2. V0.1 Release Known Limitations

截至固定基线 `6513102`，官方 release limitation 共 13 项。

来源：`AEH-KNOWN-LIMITATIONS-6513102`

---

# 3. L1 — Human Approval 不是强身份

当前：

```text
actor.id string
human attestation
```

没有：

```text
OIDC
IAM
signature
approval TTL
```

因此：

```text
Approval Integrity
<
Enterprise Identity Assurance
```

手册必须避免：

> “AEH 已确认某个真实人类批准。”

正确：

> “AEH 记录了一份 human attestation。”

---

# 4. L2 — 部分 Adapter 能力是 GUIDANCE_ONLY

例如：

```text
Codex git_push deny
Claude web_access deny
review.human_required_for
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这意味着：

```text
instruction
≠
hard platform control
```

Doctor/Adapter 的价值之一就是不隐藏这一事实。

---

# 5. L3 — Bootstrap 不是仓库级事务

当前：

```text
stage
validate
per-file replace
rollback-capable
```

但不是：

```text
all-or-nothing repository transaction
```

崩溃/进程终止仍可能留下：

```text
.aeh-tmp
.aeh-rollback
partial install
```

Doctor 会检测 residue，但不会修。

来源：

- `AEH-RUNTIME-BOOTSTRAP-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`
- `AEH-KNOWN-LIMITATIONS-6513102`

---

# 6. L4 — Command String Compatibility Path 与无 OS Sandbox

Known Limitations：

```text
free-form command string
→ compatibility shell=True

argv
→ preferred

no OS sandbox
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这说明：

> AEH 的 Test/Verify Runner 不是安全隔离环境。

更长期策略仍应：

```text
Native Sandbox Integration
```

而不是把自己的 subprocess wrapper 宣传成 Sandbox。

---

# 7. L5 — No Repair / Recover

当前 Doctor 可以发现：

```text
runtime digest mismatch
managed marker malformed
install residue
```

但没有：

```text
aeh repair
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这意味着用户需要：

```text
manual review / re-bootstrap
```

恢复能力应独立实现：

```text
diagnose
→ repair plan
→ dry-run
→ apply
→ journal
→ rollback
→ doctor verify
```

---

# 8. L6 — No Upgrade System

Manifest 已为：

```text
version
source_revision
digest
```

提供基础。

但：

```text
aeh upgrade
```

尚未实现。

来源：`AEH-KNOWN-LIMITATIONS-6513102`

因此不同 AEH 版本间 Contract Migration 仍是开放问题。

---

# 9. L7 — No Deep CI Integration

当前 Acceptance 主要发生在本地 CLI。

这限制：

```text
authority separation
reproducibility
protected enforcement
```

但 CI 不是简单加一个 YAML Workflow 就结束。

还涉及：

```text
resource packaging
clean install
version pin
artifact upload
branch protection
identity
```

---

# 10. L8 — No Automatic Merge / Push / PR

这既是限制，也是合理边界。

AEH：

```text
MERGE_READY
```

之后：

```text
merge
push
PR
release
```

属于外部系统。

来源：`AEH-KNOWN-LIMITATIONS-6513102`

本手册建议保留这一边界。

---

# 11. L9 — No Multi-Agent Orchestrator

这不是当前 Change Assurance 核心缺陷。

如果未来需要：

```text
Planner
Generator
Reviewer
```

可以由外部 Agent Runtime 编排。

AEH 只需要：

```text
验证最终 Change
记录各 Evidence producer
```

除非 PoV 证明 Multi-Agent Authority 本身需要 AEH 特定能力。

---

# 12. L10 — Manual Verification Pending

V0.1 manual verification：

```text
PENDING
```

并阻塞 VERIFY。

来源：

- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-RUNTIME-VERIFY-6513102`

这比伪造自动 PASS 更诚实。

但未来需要更好的：

```text
manual evidence
approval linkage
identity
expiry
```

---

# 13. L11 — Editable Install Only

当前：

```text
pip install -e .
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

`pyproject.toml` 只发现：

```text
src/aeh*
```

没有把：

```text
core/
schemas/
bootstrap/
adapters/
```

声明为 package data。

来源：`AEH-PYPROJECT-6513102`

因此 Relocatable Wheel 是基础设施缺口。

---

# 14. L12 — Keyword Risk Escalation 是 Heuristic

Keyword Hint：

```text
reward
payment
db
permission
...
```

用于 fail-safe escalation。

来源：`AEH-CORE-CLASSIFICATIONS-6513102`

风险：

```text
false positive
```

会增加 Friction。

但不能用 Keyword Miss：

```text
自动降级高风险 Change
```

---

# 15. L13 — Grounding Hard Escalation 与 Test Plan

如果 Grounding 后升级为 CRITICAL：

```text
Test Plan
必须补 integration/contract verification
```

否则 VERIFY 会 BLOCK。

来源：

- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-RUNTIME-VERIFY-6513102`

这体现：

> Risk 可以在证据增加后动态升级。

---

# 16. Failure Recovery Taxonomy

建议长期把失败分为：

```text
F1 User/Task Failure
  requirement incomplete
  invalid test
  code failure

F2 Environment Failure
  tool missing
  dependency missing
  timeout

F3 Assurance Failure
  test changed
  scope escape
  stale evidence
  trace incomplete

F4 Harness Integrity Failure
  runtime digest mismatch
  schema tamper
  install residue

F5 Governance Failure
  approval missing
  identity weak
  policy conflict

F6 Infrastructure Failure
  CI outage
  disk failure
  network failure
```

不同 Failure 不应该都统一成：

```text
“重新跑一下”
```

---

# 17. Fail-safe 与 Fail-open

对于 Acceptance-critical 问题：

```text
unknown contract integrity
unknown approval
stale evidence
test mutation
```

默认应：

```text
BLOCK
```

对于非关键可选能力：

```text
某个额外检查 unavailable
```

可以按 Risk：

```text
WARN
```

但必须在 Verdict 中暴露。

---

# 18. Recovery 的基本原则

### REC-INV-01

> **Diagnosis and repair MUST be separate authorities.**

### REC-INV-02

> **Repair MUST be plan-first, auditable and rollback-aware.**

### REC-INV-03

> **A failed or uncertain Harness Integrity check MUST NOT be repaired by silently accepting the current state.**

### REC-INV-04

> **Known limitations MUST flow into risk classification, user-visible diagnostics and product claims.**

---

# 19. 当前测试基线不是生产证明

Release：

```text
232 / 232 PASS
```

来源：`AEH-RELEASE-TEST-6513102`

这是重要工程证据。

但不能推出：

```text
所有 OS PASS
大型 Unity PASS
企业 CI PASS
所有攻击 PASS
```

这些属于后续：

```text
PoV
Cross-domain
Adversarial
Infrastructure hardening
```

---

# 20. 当前最重要的工程化优先级

在“不横向扩张”原则下，仍值得优先补的是：

```text
relocatable packaging
AEH self CI
clean-room regression
repair/recovery
CI acceptance integration
```

因为这些提升的是：

> **Verifier 自己的可信度与可部署性。**

而不是把 AEH 变成新的 Agent 平台。

---

# 21. References

- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-RUNTIME-BOOTSTRAP-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `AEH-PYPROJECT-6513102`
- `AEH-CORE-CLASSIFICATIONS-6513102`
- `AEH-RELEASE-TEST-6513102`
- `AEH-ROADMAP-V02-6513102`
