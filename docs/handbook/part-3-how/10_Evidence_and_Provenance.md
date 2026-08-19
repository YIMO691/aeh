# 10 · Evidence 与 Provenance

> **章节类型**：HOW / CORE ASSURANCE  
> **状态**：H3_IMPLEMENTED_DRAFT  
> **核心问题**：AEH 为什么不能只保存“结果”，而必须证明结果来自什么代码、什么环境、什么命令和什么可信路径？

---

## 1. 本章解决什么问题

Agentic Coding 最大的错觉之一是：

```text
有日志 = 有证据
有 evidence.yaml = 证据可信
测试输出 PASS = 可接受
```

这些等式都不成立。AEH 真正需要的是：

```text
Evidence
+ Provenance
+ Freshness
+ Integrity
+ Replayability
= 可用于 Acceptance 的证据
```

[NORMATIVE][DECISION] `ADR-HB-011`

> **Artifact Presence 只能证明“文件存在”；不能自动证明“内容可信”。**

## 2. 什么是 Evidence

本手册将 Evidence 定义为：

> **能够被独立检查，并对某个工程 Claim 提供支持或反证的可复核事实。**

Evidence 可能来自：

```text
SOURCE
TEST
CALL_PATH
CONFIG
ARCHITECTURE_CONSTRAINT
NEGATIVE_SEARCH
Command output
Git diff
Hash
Runtime observation
Manual attestation
```

[AEH][FACT] V0.1 `evidence-index.schema.json` 已定义 `SOURCE / TEST / CALL_PATH / CONFIG / ARCHITECTURE_CONSTRAINT / NEGATIVE_SEARCH / UNKNOWN`，并为 Evidence 提供 `id / finding / confidence / location / source_state / limitations`。来源：`AEH-SCHEMA-EVIDENCE-6513102`。

## 3. Evidence 与 Claim 的关系

Evidence 不是“结论本身”。

```text
Claim:
“RewardService 当前允许重复领取。”

Evidence EV-001:
path = RewardService.cs
symbol = ClaimReward
file_hash = H1
finding = missing idempotency guard
confidence = DIRECT
```

另一个 Evidence 可能是：

```text
EV-002
 type = TEST
 finding = duplicate request reproduces double grant
```

所以关系是：

```text
Claim ← supported / contradicted by Evidence[]
```

而不是 `Claim = Evidence`。

## 4. Provenance 是什么

Provenance 回答：

```text
证据来自谁？
来自哪里？
基于哪个 Repository State？
什么时候产生？
通过什么 Method 产生？
```

V0.1 Evidence Index 已经能够记录：

```yaml
repository:
  base_commit:
  dirty:

evidence:
  - source_state:
      base_commit:
      dirty:
      file_hash:
      rel_path:
```

来源：`AEH-SCHEMA-EVIDENCE-6513102`。

这使 Evidence 不再只是“我看过这个文件”，而是“我在某个 Repository State 上检查过这个具体文件状态”。

## 5. Provenance 为什么重要

假设：

```text
10:00 Grounding:
RewardService.cs hash = H1

10:20 另一个 Change 修改同文件:
hash = H2

10:30 当前 Agent 仍根据 H1 写 Spec
```

如果没有 Provenance，Evidence 看起来仍然存在；如果有 Provenance：

```text
current hash H2 != evidence source hash H1
→ STALE
```

[AEH][FACT] V0.1 RED runtime 在执行 RED 前调用 `check_stale`；发现 stale evidence 会返回 `BLOCKED_STALE_EVIDENCE`。来源：`AEH-RUNTIME-RED-6513102`。

[AEH][FACT] GREEN 和 VERIFY 也会重新检查 stale evidence，只排除本次受控修改的生产文件。来源：`AEH-RUNTIME-GREEN-6513102`、`AEH-RUNTIME-VERIFY-6513102`。

这说明 Freshness 不是只在 Grounding 时检查一次，而是进入后续 Gate 时需要重新确认。

## 6. Evidence Freshness

定义：

> **Evidence 在当前 Acceptance Decision 所依赖的 Source State 上仍然有效。**

概念上：

```text
EvidenceState = hash(source_at_capture)
CurrentState  = hash(source_now)

if relevant_source_changed:
    Evidence = STALE
```

但实际系统不能简单地“任何文件变化 → 所有 Evidence stale”，因为 GREEN 本身就会合法修改生产文件。因此必须区分：

```text
authorized mutation
vs
unrelated source drift
```

[AEH][FACT] GREEN runtime 的 `_stale_excluding` 会在 stale 检查时排除当前受控 changed_files，但其他关联 Evidence 变 stale 仍会阻塞。来源：`AEH-RUNTIME-GREEN-6513102`。

## 7. RED Evidence 为什么比“测试红了”更复杂

一个失败测试不一定证明 Bug 存在，可能是：

```text
ImportError
Fixture broken
Spec mismatch
Test defect
Environment failure
Unexpected failure
```

V0.1 RED Evidence 记录：

```text
command
exit_code
output_ref
output_hash
expected_failure
actual_failure
base_commit
changed_files_hash
test_files_hash
verdict
```

并定义：

```text
VALID_RED
INVALID_RED_TEST_DEFECT
INVALID_RED_SPEC_MISMATCH
INVALID_RED_ENVIRONMENT
INVALID_RED_FIXTURE
INVALID_RED_UNEXPECTED_FAILURE
NO_RED_ALREADY_GREEN
```

来源：`AEH-SCHEMA-RED-6513102`、`AEH-RUNTIME-RED-6513102`。

因此 RED 不是 `exit_code != 0`，而是：

> **失败模式与冻结预期相匹配，并且失败发生在可复核 Repository State 上。**

## 8. Output Hash 的意义

如果 Evidence 只记录 `exit_code: 1`，第三方不知道当时具体输出是什么，也不知道后来 log 有没有被改。

V0.1 RED / GREEN / VERIFY 都会把原始输出落盘并保存 `output_hash`。来源：`AEH-SCHEMA-RED-6513102`、`AEH-SCHEMA-GREEN-6513102`、`AEH-SCHEMA-VERIFY-6513102`。

这不是密码学身份签名，但至少提供 Artifact Content Integrity。

## 9. Confidence、Unknowns 与 Limitations

成熟 Evidence System 必须允许“不知道”。V0.1 Evidence Index 已定义：

```text
confidence:
  DIRECT
  INDIRECT
  INFERRED

unknowns:
  field
  reason

limitations: []
```

来源：`AEH-SCHEMA-EVIDENCE-6513102`。

因此一个重要工程原则是：

> **诚实的 UNKNOWN 比伪造的 HIGH_CONFIDENCE 更有价值。**

## 10. Artifact Presence ≠ Evidence Validity

[EVAL] RUN-D004 中 `.aeh` manifest、`change.yaml` 和 workflow artifacts 都存在，但真实 External Validator Replay 得到 `BLOCKED_CHANGE_STATE`。来源：`EVAL-P1-D004`。

因此未来 Evidence Model 至少应拆分：

```yaml
artifact:
  present: true
provenance:
  valid: false
validator:
  accepted: false
```

而不是一个模糊的 `AEH_EVIDENCE_OK`。

## 11. Evidence Trust Ladder

建议手册采用：

```text
L0 — Statement
Agent 说它跑过。

L1 — Artifact
有一份 log/test result。

L2 — Bound Evidence
Artifact 绑定 repo SHA / file hash / command。

L3 — Integrity Checked
Artifact 内容 hash、source freshness、protected state 被检查。

L4 — Independently Recomputed
外部 Validator 在当前可信环境重新执行或重算。

L5 — Strong Attestation
由强身份/签名/可信 CI 证明来源。
```

当前 AEH V0.1 主要覆盖 L2–L4 的部分能力，不是完整 L5。

## 12. Evidence Substrate 与 AEH Evidence Engine 的边界

Git / CI / Test Runner 已经产生大量原始 Evidence。AEH 不应该重新发明 Git、Test Framework、Build System、CI Log Store。

AEH 应负责：

```text
选择哪些 Evidence 能参与 Gate
绑定 Provenance
检查 Freshness
检查 Integrity
建立 Trace
触发 Replay
产生 Acceptance Verdict
```

## 13. Failure Modes

### FM-EV-01 — Trust File Existence

`verification.yaml exists → VERIFIED`：错误。

### FM-EV-02 — Trust Agent Summary

Agent 说“Tests all pass”，但没有 command/output/hash/replay：不足。

### FM-EV-03 — Stale Grounding

Grounding 后源代码改变，但 Spec/GREEN 继续使用旧 Evidence：必须 BLOCK 或重新 Ground / Repair。

### FM-EV-04 — Evidence Without Limitation

推断性 Evidence 被写成直接事实：应记录 confidence / limitations / unknowns。

## 14. Architecture Invariants

### EV-INV-01
> **Evidence MUST be bound to sufficient provenance to identify the state it describes.**

### EV-INV-02
> **Evidence that depends on mutable source state MUST be revalidated for freshness before critical acceptance transitions.**

### EV-INV-03
> **Artifact Presence MUST NOT imply Evidence Validity.**

### EV-INV-04
> **Where deterministic recomputation is practical, Acceptance SHOULD prefer recomputation over self-reported summaries.**

## 15. 当前实现事实与限制

已支持：Evidence 类型/置信度、Repository base state、Source rel_path/file_hash、Unknowns/limitations、RED/GREEN/VERIFY output hash、staleness check、Test Lock protected hashes。

尚不能宣称：强身份 Evidence Producer、密码学签名 Evidence Bundle、企业 CI provenance、全部 Evidence 都不可篡改。

## 16. References

- `AEH-SCHEMA-EVIDENCE-6513102`
- `AEH-SCHEMA-RED-6513102`
- `AEH-SCHEMA-GREEN-6513102`
- `AEH-SCHEMA-VERIFY-6513102`
- `AEH-RUNTIME-RED-6513102`
- `AEH-RUNTIME-GREEN-6513102`
- `AEH-RUNTIME-VERIFY-6513102`
- `EVAL-P1-D004`
