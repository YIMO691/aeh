# 18 · Agent Adapter 与能力协商

> **章节类型**：BUILD / INTEGRATION  
> **状态**：H4_IMPLEMENTED_DRAFT  
> **核心原则**：`Adapter translates; it does not invent governance.`

---

# 1. 为什么需要 Adapter

不同 Coding Agent 的控制面不同。

例如：

```text
Codex
AGENTS.md
sandbox / approval
config / rules

Claude
CLAUDE.md
permission rules
hooks
sandbox

Gemini
policy engine
hooks
sandbox
```

如果 AEH 把每个平台自己的语义写进 Core：

> Core 会迅速 vendor-specific。

所以需要：

```text
Canonical AEH semantics
       ↓
Adapter
       ↓
Platform expression
```

---

# 2. Adapter 的冻结边界

[AEH][FACT] `render.py` 头部明确：

```text
Adapter 不重算 precedence
不解决 conflict
不修改 Profile/Workflow
只翻译
```

来源：`AEH-RUNTIME-ADAPTER-6513102`

因此：

```text
Policy Decision
应在 Adapter 之前完成。
```

Adapter 不是第二套 Policy Engine。

---

# 3. Canonical Semantics

当前 Renderer 从 Profile 提取：

```text
permissions.modify_source
permissions.git_commit
permissions.git_push
permissions.shell
permissions.web_access

testing.tdd
review.human_required_for
workflow.default_level
developer.plan_before_code
team.code_review_policy
```

来源：`AEH-RUNTIME-ADAPTER-6513102`

Codex 与 Claude 共用同一份 Canonical Semantics。

平台只能改变：

```text
表达方式
```

不能改变：

```text
最终语义
```

---

# 4. Capability Map

每个平台声明：

```text
field
channel
status
```

当前状态包括：

```text
ENFORCEABLE
GUIDANCE_ONLY
```

Doctor 还能够处理：

```text
UNENFORCEABLE
```

语义。

来源：

- `AEH-RUNTIME-ADAPTER-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`

---

# 5. Codex 当前能力声明

V0.1 Codex：

```text
permissions.modify_source
  sandbox
  ENFORCEABLE

permissions.git_commit
  approval
  ENFORCEABLE

permissions.git_push
  instruction
  GUIDANCE_ONLY

permissions.shell
  sandbox
  ENFORCEABLE

permissions.web_access
  sandbox
  ENFORCEABLE

review.human_required_for
  instruction
  GUIDANCE_ONLY
```

来源：`AEH-ADAPTER-CODEX-6513102`

注意：

> 这是 AEH V0.1 Adapter 对平台能力的声明，不应被理解成 OpenAI 官方对所有 Codex 版本永恒能力的描述。

---

# 6. Claude 当前能力声明

V0.1 Claude Adapter：

```text
modify_source
git_commit
git_push
shell
  → permission_rules / ENFORCEABLE

web_access
  → instruction / GUIDANCE_ONLY

review.human_required_for
  → instruction / GUIDANCE_ONLY
```

来源：`AEH-ADAPTER-CLAUDE-6513102`

同样，这是 AEH 当前声明。

---

# 7. Capability Honesty

[DECISION] `ADR-HB-019`

AEH 最危险的错误之一：

```text
Prompt 写了 “禁止 push”
→ 文档宣称 “AEH 强制禁止 push”
```

这不成立。

必须区分：

```text
GUIDANCE
NATIVE ENFORCEMENT
AEH DETECTION
EXTERNAL CI ENFORCEMENT
```

Capability Map 的价值不只是兼容。

它是：

> **控制强度真值。**

---

# 8. Deny 不得被降级

Renderer 明确：

```text
deny 不得放宽为 ask/allow
required 不得降级为 optional
```

来源：`AEH-RUNTIME-ADAPTER-6513102`

如果平台只能 Guidance：

```text
unsupported_capabilities
```

必须显式记录。

---

# 9. Doctor 如何使用 Capability Map

Doctor 对：

```text
required semantic = deny
```

进行检查。

如果：

```text
UNENFORCEABLE
```

则：

```text
BLOCKED
```

如果：

```text
GUIDANCE_ONLY
```

则：

```text
WARN
```

来源：`AEH-RUNTIME-DOCTOR-6513102`

这是非常重要的“诚实降级”设计。

---

# 10. 为什么 GUIDANCE_ONLY 有时仍能运行

不是所有 Guidance-only 都必须 BLOCK。

例如：

```text
human_required_for
```

可能需要：

```text
AEH Approval Gate
```

作为真正 Authority。

Adapter 中的 Prompt 只是提醒 Agent。

所以系统要问：

```text
这个控制最终由谁 enforce？
```

而不是机械要求每个字段都必须由 Agent 平台硬执行。

---

# 11. Minimum Disclosure

Adapter Renderer 只读取：

```text
effective constraint
ref IDs
```

不复制：

```text
private source text
```

来源：`AEH-RUNTIME-ADAPTER-6513102`

这对组织政策尤其重要：

```text
Agent 需要知道：
“production access = deny”

不一定需要知道：
完整公司安全制度正文。
```

---

# 12. Managed Section

Renderer 的 merge：

```text
保留用户原文
只维护 AEH marker 中间内容
```

重复运行幂等。

Malformed marker：

```text
MALFORMED_MANAGED_MARKERS
```

来源：`AEH-RUNTIME-ADAPTER-6513102`

这避免 AEH 把：

```text
Repository Instructions
```

整个变成自己的私有格式。

---

# 13. Capability Negotiation 的未来模型

建议长期把 Adapter 扩展为：

```yaml
capability:
  name: git_push_deny

  requested_semantic:
    effect: deny

  native:
    platform: codex
    support: enforceable

  fallback:
    - instruction
    - post_action_detection

  assurance:
    required: true
    actual: native_enforced
```

这是架构建议，不是 V0.1 Schema。

---

# 14. Adapter 与 AEH Core 的关系

错误：

```text
Codex Adapter:
自己定义 STANDARD / CRITICAL
自己决定 deny
自己判断 approval
```

正确：

```text
Core/Profile:
定义语义

Adapter:
翻译语义

Doctor:
检查能力可用性

Runtime/CI:
验证 Change Assurance
```

---

# 15. 新 Agent 接入原则

接 Gemini/Kimi/未来 Agent 时：

```text
1. 不复制一套 AEH Workflow

2. 建 capability declaration

3. 定义 platform expression

4. 证明语义等价/不放宽

5. 对无法 enforce 的字段诚实标记

6. Doctor 检查实际 capability state
```

---

# 16. Architecture Invariants

### ADP-INV-01

> **Adapters MUST translate compiled semantics; they MUST NOT become independent policy engines.**

### ADP-INV-02

> **A deny semantic MUST NOT be silently weakened.**

### ADP-INV-03

> **Unsupported or guidance-only controls MUST be reported explicitly.**

### ADP-INV-04

> **Private policy source text MUST NOT be copied merely because an Adapter needs the effective constraint.**

### ADP-INV-05

> **Adding an Agent platform MUST NOT require redefining AEH Core workflow semantics.**

---

# 17. 当前限制

Known Limitations：

```text
Codex git_push deny = GUIDANCE_ONLY
Claude web_access deny = GUIDANCE_ONLY
review.human_required_for = GUIDANCE_ONLY on both
```

来源：`AEH-KNOWN-LIMITATIONS-6513102`

这也是为什么手册不能写：

> “AEH 已经在所有平台拥有完整权限控制。”

---

# 18. References

- `AEH-RUNTIME-ADAPTER-6513102`
- `AEH-RUNTIME-DOCTOR-6513102`
- `AEH-ADAPTER-CODEX-6513102`
- `AEH-ADAPTER-CLAUDE-6513102`
- `AEH-KNOWN-LIMITATIONS-6513102`
- `EXT-GEMINI-POLICY-ENGINE`
- `EXT-GEMINI-HOOKS`
- `EXT-GEMINI-SANDBOX`
