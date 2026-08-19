# 20 · Artifact Integrity 与 Audit Bundle

> **章节类型**：BUILD / ASSURANCE OUTPUT  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **重要说明**：V0.1 已有大量可审计 Machine Artifact，但“标准化导出的 Audit Bundle”在本手册中是目标模型，不应伪装成当前完整产品功能。

---

# 1. 为什么需要 Audit Bundle

一次高风险 Change 结束后，第三方应该能够回答：

```text
谁提出了什么变更？
基于哪个代码版本？
Grounding 看到了什么？
Spec 要求什么？
什么测试先真实 RED？
测试后来有没有被改？
实际改了哪些生产文件？
GREEN / Regression 结果是什么？
Requirement 如何映射到 Test / Code / Verification？
谁批准？
为什么最终 MERGE_READY / BLOCKED？
```

如果回答这些问题必须：

```text
翻聊天记录
问原 Agent
回忆当时发生什么
```

就没有形成成熟 Assurance。

---

# 2. 当前已经存在的 Artifact Chain

典型 Change：

```text
manifest.yaml
profile.yaml
effective-workflow.yaml

change.yaml
evidence.yaml
spec.yaml
test-plan.yaml
red.yaml
test-lock.yaml
green.yaml
verification.yaml
traceability.yaml
approvals.yaml

evidence/*.log
review.md
```

其中：

```text
review.md
```

只是 Human Projection。

真正机器链来自 YAML/JSON + 原始日志。

---

# 3. Manifest 是 Audit Root 之一

Manifest 记录：

```text
AEH version
source revision
compiler version
schema version
install time
runtime/compiler/bootstrap/adapter hashes
```

来源：`AEH-SCHEMA-MANIFEST-6513102`

它回答：

> **哪一版裁判体系参与了这次 Change？**

---

# 4. RED Audit Artifact

RED 保存：

```text
command
exit code
output ref/hash
expected failure
actual failure
base commit
test hashes
verdict
```

来源：`AEH-SCHEMA-RED-6513102`

它回答：

> **修复前真的失败了吗？为什么失败？**

---

# 5. Test Lock Audit Artifact

Test Lock 保存：

```text
test file path/hash
protected context hashes
repository base state
lock time
```

来源：`AEH-SCHEMA-TESTLOCK-6513102`

它回答：

> **实现阶段使用的 Oracle 是哪一份？**

---

# 6. GREEN Audit Artifact

GREEN 保存：

```text
test_lock_hash
production_before_hash
production_after_hash
test output hashes
changed files
before/after file hashes
```

来源：`AEH-SCHEMA-GREEN-6513102`

它回答：

> **实际实现改变了什么，以及验证使用的 Test Lock 是哪一份？**

---

# 7. Verification Artifact

Verification 保存：

```text
target_test
regression
integration
contract
runtime
platform
manual

status
method
exit_code
output_ref/hash
overall
blocked_reason
warnings
verified_at
```

来源：`AEH-SCHEMA-VERIFY-6513102`

它回答：

> **最终执行了哪些验证，哪个失败导致了 BLOCK？**

---

# 8. Traceability Artifact

Traceability：

```text
REQ
→ AC
→ TEST
→ CODE
→ VER
```

来源：`AEH-SCHEMA-TRACE-6513102`

它回答：

> **这些测试和代码为什么属于这个 Change？**

---

# 9. Approval Artifact

Approval：

```text
gate
status
actor
decided_at
evidence_ref
```

来源：`AEH-SCHEMA-APPROVAL-6513102`

当前限制：

```text
attestation only
```

所以 Audit Bundle 必须如实表达：

```text
identity_strength: attestation
```

而不是：

```text
identity_verified: true
```

---

# 10. Audit Bundle 的目标不是“压 ZIP”

[DECISION] `ADR-HB-021`

Audit Bundle 是：

> **一组足以解释并尽可能重放 Acceptance Decision 的最小证据集。**

具体封装可以是：

```text
directory
zip
CI artifact
signed attestation bundle
SCM attachment
```

格式可以演化。

---

# 11. 候选 Bundle Manifest

这是手册设计建议，不是 V0.1 现有 Schema：

```yaml
audit_bundle:
  version: 1

  change_id:

  repository:
    base_sha:
    final_sha_or_tree_hash:

  aeh:
    version:
    source_revision:
    runtime_digest:

  contract:
    spec_ref:
    scope_ref:
    risk:

  assurance:
    red_ref:
    test_lock_ref:
    green_ref:
    verification_ref:
    traceability_ref:
    approvals_ref:

  raw_evidence:
    - path:
      sha256:

  verdict:
    task_outcome:
    assurance_outcome:

  limitations:
    - ...
```

---

# 12. Replay Levels

建议将 Auditability 分级：

```text
A0 — Narrative only

A1 — Machine artifacts present

A2 — Hash-bound artifacts

A3 — Repo revision + commands + environment known

A4 — Third party can rerun deterministic checks

A5 — Protected CI / signed provenance / strong identity
```

当前 V0.1 不应被宣传成完整 A5。

---

# 13. Release Baseline 也体现同一思想

V0.1 Release 目录已经包含：

```text
RELEASE_BASELINE.sha256
RELEASE_MANIFEST.yaml
RELEASE_TEST_REPORT.md
KNOWN_LIMITATIONS.md
```

来源：`AEH-RELEASE-TEST-6513102` 与 release directory evidence。

这说明 AEH 自己已经在采用：

```text
Release Artifact
+
Hash baseline
+
Test report
+
Known limitations
```

的证据风格。

手册应把同一原则推广到单次 Change，但不能假装标准 Bundle 已经正式实现。

---

# 14. Artifact Integrity 与 Strong Provenance 的区别

Hash 能证明：

```text
内容没变化
```

Hash 不能单独证明：

```text
是谁生成的
生成时是否可信
身份是否真实
机器是否受保护
```

所以：

```text
Integrity
≠
Identity
≠
Provenance
```

强 Assurance 最终可能需要：

```text
hash
+ protected execution
+ trusted identity
+ attestation
```

---

# 15. Failure Modes

### FM-AUD-01 — Missing Raw Output

只保存：

```text
PASS
```

不保存 output/log/hash。

无法复核。

### FM-AUD-02 — Bundle Cannot Identify Validator Version

不知道：

```text
哪版 AEH
哪版 schema
哪版 runtime
```

不能可靠解释 Verdict。

### FM-AUD-03 — Narrative Replaces Machine Truth

只保留 `review.md`。

无法独立重算。

### FM-AUD-04 — Identity Overclaim

只有：

```text
actor: Alice
```

却宣称：

```text
cryptographically verified by Alice
```

错误。

---

# 16. Architecture Invariants

### AUD-INV-01

> **An audit artifact MUST preserve enough provenance to explain which state and rules it describes.**

### AUD-INV-02

> **The audit chain SHOULD retain raw evidence or hashes/references sufficient for independent checking.**

### AUD-INV-03

> **Human narrative MUST remain a projection, not the sole acceptance record.**

### AUD-INV-04

> **Audit output MUST state assurance limitations honestly, especially identity and environment strength.**

---

# 17. 当前事实与未来工作

当前已有：

```text
✓ machine artifacts
✓ output hashes
✓ file hashes
✓ runtime/source revision manifest
✓ traceability
✓ approvals
✓ release evidence style
```

仍需设计：

```text
? standardized change audit bundle export
? CI artifact format
? signed provenance
? retention policy
? enterprise identity integration
? cross-platform replay
```

---

# 18. References

- `AEH-SCHEMA-MANIFEST-6513102`
- `AEH-SCHEMA-RED-6513102`
- `AEH-SCHEMA-TESTLOCK-6513102`
- `AEH-SCHEMA-GREEN-6513102`
- `AEH-SCHEMA-VERIFY-6513102`
- `AEH-SCHEMA-TRACE-6513102`
- `AEH-SCHEMA-APPROVAL-6513102`
- `AEH-RELEASE-TEST-6513102`
