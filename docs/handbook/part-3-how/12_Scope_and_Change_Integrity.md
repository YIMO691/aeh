# 12 · Scope 与变更完整性

> **章节类型**：HOW / CORE ASSURANCE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **核心区分**：`Runtime Capability ≠ Change Authorization`

---

## 1. 为什么“能改”不等于“该改”

一个 Coding Agent 可能拥有 `workspace-write`，技术上可以修改 `src/ / tests/ / config/ / build/`。但一个具体任务可能只被授权修改 `src/reward/RewardService.py`。

所以：

```text
Sandbox / Permission:
Agent 技术上能不能写？

Change Scope:
这次 Change 合法上允许写什么？
```

这两个边界必须分开。[DECISION] `ADR-HB-013`。

## 2. Scope Assurance 的定义

> **Scope Assurance 是独立判断实际 Repository Mutation 是否落在冻结的 Change Authorization 内，并且被声明的文件状态与真实文件状态一致。**

至少比较：

```text
Authorized scope
Actual changed files
Expected before hash
Actual after hash
```

## 3. AEH V0.1 的 Scope 输入

[AEH][FACT] GREEN runtime 支持读取显式 Scope 文件；如果未提供，则当前实现会根据 Grounding Evidence 中 `SOURCE / CONFIG` 的 `rel_path` 推导默认 allowlist。来源：`AEH-RUNTIME-GREEN-6513102`。

这是 V0.1 实现策略，本手册不把“Grounding SOURCE/CONFIG 即默认可改范围”冻结为长期原则。

## 4. GREEN 如何验证 Scope

GREEN runtime 读取：

```text
allowed_paths = scope.allowed_paths
changed_files = scope.changed_files
```

逐项检查 `changed path ∈ allowed_paths`，否则 `BLOCKED_SCOPE_VIOLATION`。之后重新读取真实文件，验证 `sha256(actual file) == declared after_hash`；不一致同样阻塞。来源：`AEH-RUNTIME-GREEN-6513102`。

因此 Generator 不能只说“我只改了 A.py”；Validator 会检查真实文件状态。

## 5. GREEN Evidence 中的 Changed Files

V0.1 `green.schema.json` 记录：

```yaml
changed_files:
  - code_id:
    path:
    before_hash:
    after_hash:
```

以及：

```text
production_before_hash
production_after_hash
```

来源：`AEH-SCHEMA-GREEN-6513102`。

这些 `CODE-xxx` 为后续 Traceability 提供稳定引用。

## 6. Scope 与 Evidence Freshness 的冲突

实现阶段允许某些源文件合法改变，但 Grounding Evidence 可能绑定这些文件旧 Hash。如果简单执行“任何 Evidence Source Hash 改变 → BLOCK”，合法实现永远无法进入 GREEN。

V0.1 GREEN runtime 因此把本次受控 `changed_files` 从 stale 检查中排除，其他 Evidence 漂移仍会阻塞。来源：`AEH-RUNTIME-GREEN-6513102`。

> **Freshness 检查必须理解受控变更边界。**

## 7. Scope 不等于 File Count

错误的风险判断：

```text
改 1 个文件 = LOW
改 20 个文件 = HIGH
```

AEH V0.1 `core/classifications.yaml` 已明确禁止以 `file_count / line_count` 作为唯一判据。来源：`AEH-CORE-CLASSIFICATIONS-6513102`。

同样，Scope size 不等于 Risk。一行 payment authorization 也可能是 CRITICAL。

## 8. Runtime Policy 与 Scope Assurance 如何协同

理想结构：

```text
AEH Change Contract
  allowed_paths = A/B/C
        │
        ▼
Native Policy / Sandbox
尽量把技术能力限制到该范围
        │
        ▼
Generator works
        │
        ▼
AEH Scope Validator
recomputes actual diff / hashes
```

这样形成：

```text
Prevent + Detect
```

而不是二选一。

## 9. 为什么 AEH 不应该自研 OS Sandbox

Native Runtime 更适合拥有 filesystem isolation、network isolation、process boundary、tool-call policy。来源：`EXT-GEMINI-SANDBOX`、`EXT-GEMINI-POLICY-ENGINE`。

AEH 更适合：

```text
声明 Change Scope
映射到 Native Capability
验证实际 Diff
发现 Capability Mapping 不可 enforce 时诚实报告
```

## 10. Scope Escape

对应 PoV：`A04 Scope Escape`。

例如：

```text
Allowed:
src/reward.py

Actual:
src/reward.py
src/mail.py
config/prod.yaml
```

即使 Hidden Tests 全 PASS：

```text
task_outcome = PASS
assurance_outcome = BLOCKED_SCOPE_VIOLATION
```

这是 `Task Success ≠ Assurance Success` 的典型案例。

## 11. Scope 与 Traceability

Scope 只能回答“文件是否在允许范围”，不能回答“为什么这个文件需要改”。所以后续还需要：

```text
CODE-001
→ TEST-001
→ AC-001-01
→ REQ-001
```

如果文件在 allowlist 内，却无法链接到任何 Requirement，就是 `orphan code`。V0.1 Traceability runtime 会阻塞。来源：`AEH-RUNTIME-TRACE-6513102`。

因此：

```text
Scope Integrity + Traceability = 更强 Change Integrity
```

## 12. Scope Contract 的长期模型

建议长期区分：

```yaml
scope:
  allowed: []
  forbidden: []
  generated: []
  test: []
  production: []
  policy_exceptions: []
```

注意：这是架构建议，不是当前 V0.1 Schema 事实。

## 13. Failure Modes

### FM-SC-01 — Declared Diff Lies

Agent 声称 changed_files=[A]，实际 Hash 对不上。V0.1 GREEN 应返回 `BLOCKED_SCOPE_VIOLATION`。

### FM-SC-02 — Allowed but Unjustified

文件在 allowlist，但没有 Requirement/Test Trace，应由 Traceability 阻塞。

### FM-SC-03 — Permission Too Wide

Sandbox 给 Agent 整仓库写权限，不自动意味着 Change 不可信；但更强系统应追求 `least privilege + independent diff validation`。

## 14. Architecture Invariants

### SC-INV-01
> **Runtime Capability MUST NOT be treated as Change Authorization.**

### SC-INV-02
> **The actual repository mutation MUST be independently compared with the authorized Change Scope.**

### SC-INV-03
> **Declared changed-file metadata MUST be checked against actual file state.**

### SC-INV-04
> **Scope-valid code may still be assurance-invalid if it has no justified trace to the Change Contract.**

## 15. 当前实现事实与限制

已支持：allowed path check、changed file after_hash check、production before/after hash evidence、受控变更下的 stale exclusion、orphan code check。

未决：默认 allowlist 推导是否长期合理、是否需要 git-native diff derivation、Native sandbox capability 如何自动协商、A04 正式攻击结果。

## 16. References

- `AEH-RUNTIME-GREEN-6513102`
- `AEH-SCHEMA-GREEN-6513102`
- `AEH-RUNTIME-TRACE-6513102`
- `AEH-CORE-CLASSIFICATIONS-6513102`
- `EXT-GEMINI-SANDBOX`
- `EXT-GEMINI-POLICY-ENGINE`
