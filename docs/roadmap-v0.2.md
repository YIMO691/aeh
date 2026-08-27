# AEH V0.2 Roadmap

> 状态：**V02-0 + M1–M3 MERGED；M4 LOCAL VERIFIED / NOT MERGED；V0.2.0 GITHUB RELEASED；V0.2.1 INTEGRITY PATCH CANDIDATE；PYPI NOT PUBLISHED**（2026-08-26）
> 本文档是 V0.2 的**规划输入**，不是冻结契约。任何里程碑开工前，仍须独立走完
> 规范驱动开发六阶段（SPEC/PLAN/Gate/实现/验证/审查）并按需新增 CD/RISK 决策记录。
> V0.1 线保持 Feature Freeze：只收 P0/P1 release blocker、安全、安装/CLI/跨平台
> 与文档修复，不下沉任何 V0.2 功能。

---

## 1. 10 秒结论

- 现状：V0.1.0 已发布（`docs/releases/v0.1.0/RELEASE_TEST_REPORT.md`：232/232）。
- Phase 1.1：v1.6 冻结协议与 External Runner 最小机制已验证；在该基线冻结时 72-run
  尚未授权，后续 Phase 2 v1.10 已完成并给出 `REPOSITION`。
- **M1–M3 已按依赖顺序审查并合并到 main；v0.2.0 已发布。Phase 2 暴露的
  RUN-F055 机器真值逃逸已在 main 修复，当前软件包为未发布的 v0.2.1 candidate。**
- M1 提供 wheel/CI，M2 提供显式 repair/transaction，M3 提供 v0.1 snapshot 到当前
  candidate 的显式 upgrade。独立 Release Safety Review 已通过，Owner 已执行 v0.2.0
  tag 与 GitHub Release；PyPI 未授权、未发布。v0.2.1 仅收口已观察完整性缺陷；M4 已在
  独立授权、SPEC/PLAN 和本地 feature branch 下实施，尚未获得 push/merge/release 授权。
- 顺序总览：`V02-0 → M1 → M2 → M3 → M4 → M5 → M6`，一次只开一个 M。

## 2. 输入与约束

| 输入 | 作用 | 位置 |
|---|---|---|
| Feature Freeze | V0.1 只收修复，V0.2 功能不得下沉 | `CONTRIBUTING.md`「V0.1 feature freeze」 |
| 已知限制 #1–13 | 候选池的直接来源 | `docs/releases/v0.1.0/KNOWN_LIMITATIONS.md` |
| P2 四项 / RISK-022~024 | 发布时接受的欠账 | `docs/decisions.md` |
| 冻结架构 | upgrade 语义、manifest 版本/digest、写入边界已预留 | `docs/architecture.md` ADR-003/P-09 |
| V0.2 目标形态 DRAFT | 远期目录形态参考 | `docs/repository-panorama.md` |
| 回归基线 | 232/232，Python 3.10+ | `docs/releases/v0.1.0/RELEASE_TEST_REPORT.md` |
| Design & Evidence Baseline | Handbook v0.2；AEH 软件仍为 v0.1.0 | `docs/handbook/` |
| Phase 1.1 | v1.6；PHASE_1_1_FROZEN_AND_REPLAYED；72-run unauthorized | `aeh-evals reports/PHASE_1_1_CLOSURE.md` |

约束：本文不承诺日期/人员/版本号；只给依赖顺序、复杂度档位与退出条件。
术语与 README/architecture.md 一致。复杂度口径见 §5。

## 3. 候选池（全量盘点，20 条）

来源缩写：C=CONTRIBUTING；KL=KNOWN_LIMITATIONS #n；P2/RISK=decisions.md；
ADR/SEAM=架构预留或代码接缝。**每条候选去向三选一：M1–M6 / 候选池 / 拒绝。**

| ID | 名称 | 来源 | 复杂度 | 契约影响 | 去向 |
|---|---|---|---|---|---|
| V02-C-001 | 安装修复/恢复子系统（aeh repair） | KL#5, C | L | Y | M2 |
| V02-C-002 | 升级系统（aeh upgrade） | KL#6, C, ADR-003/P-09, SEAM | L | Y | M3 |
| V02-C-003a | AEH 自身 CI 回归门 | KL#7, C, SEAM | S | N | M1 |
| V02-C-003b | 用户项目 CI 深集成 | KL#7, C | L | N | M6 |
| V02-C-004 | RAG 证据检索 | C | XL | N | 候选池 |
| V02-C-005 | Web UI | C | XL | N | 候选池 |
| V02-C-006 | Mutation testing | C | L | N | 候选池 |
| V02-C-007 | Impact analysis | C | L | N | 候选池 |
| V02-C-008 | 多代理编排器 | KL#9, C | XL | Y | M6 |
| V02-C-009a | 批准凭据最小强化（TTL/撤销/审计） | KL#1, P2, RISK-023 | M | Y | M4 |
| V02-C-009b | 强审批身份（签名/凭据校验） | KL#1, ENF-APPROVAL-001, RISK-023 | XL | Y | M5 |
| V02-C-010 | 新 workflow levels | C | XL | Y | 候选池 |
| V02-C-011 | Manual 验证独立批准 gate | KL#10, P2, RISK-022, CD-097 | M | Y | M4 |
| V02-C-012 | Bootstrap 原子应用/应用日志 | KL#3 | M | N | M2 |
| V02-C-013 | CRITICAL plan 强制校验/模板 | KL#13, P2, SEAM | S | N | M4 |
| V02-C-014 | 可迁移 wheel 打包 | KL#11, P2, RELEASE-FIX-001, SEAM | M | N | M1 |
| V02-C-015 | Adapter 能力升级（GUIDANCE_ONLY→enforce） | KL#2, C | S/M | N | 候选池 |
| V02-C-016 | 分类升级为证据分类 | KL#12 | M | Y | 候选池 |
| V02-C-017 | 工作流 repair 命令 UX | SEAM（states.yaml 已有 TEST_REPAIR/SPEC_REPAIR） | S | N | M2 |
| V02-C-018 | 自动 merge/push/PR | KL#8 | — | — | 拒绝 |
| V02-C-020 | 命令执行沙箱 | KL#4, RISK-EXEC-001, README §12 | L | N | M5 |

覆盖核对：CONTRIBUTING V0.2 清单 10 项、KNOWN_LIMITATIONS #1–#13、P2 四项全部
逐条映射到上表；每条候选均有仓库内可循证引用（原始盘点与逐条核对见任务证据包）。

## 4. 优先级模型

公式（Owner 已批准 Q-004）：

`score = (痛点×20 + 安全×25 + 成本×15 + 契约×15 + 依赖×10 + 回退×15) / 100`

- 每维 1–5。反向计分：成本（5=最便宜）、契约影响（5=零契约变更）、依赖（5=无前置）。
- 平局规则：安全分高者优先 → 痛点分高者优先 → 维持原 ID 序。
- 评分只给顺序；里程碑分组还叠加主题与依赖约束（例如 C-015 受外部平台能力约束入池）。

### 排序结果（降序）

| 排名 | ID | 总分 | 一句话理由 |
|---|---|---|---|
| 1 | C-003a | 4.35 | 自身 CI 是后续所有 M 的回归护栏，成本最低 |
| 2 | C-013 | 4.25 | 一行级强制校验即可关闭 CRITICAL plan 补救缺口 |
| 3 | C-009a | 4.20 | 安全分 5；TTL/撤销给证词级批准加最小可信度 |
| 4 | C-014 | 4.05 | wheel 解除 editable-only 限制并支撑 CI 分发 |
| 5 | C-017 | 4.00 | 状态机已备好，只差命令 UX |
| 6 | C-011 | 3.85 | manual 验证独立 gate，关闭 P2 欠账 |
| 7 | C-012 | 3.80 | 应用日志让安装可审计，也是 repair 前置 |
| 8 | C-001 | 3.75 | repair 价值最高，跨模块成本 L |
| 9 | C-020 | 3.55 | 平局裁决：安全 5 > C-015 的 3 |
| 10 | C-015 | 3.55 | 受外部平台能力约束，入池 |
| 11 | C-003b | 3.45 | 依赖 M1/M3 支撑 |
| 12 | C-002 | 3.30 | 依赖项压制得分，顺序在 M2 之后 |
| 13 | C-016 | 3.20 | 触 frozen classifications 契约 |
| 14 | C-009b | 3.10 | 成本最高档，依赖 M4 |
| 15 | C-007 | 3.05 | 依赖 upgrade + CI 深集成 |
| 16 | C-006 | 2.85 | 依赖 CI 深集成 |
| 17 | C-005 | 2.65 | 成本 XL，CLI 先行 |
| 18 | C-004 | 2.60 | 依赖深集成与证据语料 |
| 19 | C-008 | 2.35 | 平台级成本；Q-003 保留在 M6，开工前复核 |
| 20 | C-010 | 1.75 | 契约级扩展，V0.2 内不启动 |

完整 6 维打分与复算证据见任务证据包（20 行重算 0 不匹配）。

## 5. 复杂度口径

S=≤2 文件小改动；M=单模块/单命令；L=跨多模块+契约决策；XL=跨里程碑平台级能力。

## 6. 里程碑与依赖

一次只开一个 M；顺序 `V02-0 → M1 → M2 → M3 → M4 → M5 → M6`。每个 M 开工前独立走
规范驱动开发六阶段，契约影响=Y 的必须新增 CD-1xx。

### V02-0 Design & Evidence Baseline（已完成）

- 目标：统一 Phase 1.1 机器证据、Handbook 架构决策和 V0.2 设计边界。
- 退出：Phase 1.1 findings 关闭；Handbook 00–26/A–G、Registry、总稿与 manifest 全部通过；
  明确 AEH 软件仍为 v0.1.0、产品有效性未证明、72-run 未授权。
- 代码影响：无 AEH 功能代码或 Schema 修改。
- 结果：允许 M1 进入独立 SPEC/PLAN，不表示 M1 已实现或软件 v0.2.0 已发布。

### M1 基础设施可信度：wheel 打包 + AEH 自身 CI 回归门（已合并）

- 目标：非 editable 安装可用；每次推送跑全量回归。
- In：pyproject package-data/资源定位重构；.github/workflows 回归 workflow；配套测试与文档安装节。
- Out：PyPI 发布（未授权不承诺）；用户项目 CI 深集成（M6）。
- 进入：Owner 批准 M1 SPEC/PLAN。
- 退出：clean-room `pip install .` 后 `aeh doctor`/`aeh bootstrap` PASS；CI 绿；回归 232+n；README 安装节更新。
- 契约影响：N。关联：KL#11、P2#3、C-014、C-003a。
- 本地风险：① setuptools 数据文件重定位在 editable 与 wheel 两条路径必须同时测试，否则易半修；② Windows/POSIX 资源路径差异——用 clean-room 双路径验证兜底。
- 实现结果：relocatable wheel、Windows/Linux CI matrix 与 clean-room smoke 已落地；软件包版本仍为 `0.1.0`，未发布 PyPI/tag。

### M2 修复/恢复：aeh repair + 原子应用日志 + 工作流 repair UX（已合并）

- 目标：安装损坏可诊断→dry-run→修复→审计→回滚；TEST_REPAIR/SPEC_REPAIR 一键直达。
- In：`aeh repair` 子命令（数据驱动修复规则）；bootstrap journal 与回滚；repair 命令 UX；doctor 修复建议联动。
- Out：upgrade（M3）；网络自愈；任何未经 dry-run 的自动写。
- 进入：M1 退出达成。
- 退出：5 类故障注入（缺 runtime 文件 / digest 不一致 / managed 块损坏 / 半安装残留 / gitignore 缺失）经 repair 后 doctor READY；journal 存在；回滚可证；回归 232+n。
- 契约影响：Y（repair 真值工件 → CD）。关联：KL#3、KL#5、C-017、C-012、C-001。
- 本地风险：① repair 会写用户文件——默认 dry-run、先日志后应用、绝不自动 APPROVE；② 修复规则过度匹配可能误伤用户原文——规则必须最小作用域并带回归夹具。
- 实现结果：5 类故障注入、事务 journal、显式 rollback、漂移阻断和 TEST_REPAIR/SPEC_REPAIR 路由已覆盖；完整回归 `259/259`，wheel clean-room repair smoke 通过。

### M3 升级系统：aeh upgrade（已合并）

- 目标：已装项目显式升级 runtime/契约，不丢用户数据，中断可回滚。
- In：升级计划（diff）→ dry-run → 应用 → 回滚；manifest 版本/digest 更新；升级后 doctor 自检。
- Out：多版本并存、增量升级、自动升级（ADR-003 future boundary）。
- 进入：M2 退出达成（复用 journal/rollback）。
- 退出：v0.1 安装项目升级到 v0.2 成功且 profile/approvals/changes 不丢；注入中断可回滚；manifest 更新正确；回归 232+n。
- 契约影响：Y（升级写入边界；ADR-003/P-09 已预留）。关联：KL#6、C-002。
- 本地风险：① 升级覆盖用户配置——升级计划必须逐文件声明 preserve/overwrite/merge；② digest 不一致的旧安装可能无法识别版本来源——先 repair 后 upgrade 的顺序保证。
- 实现结果：runtime/manifest 最小写边界、v0.1 source-integrity gate、UPG journal、
  deterministic history、项目数据 preserve、失败/显式 rollback 与 clean-room upgrade smoke 已覆盖；
  完整回归 `273/273`（Windows 本地符号链接权限限制导致 1 项平台测试跳过，Linux CI 执行该项）。

### M4 P2 收口 + 批准凭据最小强化（本地已验证，未合并）

- 目标：manual 验证有独立批准 gate；CRITICAL plan 缺 integration/contract 直接拒绝；approval 有 TTL/撤销。
- In：manual VER gate（gates/approvals 契约扩展）；test-design 强制校验；approve revoke + TTL。
- Out：签名/凭据强身份（M5）；OIDC/IAM。
- 进入：M1 退出达成。
- 退出：manual VER 未批准 → verify 明确 BLOCKED_WAITING_MANUAL；缺 integration/contract 的 CRITICAL plan 被 test-design 拒绝；过期/撤销 approval 不计入 gate；回归 232+n。
- 契约影响：Y（gates/approvals → CD）。关联：KL#10、KL#13、P2#1/#2/#4、RISK-022、CD-097、C-013、C-011、C-009a。
- 本地风险：① 旧 approvals.yaml 无 TTL 字段的迁移语义必须先定义（默认：视为无 TTL 并 WARN）；② manual gate 可能拖慢流程——只对 CRITICAL 强制，STANDARD 可选。
- 实现状态：新增 `VERIFY_MANUAL` 独立 Gate；批准支持可选 TTL、失效判断和保留原始
  证词的显式撤销；旧无 TTL 记录继续有效并 WARN；CRITICAL 的 integration/contract
  要求前移到 TEST_DESIGN，VERIFY 保留防御性复查。完整回归共执行 `314` 项（`310`
  通过，Windows 符号链接权限限制跳过 `4` 项），wheel build 与 clean-room smoke 通过。当前仅为本地
  feature branch，版本、push、merge、tag、Release 与 PyPI 均需独立 Owner 决策。

### M5 安全边界：命令执行沙箱 + 强审批身份

- 目标：测试命令在可配置隔离边界内执行；approval 支持签名/凭据校验。
- In：执行器隔离层（shell=True 兼容路径默认收紧）；approvals 签名验证。
- Out：企业 TCB/attestation、CI 远端重算（ADR-004 future boundary）。
- 进入：M4 退出达成。
- 退出：shell=True 路径默认禁用或需显式授权；注入攻击测试不逃逸；伪造 approval 被拒；回归 232+n。
- 契约影响：Y（命令执行/审批契约 → CD）。关联：KL#1、KL#4、RISK-EXEC-001、RISK-023、ENF-APPROVAL-001、C-020、C-009b。
- 本地风险：① 沙箱跨平台能力差异大——Windows/POSIX 分能力矩阵，未支持项诚实报 WARN；② 签名密钥分发/轮换是新的治理面——密钥管理独立 SPEC，禁止写死在公共 core。

### M6 规模化：CI 深集成 + 多代理编排

- 目标：用户项目 PR/merge 触发 aeh 校验门；多代理并发 change 不串扰。
- In：CI 模板/action；并发 change 隔离强化；编排协议（C-008 开工前复核）。
- Out：自动 merge/push/PR（Q-006 拒绝）；RAG/Web UI。
- 进入：M3 退出 + M5 退出。
- 退出：模板项目 PR 校验门 BLOCKED 且不可绕过；两代理并发 change 故障注入无串扰；回归 232+n。
- 契约影响：Y（编排语义 → CD）。关联：KL#7、KL#9、C-003b、C-008。
- 本地风险：① CI 校验门被伪造（跳过命令/改结果文件）——校验命令与报告必须可重放且摘要进 CI 日志；② 编排协议范围易膨胀——M6 SPEC 必须把「协议」冻结在最小子集。

### 依赖 DAG（已做拓扑校验：no cycle）

```text
V02-0 ─ M1
├─ M2 ─ M3 ─┐
└─ M4 ─ M5 ─┴─ M6
```

| 边 | 理由 |
|---|---|
| M1 blockedBy V02-0 | 软件工作必须建立在已对账的设计与证据基线上 |
| M2 blockedBy M1 | repair 需 wheel 分发 + CI 回归护栏 |
| M3 blockedBy M2 | upgrade 中断回滚复用 M2 的 journal/rollback |
| M4 blockedBy M1 | gates/approvals 契约变更必须先在 CI 有回归护栏 |
| M5 blockedBy M4 | 强身份以 TTL/撤销最小强化为前置 |
| M6 blockedBy M3 | CI 深集成需 upgrade 支持多项目 |
| M6 blockedBy M5 | 多代理编排要求代理身份可信 |

## 7. 长期候选池与拒绝项

| 候选 | 后置理由 | 激活条件 |
|---|---|---|
| C-004 RAG | 成本 XL，依赖深集成与证据语料 | C-003b 完成且语料可用 |
| C-005 Web UI | 成本 XL，CLI 先行 | CLI 稳定 + 明确用户量诉求 |
| C-006 Mutation testing | 依赖 CI 深集成 | C-003b 完成 |
| C-007 Impact analysis | 依赖 upgrade + CI 深集成 | C-002/C-003b 完成 |
| C-010 新 workflow levels | 契约级扩展，风险最高 | Owner 明确需求 + 单独 CD |
| C-015 Adapter 能力升级 | 受外部平台能力约束 | Codex/Claude 开放对应 enforce 能力 |
| C-016 证据分类升级 | 触 frozen classifications 契约 | C-004 完成或独立 CD 获批 |

**拒绝**：V02-C-018 自动 merge/push/PR（KL#8）——与「AEH stops at MERGE_READY」
（README §8）哲学边界冲突；AEH 是 Validator，不代行 merge/push/PR（Q-006 已裁决）。

## 8. 风险登记与治理

### 全局风险

| 风险 | 缓解 |
|---|---|
| 范围蔓延：M 内塞入隐含需求 | 每个 M 独立 SPEC/PLAN + 排除表 + Gate 门禁 |
| 冻结契约漂移：未走 CD 就改 core/schemas | 契约影响=Y 的 M 强制 CD-1xx + 契约回归测试；审查者核查 |
| Owner 审批节奏中断长链 | M1 独立可交付；每 M 结束有完整证据包供裁决 |
| 多 M 并行返工 | 政策：一次只开一个 M，按 M1→M6 串行 |
| 评分主观性/信息过期 | 每个 M 开工前用当日证据复核其优先级与范围 |

### 治理规则

1. V02-0 已批准为 V0.2 设计与证据输入；它不替代冻结的软件契约，也不是软件发版。
2. 每个 M 独立走规范驱动开发六阶段；契约影响=Y 的必须有 CD-1xx 决策记录。
3. V0.1 线只打补丁（release-fix 记录），V0.2 功能一律在 V0.2 分支线实现。
4. 每个 M 的退出条件含「回归 232+n PASS + 证据落盘 + Owner Gate」，缺一不可。
5. 版本/tag 策略只给原则：V0.2 里程碑不单独发版，攒齐 M1–M3 形成 v0.2.0 候选后再
   走一次 Release Safety Review（参照 docs/releases/v0.1.0/RELEASE_CHECKLIST.md）。

## 9. 验收自检（本路线图自身的完成标准）

| # | 标准 | 状态 |
|---|---|---|
| AC-1 | 候选池覆盖 CONTRIBUTING 清单、KL#1–13、P2 四项且逐条有引用，无凭空候选 | PASS（§3 + 证据包 02） |
| AC-2 | 每条候选三选一去向（M/池/拒绝），拒绝有理由 | PASS（§3、§7） |
| AC-3 | 公式权重和=100、每行总分可复算 | PASS（§4 + 复算输出 0 不匹配） |
| AC-4 | DAG 无环、每边有理由 | PASS（§6 + 拓扑校验 no cycle） |
| AC-5 | 每个 M 有目标/In/Out/进入/退出/契约影响/关联/风险 | PASS（§6） |
| AC-6 | 零代码变更：仅新增本文件 + README/CONTRIBUTING 各 1 行链接 | PASS（git diff 证据） |
| AC-7 | 无 secrets、无机器绝对路径、无私库项目名 | PASS（grep 0 命中证据） |
| AC-8 | 首屏即可回答「下一个 M 是什么、为什么」 | PASS（§1） |

证据路径：任务证据包 `TASK-20260817-aeh-v02-roadmap/evidence/01–06`（机器输出不截断）。
