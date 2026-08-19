# 19 · CI/CD 与团队工程化

> **章节类型**：BUILD / TARGET INTEGRATION  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **重要边界**：V0.1 **没有用户项目 CI 深集成**。本章必须区分“当前事实”与“推荐目标架构”。

---

# 1. 为什么本地 Validator 还不够

如果：

```text
Generator
和
AEH Validator
```

都运行在同一个本地 Workspace，并拥有近似 OS 权限，那么：

```text
Contract
Validator code
Artifacts
Repository files
```

的强边界仍有限。

本地 AEH 可以提供：

```text
工程检查
一致性
Fail-safe
```

但更强的 Acceptance Authority 需要：

> **在 Generator 权限之外重新计算。**

---

# 2. 当前事实

[AEH][FACT] V0.1 Known Limitations：

```text
No CI deep integration
No automatic merge / push / PR
AEH stops at MERGE_READY
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

因此本章不能描述：

```text
“当前 AEH 已经自动保护 GitHub Branch。”
```

那是不存在的能力。

---

# 3. 推荐的团队级 Trust Boundary

[DECISION] `ADR-HB-020`

```text
Developer / Coding Agent
        │
        │ candidate change
        ▼
Repository / PR
        │
        ▼
┌──────────────────────────────┐
│ Protected CI Environment     │
│                              │
│ clean checkout               │
│ install/pin AEH              │
│ verify manifest/contracts    │
│ recompute tests/hashes       │
│ validate trace/scope         │
└──────────────┬───────────────┘
               │
        Acceptance Verdict
        ┌──────┴──────┐
        ▼             ▼
    MERGE_READY      BLOCKED
        │
        ▼
SCM Branch Protection / Human Gate
        │
        ▼
      Merge
```

这里：

```text
AEH 产生工程 Verdict
SCM/Org 决定真正 Merge
```

---

# 4. 为什么 AEH 应停止在 MERGE_READY

如果 AEH 自己同时：

```text
验证
批准
push
merge
release
```

它会积累过多 Authority。

更清晰：

```text
AEH:
Is this Change acceptable?

SCM:
Can/should it be merged?

Release system:
Can/should it be deployed?
```

来源：`AEH-README-6513102`

---

# 5. CI 需要冻结哪些输入

为了可复现，CI 至少要记录：

```text
repository commit
AEH version
AEH source revision
runtime digest
schema version
test environment
dependency lock state
platform
command / argv
timeout
network/sandbox policy
```

这与 PoV 对 Eval Environment 的冻结原则一致。

---

# 6. Clean Checkout 的意义

本地 Workspace 可能有：

```text
untracked file
stale temporary state
local configuration
modified runtime
```

CI 使用：

```text
clean checkout
```

可以显著增强：

```text
reproducibility
tamper resistance
environment separation
```

但仍要注意：

> CI 本身也需要可信配置和权限。

---

# 7. Manifest 在 CI 中的作用

CI 可以检查：

```text
manifest.source_revision
manifest.source_hashes.runtime
manifest.compiler.version
manifest.schema.version
```

来源：`AEH-SCHEMA-MANIFEST-6513102`

然后重算当前：

```text
.aeh/runtime
```

Digest。

Doctor 当前已经有这种 Runtime Integrity Check。

来源：`AEH-RUNTIME-DOCTOR-6513102`

---

# 8. CI Gate 不等于重新写一套 AEH

错误：

```text
Local AEH has rules A
CI workflow manually reimplements rules B
```

正确：

```text
同一个 Machine Contract / Validator
在更可信的执行边界重新运行
```

否则会产生：

```text
two sources of truth
```

---

# 9. Self CI 与 User Project CI

V0.2 Roadmap DRAFT 区分：

```text
AEH 自身 CI
```

和：

```text
用户项目 CI 深集成
```

来源：`AEH-ROADMAP-V02-6513102`

这两个问题不同。

### AEH Self CI

证明：

```text
AEH 自己的代码修改没有破坏 AEH。
```

### User Project CI

证明：

```text
某个使用 AEH 的项目 Change，
在外部环境仍然满足 Assurance。
```

---

# 10. 为什么 M1 自身 CI 仍值得做

即使 AEH 暂停横向功能扩张：

```text
CI
wheel
clean-room
```

仍属于：

> **让 Validator 自己可信的基础设施。**

不是新的 Product Plane。

---

# 11. Branch Protection 的理想组合

未来可以：

```text
required status check:
  AEH Assurance PASS

required human review:
  according to risk

protected branch:
  no direct push
```

这些属于 SCM / Organization Governance。

AEH 应提供：

```text
machine result
evidence references
stable exit code
artifact bundle
```

而不是替代 GitHub/GitLab 权限系统。

---

# 12. Approval Identity

当前：

```text
actor.id string
```

只是 attestation。

来源：`AEH-KNOWN-LIMITATIONS-6513102`

团队级 CI 中应优先消费：

```text
SCM identity
OIDC claims
signed attestation
enterprise IAM
```

而不是让 AEH 自己维护账号密码。

---

# 13. Failure Modes

### FM-CI-01 — CI Only Runs Tests

```text
tests PASS
→ merge
```

但不验证：

```text
test lock
scope
trace
stale evidence
```

这不是完整 Change Assurance。

---

### FM-CI-02 — CI Trusts Generated Verdict File

```text
verification.yaml says MERGE_READY
→ accept
```

却不重算。

这仍然把 Acceptance Authority 留给 Artifact Writer。

---

### FM-CI-03 — CI Drift

本地 Validator 版本与 CI 版本不同，但没有 Manifest/Version pin。

可能产生：

```text
local PASS
CI BLOCK
```

或反之。

必须记录版本来源。

---

# 14. Architecture Invariants

### CI-INV-01

> **Protected CI SHOULD recompute assurance rather than merely trust locally generated verdict files.**

### CI-INV-02

> **AEH SHOULD stop at an acceptance verdict; merge/push/release authority remains external.**

### CI-INV-03

> **CI configuration, AEH revision and repository revision MUST be sufficient to explain which rules produced a verdict.**

### CI-INV-04

> **The same normative contracts SHOULD govern local and CI validation to avoid semantic drift.**

---

# 15. 当前与目标边界

## 当前 V0.1

```text
Local CLI
Local Doctor
Local Runtime Verify
MERGE_READY
No deep CI
```

## 目标候选

```text
Local checks
+
protected CI recomputation
+
SCM required check
+
external approval identity
```

后者仍需实现与实验验证。

---

# 16. References

- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-README-6513102`
- `AEH-SCHEMA-MANIFEST-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`
- `AEH-ROADMAP-V02-6513102`
