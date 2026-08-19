# 02 · 从 AI 自检到独立 Acceptance

> **章节类型**：WHY  
> **核心问题**：Agent 能自检，为什么还需要独立 Acceptance？

---

## 1. “AI 不能自我验证”是错误的绝对表述

Coding Agent 可以有效利用：

```text
Compiler
Type Checker
Unit Test
Integration Test
Static Analyzer
Runtime feedback
```

形成：

```text
Generate → Execute → Observe → Repair
```

因此本手册不主张：

> “Generator 的自检没有价值。”

真正的问题是：

> **Generator 能否同时拥有最终 Acceptance Authority？**

---

## 2. 三个验证强度

### Level A — Self Verification

```text
Generator
→ review own output
→ run tests
→ repair
```

便宜、快速，应保留。

### Level B — Independent Probabilistic Reviewer

```text
Generator
→ separate Reviewer/Evaluator Agent
→ review
```

[EXT] Anthropic 的长任务 Harness 设计使用 planner / generator / evaluator 分离。来源：`EXT-ANTHROPIC-HARNESS-DESIGN-2026`。

它能够降低一部分单 Agent 盲点，但 Reviewer 仍可能是概率性模型。

### Level C — External Authoritative Verification

```text
Generator
→ externally owned/frozen evidence
→ deterministic or authoritative checks
→ Accept / Block
```

AEH 候选核心处于这一层。

---

## 3. 为什么“谁决定”比“谁检查”更重要

一个 Agent 可以：

```text
写代码
跑测试
发现失败
修复
```

这完全合理。

但如果它还可以：

```text
改测试
改 Gate
改 Approval
改 Validator Contract
然后自己宣布通过
```

则系统缺少权力分离。

因此：

```text
Self-correction capability
≠
Acceptance authority
```

---

## 4. Oracle 是最清晰的例子

测试的价值来自：

> 它定义了一个相对独立的成功标准。

如果实现者在 GREEN 过程中随意把：

```text
expected = 100
```

改为：

```text
expected = actual
```

测试仍可 PASS，但原目标已经消失。

因此真正长期需求是：

> **Oracle Ownership Separation**

Test Lock 只是这一原则在 AEH V0.1 中的一种实现。来源：`AEH-RUNTIME-RED-6513102`、`AEH-RUNTIME-GREEN-6513102`。

---

## 5. Scope、Evidence、Approval 同理

### Scope

```text
Agent 能写这个文件
≠
这次 Change 被授权写这个文件
```

### Evidence

```text
Agent 写了 verification.yaml
≠
verification 真的发生
```

### Approval

```text
actor.id = Alice
≠
已证明 Alice 真实批准
```

所以独立 Acceptance 是多个 Authority Boundary 的组合。

---

## 6. 为什么模型变聪明不会自动消灭这个问题

[EXT] Anthropic 已提醒，Harness 中围绕当前模型弱点构建的假设会过期。来源：`EXT-ANTHROPIC-MANAGED-AGENTS-2026`。

因此 AEH 不应建立在：

```text
Agent 不会规划
Agent 不会测试
Agent 不会搜索
```

这些暂时能力差距上。

更稳定的是：

> **即使 Generator 很聪明，也不应该因为它生成了候选结果，就自动拥有最终接受权。**

---

## 7. Architecture Invariant

[NORMATIVE]

> **The system SHOULD use Generator self-verification for efficiency, but MUST NOT use Generator self-assertion as the sole final acceptance authority for assurance-critical changes.**

---

## 8. References

- `EXT-ANTHROPIC-HARNESS-DESIGN-2026`
- `EXT-ANTHROPIC-MANAGED-AGENTS-2026`
- `AEH-ARCH-6513102`
- `AEH-RUNTIME-RED-6513102`
- `AEH-RUNTIME-GREEN-6513102`
