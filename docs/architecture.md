# AEH 架构契约（Architecture Freeze）

> 状态：**PHASE_0_ARCHITECTURE_FROZEN**（Owner 批准，2026-08-14）
> 本文档为 AEH V0.1 的正式冻结基线，后续阶段不得自行修改；变更必须走新的 Architecture Decision 流程。
>
> 本文档是 AEH V0.1 的**规范性冻结**：以下内容在 V0.1 内不可随意更改，变更必须走新的 Architecture Decision 流程。
> 目标形态与目录明细见 `docs/repository-panorama.md`；本文档与其术语完全一致，若出现差异，以本文档冻结的边界为准并回修 v0.2。
>
> 本阶段不实现 `core/*.yaml`、`schemas/*.json`、Validator、Compiler、Adapter。下文出现的文件示例**仅示意结构，不代表已实现的 Contract**。

---

## 1. 冻结契约（21 条，P-01 ~ P-21）

### P-01 五层边界

| 层 | 职责 | 不得包含 |
|---|---|---|
| Core | 通用语义：工作流、状态机、Gate、优先级、分类、证据结构 | 公司/项目/用户硬编码 |
| Bootstrap | 仓库事实发现、渐进访谈、组织规则输入、冲突解析 | 目标项目的业务规则 |
| Project Profile | 用户项目 `.aeh/profile.yaml` + `.aeh/effective-workflow.yaml`，带 source/confidence 的 Canonical Configuration | Prompt 文本（Profile ≠ Prompt） |
| Adapter | 把 Profile 编译为 Codex/Claude 的薄入口与权限映射 | 第二套工作流定义 |
| Runtime | 技能、模板、CLI、Validators 的实际执行与强制 | 业务逻辑 |

### P-02 三层责任模型：Guidance / Normative Contract / Enforcement Engine

| 层 | 作用 | 载体 | 决定合法性 |
|---|---|---|---|
| Guidance | 告诉 Agent 应如何工作 | `policies/`、`skills/`、README、Prompt | 否 |
| Normative Contract | 定义什么状态/数据/迁移合法 | `core/*.yaml`、`schemas/*.json` | 定义合法性 |
| Enforcement Engine | 独立判定并阻止绕过 | `aeh` CLI、Validators、CI、工具权限 | 是 |

不可混淆：**Schema 定义合法性，Validator 独立执行判定；Schema 本身不是 Enforcement Engine。policy 是建议，永远不等价于强制。**

### P-03 四层角色：LLM / Contract / Validator / Evidence

| 角色 | 职责 | 载体 |
|---|---|---|
| LLM | Reasoning：发现、建议、解释、执行 | Codex / Claude / 其他 Agent |
| Contract | 定义合法状态与数据（legality） | `core/` + `schemas/` |
| Validator | 独立重算与强制（independent enforcement） | `aeh validate-*` / `aeh doctor` / CI |
| Evidence | 可复核事实（reproducibility） | Git base SHA + 文件 Hash + Test Output + Change Artifacts |

注意：**Git 是最强 Evidence Carrier 之一，但 Evidence 不等于必须 Commit**（见 P-14）。

### P-04 安装拓扑

```text
公共 AEH 仓库（adaptive-engineering-harness）
    ↓ clone / checkout
aeh bootstrap <target-repo>
    ↓ Discovery + Interview + Conflict Resolution + Profile Compiler
    ↓ 安装 versioned runtime snapshot（.aeh/runtime/）
用户项目 .aeh/（manifest + profile + effective-workflow + generated adapters）
    ↓
Codex / Claude 在用户项目中运行
```

四个视角不可混为一谈：**公共 Harness ≠ 用户项目配置 ≠ Agent Prompt ≠ 单次任务工件。**

### P-05 机器真值边界

- 任何 Validator 必须判定的核心事实，必须使用 **YAML/JSON**，且必须有 Schema；
- **Markdown 只用于人类叙述**（evidence.md、design.md、decisions.md、review.md）；
- Markdown 可以引用机器 ID（如 REQ-001），但不得成为唯一 Gate 真值；
- 机器真值文件清单（V0.1 冻结）：`manifest.yaml`、`profile.yaml`、`effective-workflow.yaml`、`change.yaml`、`bugfix.yaml`、`spec.yaml`、`test-plan.yaml`、`tasks.yaml`、`traceability.yaml`、`verification.yaml`、`approvals.yaml`。

### P-06 Core 零硬编码

`core/` 与 `schemas/` 内**禁止出现任何特定公司、项目、用户、平台业务规则**。公司规则只能以「被编译的输入」形式存在，不写入公共 Core。

### P-07 Rule Precedence

```text
System / Tool Safety
    > Organization
    > Project
    > Team
    > Task
    > Developer
    > Harness Default
```

### P-08 同级冲突

同一优先级级别的规则冲突（如 Organization A vs Organization B）必须输出 **BLOCKED_POLICY_CONFLICT**。后续只能由**有权裁决该规则层级的授权主体（authorized policy authority）**处理；若当前会话无法确认具备该权限，则保持阻塞或输出 `USER_DECISION_REQUIRED` 以请求具备权限的 Owner/Policy Authority 介入。**禁止 Agent 静默选择，也禁止普通开发者越权裁决组织级政策。**

### P-09 Manifest

`.aeh/manifest.yaml` 必须记录：harness name/version、**source_revision（git sha）**、compiler version、schema version、installed_at，以及所有真正参与 Bootstrap / Compile / Runtime 的输入摘要。V0.1 不强制固定为某几个目录名，至少要覆盖 `runtime`、`compiler`、`bootstrap_contract`、`adapters` 的 digest/source manifest。目的：可升级、可复现、可回答"这项目由哪版 AEH、哪组契约与编译器生成"。

### P-10 Effective Workflow

公共默认语义 = `core/workflow.yaml`；用户项目最终生效 = `.aeh/effective-workflow.yaml`。编译分为两层，禁止循环依赖：

```text
Repository Facts
+ Organization Rules
+ Project Rules
+ Team Rules
+ Developer Preferences
+ Harness Defaults
    ↓
Profile Compiler
    ↓
.aeh/profile.yaml
```

然后：

```text
core/workflow.yaml
+ .aeh/profile.yaml
    ↓
Workflow Compiler
    ↓
.aeh/effective-workflow.yaml
```

`Task Rules` 属于单个 `CHG-*` 生命周期，只能在运行时与项目级 `effective-workflow.yaml` 合成 Change 级有效规则，**不得反向污染项目级 Profile 或 effective-workflow**。二者禁止同名，防止 Source/Effective 混淆。

### P-11 Bootstrap 幂等

相同输入（AEH version、仓库状态、用户回答、组织规则）重复运行 `aeh bootstrap`，输出不得产生意外 diff。`installed_at` 仅表示首次安装时间，不得因无变化重跑而刷新；若未来增加 `recompiled_at`，只有实际输入/编译结果变化时才允许更新。若所有输入 digest 均未变化，Bootstrap 不应重写 Manifest 或生成无意义 diff。

### P-12 非破坏式 Adapter 合并

已有 `AGENTS.md` / `CLAUDE.md` 的原文**必须保留**；AEH 只维护标记块内内容：

```markdown
<!-- AEH:BEGIN MANAGED -->
AEH generated content
<!-- AEH:END MANAGED -->
```

与 AEH Profile 冲突的既有规则：记录 conflict → 按来源级别判定 → 无法自动判定则阻塞，**禁止静默重写用户原文**。

### P-13 Private Policy 最小披露

```text
Private Source → Policy Normalizer → Effective Constraint → Profile/Effective Workflow
→ Agent 只见最小必要约束
```

私有规则原文仅存 `.aeh/private/`（默认 gitignore）；**不得默认复制组织制度正文**到 AGENTS.md、CLAUDE.md、Change Evidence 或公开日志。保留 redaction、minimum disclosure、no secret echo；private ref 只保存 ID。

### P-14 RED Evidence 不依赖 Commit

RED 证据必须至少包含：`base_commit` + `changed_files_hash` + `test_files_hash` + `command` + `exit_code` + `output_ref`（原始输出路径）+ `output_hash`（原始输出内容哈希）+ expected/actual failure 分类。`commit` 字段**可选**：Profile 允许 commit 时记录 sha，禁止时仅凭 repository/file hash + command + exit_code + output_ref/output_hash 即可形成可复核证据。

### P-15 Test Lock 时序

冻结时序：**`VALID_RED → LOCK_TEST → GREEN`**。禁止 GREEN 后才锁测试。Green 期间 tests 与 spec 只读，生产代码按 allowlist 修改；测试变化 → `BLOCKED_TEST_CHANGED`；确需改测试/规格必须走 `TEST_REPAIR` / `SPEC_REPAIR` 重新审批与 RED。

### P-16 INVALID_RED 分类路由

```text
INVALID_RED_TEST_DEFECT        → TEST_DESIGN
INVALID_RED_SPEC_MISMATCH      → SPEC_REPAIR
INVALID_RED_ENVIRONMENT        → BLOCKED_ENVIRONMENT
INVALID_RED_FIXTURE            → TEST_SETUP
INVALID_RED_UNEXPECTED_FAILURE → INVESTIGATE
VALID_RED                      → LOCK_TEST
```

不止要知道"红了"，还要知道"为什么红"，并按原因路由。

### P-17 Critical Human Gate 机器可读

Critical 的人工批准必须写入 `.aeh/changes/CHG-*/approvals.yaml`（gate / status / actor / decided_at / evidence_ref）。只有**可信审批写入路径（trusted human approval path）**可以把 required gate 写为 `APPROVED`；普通 Runtime Agent 不得直接把审批状态改成 APPROVED。Validator 规则：Critical + required approval ≠ APPROVED → **BLOCKED_HUMAN_APPROVAL_REQUIRED**。对话中的口头批准不作为机器证据。V0.1 的 `approvals.yaml` 是 human attestation record，不等同于密码学身份认证；签名/OIDC/企业审批集成属于未来扩展。

### P-18 每个 Change 独立状态

状态全部保存在 `.aeh/changes/CHG-YYYY-NNNN/` 各自目录；**不存在单一"全局当前 Change"**。CLI 支持 `--change` 显式指定或从 worktree 上下文推导。支持多 worktree、多 Agent、多并行任务。

### P-19 单一 CLI 入口

V0.1 用户入口统一为 `aeh` CLI：`bootstrap / doctor / validate / verify / change` 子命令族。不向用户暴露散落脚本；原 sdd-selfcheck 的 Python 严格链只作为 Validator 内部原型迁移。

### P-20 V0.1 范围边界

**不做**：Web 后台、数据库、RAG、SaaS、全自动多 Agent Orchestrator、自研 Coding Agent、自动修改公司政策、Spec 全项目生成。
**做**：Git 仓库 + Markdown + YAML/JSON Schema + 少量 Validator 代码 + Agent Instructions + Bootstrap Skills + Templates。

### P-21 Trusted Mutation Boundary（可信写入边界）

AEH 不仅要定义“什么是真值”，还必须定义“谁有权修改真值”。所有机器真值与运行时 Contract 均采用最小写权限模型：

| 资产 | 允许修改主体 | 普通 Runtime Agent |
|---|---|---|
| `.aeh/runtime/core/**` | Bootstrap / Upgrade trusted path | 禁止 |
| `.aeh/runtime/schemas/**` | Bootstrap / Upgrade trusted path | 禁止 |
| `.aeh/manifest.yaml` | Installer / Compiler trusted path | 禁止直接编辑 |
| `.aeh/profile.yaml` | Profile Compiler | 禁止直接编辑生效值 |
| `.aeh/effective-workflow.yaml` | Workflow Compiler | 禁止直接编辑 |
| `approvals.yaml` 中 `APPROVED` | Trusted Human Approval Path | 禁止 |
| `change.yaml.state` | AEH State Transition command / Validator-mediated path | 禁止绕过状态机直接写 |
| `spec.yaml` | SPEC / SPEC_REPAIR 阶段授权路径 | 非该阶段禁止 |
| 测试文件 | RED / TEST_REPAIR 阶段授权路径 | GREEN 阶段只读 |
| 生产代码 | GREEN / REFACTOR 阶段 allowlist | 非对应阶段禁止 |
| `verification.yaml` | VERIFY 授权路径 | 非 Verify 阶段禁止伪造 |

Validator 在执行关键 Gate 前必须能够核对当前 runtime/core/schema 等关键 Contract 与 `manifest.yaml` 记录的 digest/source manifest 是否一致；若 Contract 被未授权篡改，必须阻塞，而不是基于“被换过的裁判规则”继续判 PASS。

RED 完成并进入 LOCK_TEST 后、Coding Agent 开始实现之前，Controller 必须在受管仓库
之外封存 Change 工作区内 YAML/JSON 机器真值的路径集合与内容哈希。GREEN、VERIFY、
REVIEW 与此后的可信批准路径先核对该检查点；新增、删除、修改、符号链接或检查点缺失
一律 fail closed。各合法 Controller 写路径完成后推进检查点。检查点目录
不得位于目标仓库内，因为同一写入者可同时伪造仓库内工件与仓库内哈希。

冻结原则：

> **Machine Truth + Validator 只有在 Trusted Mutation Boundary 存在时才构成真正 Enforcement。**

---

## 2. 三层责任模型与四层角色的精确语义

```text
states.yaml  定义"什么迁移合法"          Validator 判断"当前迁移是否合法"
schema       定义"数据结构合法条件"        Validator 判断"当前文件是否符合结构"
policy       告诉 Agent"应该做什么"        policy 本身不能等价于强制
```

反模式（V0.1 明令禁止）：

1. 把 Schema 称为 Enforcement Engine；
2. 用更长的 Prompt 替代机器 Gate；
3. 让 Validator 信任 Agent 自报"已完成 RED"而不核对工件/证据/审批；
4. 让 Markdown 成为唯一 Gate 真值；
5. 允许 Runtime Agent 直接改 machine truth / approvals / runtime contract 后再让 Validator 对修改后的规则判 PASS；
6. Validator 不核对 manifest/runtime contract digest 就继续执行关键 Gate。

---

## 3. 安装拓扑与版本契约

- 公共仓库通过 `aeh bootstrap <target>` 将 **versioned runtime snapshot** 装入用户项目 `.aeh/runtime/`（core/schemas/skills）；
- `.aeh/manifest.yaml` 记录 harness/compiler/schema version、source_revision，以及覆盖 runtime/compiler/bootstrap_contract/adapters 的 digest/source manifest（见 P-09）；
- 升级必须显式执行 `aeh upgrade`（V0.1 预留 manifest 字段与版本约束，不要求完整实现）；
- Bootstrap 幂等（P-11）；`installed_at` 仅首次安装写入，无输入变化时不刷新；升级不得静默覆盖用户配置。

---

## 4. 机器真值与人类叙述清单

### 机器真值（必须有 Schema、可被 CLI 独立重算）

```text
.aeh/manifest.yaml
.aeh/profile.yaml
.aeh/effective-workflow.yaml
.aeh/changes/CHG-*/change.yaml
.aeh/changes/CHG-*/bugfix.yaml        (Lightweight)
.aeh/changes/CHG-*/spec.yaml          (Standard/Critical)
.aeh/changes/CHG-*/test-plan.yaml
.aeh/changes/CHG-*/tasks.yaml
.aeh/changes/CHG-*/traceability.yaml
.aeh/changes/CHG-*/verification.yaml
.aeh/changes/CHG-*/approvals.yaml     (Critical)
```

### 人类叙述（Markdown，可引用机器 ID，不可反向成为 Gate 真值）

```text
.aeh/changes/CHG-*/evidence.md
.aeh/changes/CHG-*/design.md          (Critical)
.aeh/changes/CHG-*/decisions.md       (Critical)
.aeh/changes/CHG-*/review.md          (Critical)
```

Lightweight 工件唯一冻结为：`change.yaml + bugfix.yaml + test-plan.yaml + verification.yaml`（bugfix.yaml 内含 problem/acceptance/scope，不生成完整 spec.yaml）。

---

## 5. Profile / Workflow / Change 三层编译作用域

V0.1 冻结三种不同生命周期，禁止把 precedence 与 compilation scope 混为一谈。

### 5.1 Project Profile

输入：

```text
Repository Facts
+ Organization Rules
+ Project Rules
+ Team Rules
+ Developer Preferences
+ Harness Defaults
```

输出：

```text
.aeh/profile.yaml
```

Profile 表示“这个项目长期有效的配置与约束”。

### 5.2 Project Effective Workflow

输入：

```text
core/workflow.yaml
+ .aeh/profile.yaml
```

输出：

```text
.aeh/effective-workflow.yaml
```

表示 Core 工作流在当前项目中的有效编译结果。

### 5.3 Per-Change Effective Rules

输入：

```text
.aeh/effective-workflow.yaml
+ CHG Task Rules
+ Change Classification
+ Change-specific approvals/constraints
```

输出可以在 V0.1 由 Runtime 内存计算，未来也可落盘为：

```text
.aeh/changes/CHG-*/effective-rules.yaml
```

**Task Rules 不得写回项目级 Profile 或 effective-workflow。**

---

## 6. 未来文件示例（仅示意，非已实现 Contract）

> 以下示例只为让审查者看到目标形态；Phase 1 才会正式实现 core/*.yaml 与 schemas/*.json。

### 6.1 core/states.yaml（示意）

```yaml
states:
  - GROUND
  - SPEC
  - RED
  - LOCK_TEST
  - GREEN
transitions:
  - from: GROUND
    to: SPEC
  - from: RED
    to: LOCK_TEST
  - from: LOCK_TEST
    to: GREEN
illegal_examples:
  - GROUND -> GREEN
  - SPEC -> DONE
```

### 6.2 .aeh/profile.yaml 配置项（示意）

```yaml
git:
  push:
    value: deny
    source:
      type: organization_policy
      ref: ORG-GIT-001
    confidence: confirmed
```

### 6.3 .aeh/manifest.yaml（示意）

```yaml
harness:
  name: adaptive-engineering-harness
  version: "0.1.0"
  source_revision: "<git-sha>"
compiler:
  version: "0.1.0"
schema:
  version: "1"
installed_at: "<timestamp>"
source_hashes:
  runtime: "<sha256>"
  compiler: "<sha256>"
  bootstrap_contract: "<sha256>"
  adapters: "<sha256>"
```

### 6.4 change.yaml 状态（示意，每 Change 独立）

```yaml
change_id: CHG-2026-0001
state:
  current: RED
  previous: TEST_DESIGN
gates:
  classification: PASS
  grounding: PASS
  spec: PASS
  red: ACTIVE
```

### 6.5 RED Evidence（示意，commit 可选）

```yaml
red:
  test_id: TEST-014
  command: "..."
  exit_code: 1
  expected_failure:
    category: behavior
    signature: "duplicate debit"
  actual_failure:
    category: behavior
    signature: "duplicate debit"
  repository_state:
    base_commit: "<sha>"
    changed_files_hash: "<sha256>"
    test_files_hash: "<sha256>"
  output_ref: "evidence/red-TEST-014.log"
  output_hash: "<sha256>"
  commit: null
  verdict: VALID_RED
```

### 6.6 approvals.yaml（示意）

```yaml
approvals:
  - gate: SPEC_REVIEW
    status: APPROVED
    actor:
      type: human
      id: owner
    decided_at: "<timestamp>"
    evidence_ref: DEC-001
  - gate: MERGE_GATE
    status: PENDING
```

---

## 7. Architecture Decision Records（10 个关键决策）

### ADR-001 机器真值：YAML/JSON，而非 Markdown

- **Decision**：Validator 必须判定的核心事实全部使用 YAML/JSON + Schema；Markdown 仅人类叙述。
- **Why**：Markdown 无 Schema、语义不可 diff、Agent 可自由改写、Validator 无法独立重算；YAML/JSON 可校验、可重算、可追溯。
- **Rejected Alternative**：Markdown-as-truth（旧 sdd-agent-kit 模式）；关键字段散落在 md 中的混合模式。
- **Consequence**：叙述文档需引用机器 ID；不存在 spec.md（只有 spec.yaml）；模板与 Schema 双写由 Phase 1 统一管理。
- **Future Extension Boundary**：若未来需要富文本规格，只允许从 YAML 渲染生成 Markdown，禁止反向。

### ADR-002 Guidance / Normative Contract / Enforcement Engine 三层分离

- **Decision**：三层分离；policy 不强制；Schema 定义合法性但不等于强制；Validator 独立判定并阻止绕过。
- **Why**：防止"Prompt 越长越安全"的错觉；Contract 与 Enforcement 分离后各自可测、可替换；宿主权限（allow/deny、sandbox）是 enforcement 的最后落地。
- **Rejected Alternative**：两层模型（Guidance/Enforcement）把 Schema 混入 Enforcement；Prompt-as-enforcement。
- **Consequence**：policies/ 只写建议；core/+schemas/ 只写契约；src/aeh/validators/ 只做判定；三者独立演化。
- **Future Extension Boundary**：CI / git hooks 作为 Enforcement 的额外 carrier，复用同一 validator 库。

### ADR-003 Snapshot 安装模型

- **Decision**：bootstrap 将 harness runtime（core/schemas/skills）以 versioned snapshot 安装到 `.aeh/runtime/`，manifest.yaml 记录版本、source_revision，以及覆盖 runtime/compiler/bootstrap_contract/adapters 的 source manifest/digest。
- **Why**：公共仓库升级不破坏已装项目；Profile 来源可复现；用户项目离线可用、不依赖远程路径。
- **Rejected Alternative**：引用公共仓库路径；要求用户永远在 AEH 仓库内工作；git submodule。
- **Consequence**：升级必须显式 `aeh upgrade`；每个用户项目存在少量 runtime 副本。
- **Future Extension Boundary**：增量升级、多版本并存、回滚。

### ADR-004 非破坏式 Adapter 合并

- **Decision**：AGENTS.md/CLAUDE.md 只维护 AEH Managed Section（BEGIN/END 标记）；用户原文保留；冲突按来源级别判定，无法自动判定则阻塞。
- **Why**：用户既有规则是事实资产；覆盖 = 数据丢失 + 信任损失；无标记 append 无法幂等。
- **Rejected Alternative**：全量覆盖；无标记 append；生成 .aeh/managed.md 要求用户手动 include。
- **Consequence**：需要 merge-rules.yaml；幂等性依赖 managed section 的确定性生成。
- **Future Extension Boundary**：目录级 nested AGENTS.md 分段管理（V1 之后）。

### ADR-005 RED Evidence 不依赖必须 Commit

- **Decision**：RED 证据 = base_commit + changed_files_hash + test_files_hash + command + exit_code + output_ref + output_hash + 预期/实际失败分类；commit 字段可选。
- **Why**：多数团队不允许 Agent 自由 commit；证据链不能依赖权限；未提交工作区同样可复核。
- **Rejected Alternative**：必须 commit 才能算 RED；只记录"测试红了"一句话。
- **Consequence**：RED Validator 需要计算文件哈希；工作区脏状态也可验证。
- **Future Extension Boundary**：签名证据、CI 端重算、跨机器证据比对。

### ADR-006 人工批准使用机器可读 approvals.yaml

- **Decision**：Critical 的人工 Gate 写入 approvals.yaml（gate/status/actor/decided_at/evidence_ref）；只有 trusted human approval path 可以写入 `APPROVED`，普通 Runtime Agent 不得直接写；Validator 检查 required approval 是否 APPROVED。
- **Why**：批准必须可被机器检查、可审计；防止"对话里口头批准"证据丢失。
- **Rejected Alternative**：decisions.md 自然语言；聊天记录/口头批准。
- **Consequence**：需要 approvals.schema；未来由一个可信审批命令/受控写入路径记录批准，具体 CLI 命令名不在 Phase 0 冻结。
- **Future Extension Boundary**：多级审批链、签名验证、OIDC/企业审批集成、批准时效（TTL）。

### ADR-007 Private Policy 最小披露

- **Decision**：私有规则原文仅存 `.aeh/private/`（gitignore），经 Policy Normalizer 编译为最小 effective constraint（deny/approval 级别）；Agent 只见最小约束；日志/证据/Adapter 不复制原文。
- **Why**：最小权限；防泄露；原文仍是唯一权威，只暴露"约束"不暴露"制度"。
- **Rejected Alternative**：直接引用私有全文；放 private 目录但 Adapter 照抄正文。
- **Consequence**：编译层增加 normalizer/redaction 职责；Profile 中私有项只存 ref ID 与 effective 值。
- **Future Extension Boundary**：加密存储、按角色投影、审计日志脱敏。

### ADR-008 每个 Change 独立状态（无全局当前 Change）

- **Decision**：状态全部保存在 `.aeh/changes/CHG-*/` 各自目录；禁止全局"当前 Change"；CLI 默认从 worktree 上下文推导或要求 `--change`。
- **Why**：多 worktree、多 Agent、多并行任务；状态互不污染、互不覆盖。
- **Rejected Alternative**：单一全局状态文件；环境变量记录当前 Change。
- **Consequence**：doctor 等命令 change-aware；每 Change 工件自包含。
- **Future Extension Boundary**：Change 依赖图、跨 Change 锁定与合并检测。

### ADR-009 单一 aeh CLI

- **Decision**：V0.1 用户入口统一为 `aeh` CLI（bootstrap / doctor / validate / verify / change），内部模块化（src/aeh/）。
- **Why**：用户体验一致；版本化入口；吸取 sdd-selfcheck 散脚本难发现的教训。
- **Rejected Alternative**：多个散落脚本；每个功能一个独立命令包。
- **Consequence**：CLI 保持薄，核心逻辑在可测试的库模块内。
- **Future Extension Boundary**：子命令插件扩展、非交互模式、CI 集成。

### ADR-010 Trusted Mutation Boundary / TCB

- **Decision**：所有 Machine Truth、Runtime Contract 与 Gate 状态采用最小写权限；关键资产只能由对应 trusted path 修改。普通 Runtime Agent 不得通过直接编辑 `manifest/profile/effective-workflow/approvals/state/runtime core/schemas` 绕过 Compiler、State Machine 或 Human Approval。
- **Why**：如果 Agent 可以先修改“裁判规则”或“审批记录”，再运行 Validator，则 Machine Truth + Validator 会退化成形式约束；真正 Enforcement 必须包含可信写入边界。
- **Rejected Alternative**：只依赖 Prompt 告诉 Agent“不要改”；允许任意 Agent 直接编辑 YAML 再由 Validator 验证；只校验 Schema 不校验 Contract digest。
- **Consequence**：Bootstrap/Upgrade、Compiler、State Transition、Approval、RED/GREEN/VERIFY 各自需要明确写权限；Validator 在关键 Gate 前需核对 runtime/core/schema digest 与 manifest 记录一致。
- **Future Extension Boundary**：OS 文件权限、worktree ACL、sandbox capability、签名 manifest、CI 远端重算、企业 TCB/attestation。

---

## 8. 自检（Phase 0 红线）

| # | 检查项 | 结果 | 依据 |
|---|---|---|---|
| 1 | core/ 设计零特定引擎/框架/公司/项目硬编码规则 | PASS | P-06；本文零此类硬编码 |
| 2 | 无 spec.md + JSON Schema 机器真值冲突 | PASS | P-05：机器真值只有 spec.yaml |
| 3 | Schema 不被当作 Enforcement Engine | PASS | P-02/§2 反模式 1 |
| 4 | RED 不默认必须 commit | PASS | P-14 / ADR-005 |
| 5 | 不允许覆盖现有 AGENTS.md/CLAUDE.md | PASS | P-12 / ADR-004 |
| 6 | 不把公司私有规则全文复制给 Agent | PASS | P-13 / ADR-007 |
| 7 | 不存在"全局当前 Change" | PASS | P-18 / ADR-008 |
| 8 | 无 GREEN → Test Lock 错误时序 | PASS | P-15：VALID_RED → LOCK_TEST → GREEN |
| 9 | Lightweight 工件前后定义一致 | PASS | §4：唯一冻结为 4 件套 |
| 10 | INVALID_RED 有分类路由 | PASS | P-16 |
| 11 | Critical 人工 Gate 用 approvals.yaml | PASS | P-17 / ADR-006 |
| 12 | Bootstrap 幂等 | PASS | P-11 |
| 13 | 单一 CLI 入口 | PASS | P-19 / ADR-009 |
| 14 | Trusted Mutation Boundary 已定义 | PASS | P-21 / ADR-010 |
| 15 | Profile / Workflow / Task 编译作用域无循环 | PASS | P-10 / §5 |
| 16 | Critical APPROVED 只能由 trusted human path 写入 | PASS | P-17 / ADR-006 |
| 17 | RED 原始输出有 exit_code + output_hash 完整性 | PASS | P-14 / ADR-005 |
| 18 | Manifest digest 覆盖 runtime/compiler/bootstrap/adapters | PASS | P-09 / ADR-003 |
| 19 | Bootstrap 时间字段不破坏幂等 | PASS | P-11 |
| 20 | Organization 同级冲突只能由 authorized authority 裁决 | PASS | P-08 |
| 21 | Phase 0 未通过前不创建正式 core/*.yaml | PASS | 本文只有"示意"示例，无实现文件 |

---

## 9. Phase Gate

```text
PHASE_0_ARCHITECTURE_FROZEN（Owner 批准，2026-08-14）
    ↓
Phase 1: Core Contract + Schema Skeleton（仅允许实施冻结契约，禁止新设计）
```

Owner 已批准：允许进入 `PHASE_1_CORE_CONTRACT`。Phase 1 只把 P-01~P-21 与 ADR-001~ADR-010 翻译为 Contract，不得修改已冻结架构。
