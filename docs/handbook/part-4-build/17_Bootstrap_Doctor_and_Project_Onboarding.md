# 17 · Bootstrap、Doctor 与项目接入

> **章节类型**：BUILD  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **核心问题**：AEH 如何安全进入一个已有仓库，并确保后续 Validator 不是在一套损坏或被篡改的 Contract 上工作？

---

## 1. Bootstrap 与 Doctor 是两个完全不同的能力

```text
Bootstrap
= 有意写入 / 安装

Doctor
= 只读观察 / 验证 / 诊断
```

[DECISION] `ADR-HB-018`

不能让 Doctor：

```text
发现问题
→ 自动修改
```

否则 Health Check 与 Repair Authority 混在一起。

---

# 2. Bootstrap 的目标

Bootstrap 不是简单复制几个模板。

它把：

```text
AEH public repository
+
project facts
+
answers / policy inputs
```

编译为：

```text
.aeh/manifest.yaml
.aeh/profile.yaml
.aeh/effective-workflow.yaml
.aeh/runtime/
managed AGENTS.md
managed CLAUDE.md
```

从而建立：

> **项目级 Change Assurance Contract Layer。**

---

# 3. `--dry-run` 是安装安全边界

[AEH][FACT] Bootstrap 支持：

```text
--dry-run
```

其注释明确：

```text
完整计算 + Install Plan + 零写盘
```

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

正确的修改型安装工具应优先：

```text
Plan
→ inspect
→ apply
```

而不是：

```text
run
→ hope
```

---

# 4. Install Plan

V0.1 Install Plan Schema 允许：

```text
CREATE
REPLACE_MANAGED_SECTION
UPDATE_GITIGNORE
INSTALL_RUNTIME
NOOP
```

每个 operation 至少记录：

```text
action
path
reason
```

并可记录：

```text
content_hash
kind
```

来源：`AEH-SCHEMA-INSTALL-PLAN-6513102`

Path Schema 还拒绝：

```text
absolute Windows drive path
../ traversal
```

这是基本的安装路径安全。

---

# 5. Semantic Hash 与幂等性

Bootstrap 中的 `semantic_hash` 会剔除：

```text
scanned_at
answered_at
installed_at
recompiled_at
```

再计算语义 Hash。

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

目的：

```text
相同语义输入
不应该因为时间戳变化
制造无意义 diff
```

这是 Repo-native 工具很重要的品质。

---

# 6. Manifest 首装时间

代码明确：

```text
installed_at 仅首次安装写入
```

已有安装重复 Bootstrap 时，不应因为时间刷新重写 Manifest。

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

长期仍应区分：

```text
installed_at
recompiled_at
upgraded_at
```

但只有实际发生对应语义变化才应该更新。

---

# 7. Runtime Snapshot 与 Digest

Bootstrap 安装：

```text
.aeh/runtime/core/*
.aeh/runtime/schemas/*
```

并计算 source hashes：

```text
runtime
compiler
bootstrap_contract
adapters
```

来源：

- `AEH-RUNTIME-BOOTSTRAP-6513102`
- `AEH-SCHEMA-MANIFEST-6513102`

之后项目可以回答：

```text
“当前裁判规则来自哪里？”
```

---

# 8. Adapter Managed Section

Bootstrap 不应该覆盖已有：

```text
AGENTS.md
CLAUDE.md
```

Adapter 使用：

```text
<!-- AEH:BEGIN MANAGED -->
...
<!-- AEH:END MANAGED -->
```

仅替换自己的 managed block。

来源：

- `AEH-RUNTIME-ADAPTER-6513102`
- `AEH-RUNTIME-BOOTSTRAP-6513102`

如果 marker malformed：

```text
MALFORMED_MANAGED_MARKERS
```

而不是静默覆盖用户原文。

---

# 9. Private Policy Boundary

Bootstrap 创建：

```text
.aeh/private/
```

并把：

```text
.aeh/private/
```

加入 `.gitignore`。

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

架构目标：

```text
Private Source
→ normalize
→ effective constraint
→ agent sees minimum necessary result
```

而不是把组织制度正文复制进：

```text
AGENTS.md
logs
public evidence
```

---

# 10. Apply 的真实原子性

Bootstrap 当前实现：

```text
stage
→ validate
→ per-file temp write
→ os.replace
→ journal in memory
→ failure rollback
```

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

这是：

```text
rollback-capable
```

但不是：

```text
repository-wide atomic transaction
```

Known Limitations 明确写出了这一点。

来源：`AEH-KNOWN-LIMITATIONS-6513102`

因此手册不得写：

> “Bootstrap 是完全原子的。”

正确说法：

> **单文件替换采用原子 replace，批量安装发生失败时尝试回滚，但整个仓库不是一个 ACID 事务。**

---

# 11. Bootstrap Post-Validation

Apply 后会检查：

```text
manifest schema
profile schema
effective-workflow schema
profile not BLOCKED
runtime digest
```

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

失败不能返回：

```text
BOOTSTRAP_COMPLETE
```

这是：

```text
fail-safe install
```

的最低要求。

---

# 12. Doctor 的角色

Doctor 的源文件开头直接冻结：

```text
只读
不写 .aeh/
不修改用户文件
不自动修复
无网络
```

来源：`AEH-RUNTIME-DOCTOR-6513102`

Doctor 的输出：

```text
READY
READY_WITH_WARNINGS
BLOCKED
```

Schema 同时要求每个 Check 有：

```text
check_id
domain
status
message
```

并可带：

```text
evidence
remediation
```

来源：`AEH-SCHEMA-DOCTOR-6513102`

---

# 13. Doctor 的检查域

## Install

检查：

```text
.aeh/
manifest
profile
effective-workflow
runtime/
```

缺失：

```text
BLOCKED
```

---

## Incomplete Install

扫描：

```text
.aeh-tmp
.aeh-rollback
```

残留。

发现：

```text
BLOCKED_INCOMPLETE_INSTALL
```

Doctor 只报告，不删除。

来源：`AEH-RUNTIME-DOCTOR-6513102`

---

## Contract / Runtime Integrity

Doctor：

```text
读取 manifest
验证 schema
检查 harness/schema version
重算 runtime digest
```

digest 不匹配：

```text
BLOCKED_RUNTIME_INTEGRITY
```

来源：`AEH-RUNTIME-DOCTOR-6513102`

这直接实现：

> **不能基于被换过的裁判规则宣布 READY。**

---

## Profile / Workflow

检查：

```text
profile schema
profile BLOCKED
policy conflicts
provenance completeness
effective-workflow schema
```

---

## Adapter

检查：

```text
AGENTS.md managed block
CLAUDE.md managed block
capability enforcement status
```

---

## Private Boundary

检查：

```text
.aeh/private/
是否被 gitignore
```

且 Doctor Evidence 不应回显 Private 正文。

---

# 14. Doctor 与 Repair 为什么必须分开

V0.1 明确：

```text
No repair/recover subsystem
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这不是 Doctor 的缺陷。

更合理的权限分离：

```text
Doctor
= read-only diagnose

Repair
= explicit mutation plan
  + dry-run
  + journal
  + rollback
```

否则用户执行：

```text
aeh doctor
```

时无法知道它会不会改仓库。

---

# 15. 项目接入标准流程

```text
1. Clean/known repository state

2. aeh bootstrap . --dry-run
   ↓
   inspect install plan

3. Provide explicit answers/policies where needed

4. aeh bootstrap .
   ↓
   install .aeh + managed blocks

5. aeh doctor .
   ↓
   READY / READY_WITH_WARNINGS / BLOCKED

6. Only after Doctor admission:
   start Change lifecycle
```

---

# 16. Architecture Invariants

### BOOT-INV-01

> **Bootstrap MUST be plan-first and fail-safe for writes.**

### BOOT-INV-02

> **Repeated compilation with identical semantic inputs SHOULD NOT create meaningless repository diff.**

### BOOT-INV-03

> **Doctor MUST remain read-only.**

### BOOT-INV-04

> **A runtime integrity mismatch MUST block admission rather than allow validation under modified rules.**

### BOOT-INV-05

> **Repair is a separate explicit mutation authority.**

---

# 17. 当前限制

```text
No repair
No upgrade
No repository-wide atomic transaction
Editable install only
No OS ACL/chmod security boundary
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这些会进入后续架构 Roadmap，但不能在手册中写成当前能力。

---

# 18. References

- `AEH-RUNTIME-BOOTSTRAP-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`
- `AEH-SCHEMA-INSTALL-PLAN-6513102`
- `AEH-SCHEMA-MANIFEST-6513102`
- `AEH-SCHEMA-DOCTOR-6513102`
- `AEH-RUNTIME-ADAPTER-6513102`
- `AEH-KNOWN-LIMITATIONS-6513102`
