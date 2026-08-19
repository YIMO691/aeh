# 00 · 阅读指南与手册定位

> **手册**：AEH Engineering & Architecture Handbook v0.2  
> **研究截点**：2026-08-19  
> **AEH 实现基线**：`YIMO691/aeh @ 6513102`  
> **AEH 软件版本**：`v0.1.0`（手册版本不等于软件版本）  
> **证据基线**：Phase 1.1 / protocol v1.6  
> **当前战略裁决**：`CONTINUE_BUT_NARROW — conditional`  
> **产品有效性**：`NOT_YET_PROVEN`

---

## 1. 这本手册解决什么问题

这不是一本“如何输入 `aeh change red`”的 CLI 手册。

它试图回答：

1. Agentic Coding 为什么产生新的工程可信性问题？
2. Context、Spec、Agent Harness、Runtime、Verification、Evaluation 各自负责什么？
3. AEH 应该负责什么、不应该负责什么？
4. 一次具体 Change 如何从 Agent 的“我完成了”变成可复核的工程接受判定？
5. AEH 自己如何证明值得存在，而不是靠功能数量和架构叙事自证？

本手册的最终问题只有一个：

> **如果删除 AEH，会失去哪一种其他层无法可靠提供的工程保证？**

当前候选答案是：

> **由 Generator 权限之外独立重算的 Change Acceptance Verdict。**

但这一答案仍需要 PoV、Adversarial Assurance 与 Cross-domain Validation 继续证明。

---

## 2. 三个层次必须分开

```text
Agent Claim
      ≠
Task Outcome
      ≠
Assurance Outcome
```

- `Agent Claim`：Agent 自己声称完成、测试通过、可以交付。
- `Task Outcome`：功能事实上是否满足验收。
- `Assurance Outcome`：证据、Oracle、Scope、Traceability、Approval 等是否足以支持工程接受。

[EVAL] Phase 1 RUN-D004 已观察到：功能与 Hidden Tests PASS、Agent 声称 COMPLETED，但外部 AEH Replay 因 Change State 返回 BLOCKED。来源：`EVAL-P1-D004-RAW`。

这不是 AEH 产品有效性的最终证明，但它证明三个结果变量不能混为一谈。

---

## 3. 证据标签

全文使用：

- `[EXT]`：外部官方资料、官方仓库、原始研究；
- `[AEH]`：AEH 当前源码、Schema、Release；
- `[EVAL]`：aeh-evals / PoV / Attack；
- `[DECISION]`：本手册的架构决策；
- `[HYPOTHESIS]`：尚待实验验证的假设。

所有关键 Source ID 可在附录 F 与 `references/source-registry.yaml` 中查到来源和版本。

---

## 4. 事实语气

### FACT

已有一手材料或当前源码直接支持。

### NORMATIVE

本手册建议冻结的架构不变量。

### HYPOTHESIS

尚待 PoV 或后续实验验证。

本手册禁止把 HYPOTHESIS 写成 FACT。

---

## 5. 推荐阅读路线

### 30 分钟：先理解本质

阅读：

```text
00 → 01 → 02 → 03 → 04 → 05
```

你会得到一句核心理解：

> **AI 负责干活；AEH 让过程可见、证据可查，并把最终接受权从 Generator 自报中分离出来。**

### 半天：理解 Change Assurance

继续：

```text
07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15
```

### 工程实现

继续：

```text
16 → 17 → 18 → 19 → 20 → 21
```

### 判断 AEH 是否值得继续

最后：

```text
22 → 23 → 24 → 25 → 26
```

---

## 6. 手册与 AEH 软件不是同一版本

```text
Handbook v0.2
AEH Software v0.1.0
PoV Protocol v1.x
```

三者独立演化。

---

## 7. 当前最重要的原则

> **The generator proposes.  
> The evidence records.  
> The verifier decides.**

以及：

> **Generator 可以越来越自由；Acceptance Authority 必须独立。**

---

## 8. 当前不应宣称的内容

截至本版，不能宣称：

- AEH 已显著提高 Coding Agent 成功率；
- AEH 已通过 A01–A08 正式攻击验证；
- AEH 已在 Unity / C# 大型存量项目证明有效；
- AEH 已具有强身份、深 CI、OS Sandbox；
- AEH 是市场上唯一 Change Assurance 方案。

准确状态：

> **问题具有高必要性；AEH 的独立产品价值尚在证明中。**

---

## 9. References

- `INT-DEEP-RESEARCH-20260818`
- `AEH-ARCH-6513102`
- `EVAL-P1-D004-RAW`
