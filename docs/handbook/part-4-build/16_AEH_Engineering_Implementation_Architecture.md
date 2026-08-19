# 16 · AEH 工程实现架构

> **章节类型**：BUILD  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **源码基线**：`YIMO691/aeh @ 6513102`  
> **核心问题**：前面定义的 Change Assurance 责任，当前 AEH V0.1 是如何映射到真实代码、机器契约与用户仓库中的？

---

## 1. 本章不做“逐文件导读”

架构手册如果按：

```text
change.py
red.py
green.py
verify.py
```

逐文件介绍，很快会随着重构失效。

本章采用：

```text
Architecture Responsibility
        ↓
Machine Contract
        ↓
Current Runtime Module
        ↓
Stored Artifact
        ↓
Validation Boundary
```

[DECISION] `ADR-HB-017`

---

## 2. AEH V0.1 内部五层

冻结架构定义：

```text
Core
Bootstrap
Project Profile
Adapter
Runtime
```

来源：`AEH-ARCH-6513102`

### Core

负责：

```text
workflow
states
gates
precedence
classifications
machine semantics
```

不得包含项目业务硬编码。

### Bootstrap

负责：

```text
repository discovery
interview
conflict resolution input
profile compilation
install planning
runtime snapshot installation
```

### Project Profile

用户项目中：

```text
.aeh/profile.yaml
.aeh/effective-workflow.yaml
```

表达已经编译后的项目级 Canonical Configuration。

### Adapter

把 Canonical Semantics 映射到：

```text
Codex
Claude
未来 Agent
```

Adapter 不拥有第二套工作流语义。

### Runtime

执行：

```text
doctor
change lifecycle
grounding
specification
test design
RED
GREEN
verification
approval
traceability
```

---

## 3. 三层责任模型仍然是工程实现的主轴

```text
Guidance
  ↓
告诉 Agent 应该怎么做

Normative Contract
  ↓
定义什么状态/数据合法

Enforcement Engine
  ↓
实际读取 Repo / Artifact / Hash / Test，
产生 PASS/BLOCK
```

来源：`AEH-ARCH-6513102`

这与目录结构不是一回事。

例如：

```text
Test Lock
```

同时涉及：

```text
Schema                 → Normative Contract
red.py / green.py      → Enforcement
AGENTS/CLAUDE guidance → Guidance
```

---

## 4. 当前代码拓扑

`src/aeh/` 当前主要包含：

```text
adapters/
bootstrap/
doctor/
runtime/

cli.py
compiler.py
conflict.py
discovery.py
interview.py
```

来源：`AEH-CLI-6513102` 以及 `AEH-RUNTIME-*` 系列 Source Registry。

运行时主模块包括：

```text
approval.py
change.py
classify.py
green.py
grounding.py
red.py
specification.py
test_design.py
traceability.py
verify.py
```

这说明当前实现已经把：

```text
Bootstrap / Health / Runtime Change
```

分成相对清晰的责任区。

---

## 5. 单一 CLI 入口

[AEH][FACT] `src/aeh/cli.py` 暴露统一入口：

```text
aeh bootstrap
aeh doctor

aeh change new
aeh change status
aeh change transition
aeh change ground
aeh change spec
aeh change test-design
aeh change red
aeh change green
aeh change refactor
aeh change verify
aeh change approve
aeh change review
```

来源：`AEH-CLI-6513102`

CLI 不应成为 Business Logic Owner。

它的合理职责：

```text
argument parsing
dispatch
machine-readable result printing
exit code
```

实际 Contract/Validation 仍在下层模块。

---

## 6. Exit Code 是工程接口的一部分

当前 CLI 对：

```text
BOOTSTRAP_COMPLETE
RED_COMPLETE
GREEN_COMPLETE
VERIFY_COMPLETE
```

等成功状态返回 `0`；

对 BLOCK/FAIL 返回非零。

来源：`AEH-CLI-6513102`

这对 CI 很重要：

```text
人类看 JSON
机器看 exit code + artifact
```

但长期不能只依赖：

```text
process exit code
```

Acceptance 仍应读取完整机器 Verdict。

---

## 7. Bootstrap 的工程数据流

```text
Repository
   ↓
Discovery
   ↓
Interview / Answers
   ↓
Conflict resolution
   ↓
Profile Compiler
   ↓
profile.yaml
   ↓
Workflow Compiler
   ↓
effective-workflow.yaml
   ↓
Adapter Renderer
   ↓
Install Plan
   ↓
Stage / Validate / Apply
   ↓
.aeh runtime snapshot
```

Bootstrap 是 AEH 从：

```text
公共 Harness
```

变成：

```text
某个项目里的 versioned contract layer
```

的安装边界。

---

## 8. Runtime Snapshot

Bootstrap 会把：

```text
core/*.yaml
schemas/*.json
```

复制到：

```text
.aeh/runtime/core/
.aeh/runtime/schemas/
```

来源：`AEH-RUNTIME-BOOTSTRAP-6513102`

这使项目能够记录：

> 当前安装到底使用了哪一版规则。

同时 Manifest 记录 Runtime Digest。

---

## 9. Manifest 是版本/来源锚点

V0.1 Manifest 要求：

```text
harness.name
harness.version
harness.source_revision
compiler.version
schema.version
installed_at
source_hashes.runtime
source_hashes.compiler
source_hashes.bootstrap_contract
source_hashes.adapters
```

来源：`AEH-SCHEMA-MANIFEST-6513102`

因此 Manifest 主要回答：

```text
“这个项目里的 AEH 状态到底来自哪一版？”
```

---

## 10. Change Workspace

每个 Change 存在独立目录：

```text
.aeh/changes/CHG-YYYY-NNNN/
```

可能包含：

```text
change.yaml
evidence.yaml
spec.yaml
test-plan.yaml
red.yaml
test-lock.yaml
green.yaml / refactor.yaml
verification.yaml
traceability.yaml
approvals.yaml
review.md
evidence/*.log
```

机器真值与人类投影分离。

---

## 11. 概念组件到当前实现的映射

| 概念责任 | 当前主要实现 |
|---|---|
| Change Contract | `specification.py` + schemas |
| Evidence / Provenance | `grounding.py` + evidence schema |
| Oracle Integrity | `red.py` + `test-lock` + `green.py` |
| Scope Integrity | `green.py` |
| Risk | `classify.py` + `core/classifications.yaml` |
| Traceability | `traceability.py` |
| Approval | `approval.py` + approvals schema |
| External Verification | `verify.py` |
| Health / Integrity Admission | `doctor/doctor.py` |
| Project Install | `bootstrap/pipeline.py` |
| Agent Translation | `adapters/render.py` |

这张表描述当前实现映射，不意味着未来文件名不可变。

---

## 12. AEH 没有数据库是当前设计选择

V0.1 核心状态基于：

```text
Git repository
YAML / JSON
Markdown projection
file hashes
test outputs
```

这使：

```text
local-first
repo-native
inspectable
portable
```

更容易成立。

但未来是否需要外部服务，应由：

```text
identity
cross-repo governance
central policy
enterprise audit
```

等真实需求决定。

不能因为“企业系统通常有数据库”就提前引入。

---

## 13. Packaging 的当前边界

[AEH][FACT] `pyproject.toml` 当前：

```text
packages.find:
  where = ["src"]
  include = ["aeh*"]
```

没有声明：

```text
core/
schemas/
bootstrap/
adapters/
```

作为 package data。

来源：`AEH-PYPROJECT-6513102`

Release Known Limitations 因此明确：

```text
Editable install only
Relocatable wheel post-V0.1
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这也是 V0.2 M1 的合理基础设施问题，但不是 Change Assurance 新功能。

---

## 14. Architecture Invariants

### ENG-INV-01

> **Conceptual responsibility MUST remain distinguishable from current module layout.**

### ENG-INV-02

> **The CLI MUST be an entry surface, not an alternative source of workflow truth.**

### ENG-INV-03

> **Installed project state MUST retain enough version/digest information to identify the contracts used to judge it.**

### ENG-INV-04

> **Human-readable projections MUST NOT replace machine artifacts used for gates.**

---

## 15. 当前工程成熟度事实

Release report：

```text
232 / 232 automated tests PASS
```

环境：

```text
Windows 10/11
Python 3.11.15
PyYAML 6.0.3
jsonschema 4.26.0
```

来源：`AEH-RELEASE-TEST-6513102`

这证明：

> V0.1 有较完整回归基线。

它不证明：

> AEH 已经达到跨平台/企业生产级基础设施成熟度。

---

## 16. References

- `AEH-ARCH-6513102`
- `AEH-CLI-6513102`
- `AEH-RUNTIME-BOOTSTRAP-6513102`
- `AEH-SCHEMA-MANIFEST-6513102`
- `AEH-PYPROJECT-6513102`
- `AEH-KNOWN-LIMITATIONS-6513102`
- `AEH-RELEASE-TEST-6513102`
