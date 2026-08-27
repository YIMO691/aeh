# Owner / Architecture 决策记录

> 本文件记录 Owner 裁决与已登记的延期需求；机器可验证的契约见 core/ 与 schemas/。

## OWNER-CD-001（2026-08-14，APPROVED）

- **subject**: confidence 枚举
- **decision**: `DETECTED / INFERRED / USER_CONFIRMED / UNKNOWN` 为唯一规范枚举；
  旧示例中的小写 `confirmed` 为非规范写法（deprecated example value），不是另一套合法值。
- **effect**: Phase 1 的 CD-001 保留，不返工 Schema；后续任何 `confidence: confirmed` 视为旧格式或非法。

## ENF-APPROVAL-001（known_deferred，不阻塞）

- **requirement**: Enforcement 阶段必须阻止普通 Runtime Agent 直接写入 APPROVED 审批记录；
  Schema 的 `APPROVED ⇒ actor.type=human` 只能证明"数据声明自己是 human"，不能证明"实际是 human 写的"。
- **current_phase**: contract_only
- **blocking_phase1**: false

## Phase 状态（2026-08-14）

- phase_0: FROZEN（docs/architecture.md 为唯一 canonical frozen architecture）
- phase_1: APPROVED（契约测试 21/21 PASS）
- phase_2: PHASE_2_BOOTSTRAP_DISCOVERY（Owner 已授权；仅 Discovery，不做 Interview/Conflict/Compiler/Adapter/完整 bootstrap）
## Phase 2 契约决策（2026-08-14）

- **CD-006**: Discovery 事实模型 = {id, domain, field, value, confidence, evidence[]}，
  DETECTED 必须有非空 evidence；输出结构由 schemas/discovery.schema.json 冻结。
- **CD-007**: 检测规则数据驱动（bootstrap/discovery/*.yaml），扫描器只实现通用 marker 匹配
  （file/dir/glob/content + match any/all），规则与逻辑严格分离。
- **CD-008**: V1 最小规则集只含中立生态标记（python/js/ts/csharp/go/rust/java 及通用包管理/CI/测试框架）；
  不内置任何特定引擎/公司域规则——它们将来作为用户规则层加入。
- **ENF-DISCOVERY-001（known_deferred）**: Discovery 结果落地 .aeh/bootstrap/discovery.yaml 属
  Bootstrap 安装职责，Phase 2 扫描器只返回数据不写盘；写盘由后续 Bootstrap 阶段实现。
## Phase 2 Hardening 契约决策与风险（2026-08-14）

### 契约决策

- **CD-009**: 路径防逃逸——所有 marker 解析经 _resolve_within：拒绝绝对路径与 .. 段，
  并以 realpath+commonpath 拒绝越界（含 symlink 指向根外）；os.walk 默认不跟随目录链接。
  防御纵深：规则 schema 同时禁止路径中的 .. 与绝对形式。
- **CD-010**: content 证据最小化——只保留 {type, path, rule_id, marker_index, match_line, file_hash}，
  原始匹配正文绝不进入输出（测试断言 fixture 仓库内容零泄漏）。
- **CD-011**: 输出 provenance v2——contract version=2，新增 scanner_version、ruleset_digest
  （规则文件内容哈希，规则变化即变化）、repository{root, base_commit, dirty}。
- **CD-012**: 规则加载前强制 schema 校验（schemas/discovery-rule.schema.json），
  非法规则（未知域/缺 id/路径逃逸/content 缺 contains）以 DiscoveryError 拒绝，绝不部分加载。
- **CD-013**: 资源边界——content 上限 1 MiB、binary 探测（前 8KB 含 NUL 即跳过）、
  walk 文件数上限（默认 50000，超限记 warnings.resource_limit 并停止匹配）、只读（不写盘）、无网络（无任何网络调用）。

### 已知风险

- **RISK-001**: git identity 依赖本机 git 命令（只读、无网络、5s 超时）；受限环境不可用时
  base_commit/dirty 记录为 null（诚实降级，不伪造事实）。
- **RISK-002**: Windows 符号链接端到端测试受权限限制未执行；越界防护由 realpath+commonpath
  实现并有单元测试覆盖 _resolve_within，但真实 symlink/junction 场景建议后续在 CI（Linux）补端到端用例。
- **RISK-003**: 达到 walk 上限时事实集不完整（fail-safe 设计）；调用方必须检查 warnings 字段，
  不能默认"无警告即完整"。
- **RISK-004**: ruleset_digest 只覆盖 rules 目录内 *.yaml 文件；目录内其他文件不参与摘要。
## Phase 3 契约决策（2026-08-14，PHASE_3_PROGRESSIVE_INTERVIEW_MINIMAL）

- **CD-014**: Interview 规则数据驱动——问题全部来自 bootstrap/interview/*.yaml（schema 强制），
  模块零问题硬编码；用户新增自定义 YAML 问题零代码生效（有测试证明）。
- **CD-015**: 过滤顺序冻结为：discovery_detected → optional(required=false) → already_answered → ASK。
  UNKNOWN ≠ 必须询问；仅 required=true 且无可靠答案才 ASK。
- **CD-016**: Answer Model = {question_id, answer, type, source, answered_at, confidence?}，
  answers 以 question_id 为键；reset 列表显式支持重新回答（幂等）。
- **CD-017**: 确定性——plan() 只读 discovery 的 semantic 字段（facts/unknowns），
  scanned_at 属 non-semantic provenance，时间变化不影响决策（有测试证明）。
- **CD-018**: 默认问题集覆盖 6 个示例主题（先方案/改源码/commit/push/测试/人工Review/规程），
  四类问题 FACT/PREFERENCE/POLICY/PERMISSION 全部有代表。
## Phase 4 契约决策与风险（2026-08-14，PHASE_4_CONFLICT_AND_PROFILE_COMPILER）

### 契约决策

- **CD-019**: 统一 Rule Record = {field, value, scope, source, confidence, origin_ref, type}；
  scope 使用冻结优先级体系；interview scope 映射：core→project、ai_permissions→project、
  organization/team/developer 直通；FACT 类型一律 scope=default（事实不伪装成政策）。
- **CD-020**: Profile 分区路由（permissions./developer./testing./review./team./organization./
  workflow.default_level/repository.language→project.languages），未路由字段（含 FACT 事实）进
  top-level facts，绝不进入政策分区。
- **CD-021**: 冲突解析=min-rank 语义（precedence 列表索引越小优先级越高）；
  同级不同值 → BLOCKED_POLICY_CONFLICT（conflict.schema.json 机器化），字段不进入 effective；
  同级同值 → 不冲突；被覆盖规则 provenance 保留在 entry.shadowed（ref 列表）。
- **CD-022**: profile.schema.json 扩展（Phase 4 契约演进，向后兼容）：
  provenance 增加可选 type(FACT/PREFERENCE/POLICY/PERMISSION) 与 shadowed[{type,ref}]；
  project.languages 与 review.human_required_for 的 items 允许 provenance 对象；
  workflow.default_level 允许 provenance 对象；source.type 枚举补充 user_answer/default_applied。
- **CD-023**: effective-workflow.schema.json 增加可选 default_level（枚举五级）；
  Workflow Compiler 只读 core/workflow.yaml 深拷贝，绝不写回（测试哈希前后一致证明）。
- **CD-024**: 时间 provenance 不参与编译：scanned_at/answered_at 只作审计，不进入 profile
  semantic 字段；答案合法性在 normalize 阶段校验（非法 option 值 CompilerError 拒绝）。

### 已知风险

- **RISK-005**: Phase 4 的"organization_policy 输入通道"尚未实现（Policy Normalizer 属后续
  Bootstrap 阶段）；当前 organization scope 来自 interview organization.yaml 的用户回答，
  测试用 source=user_answer 覆盖同级冲突路径。
- **RISK-006**: workflow.default_level 的 harness 默认 STANDARD 硬编码在 compiler 常量
  DEFAULT_LEVEL；后续 Bootstrap 阶段应改为从 core 或显式 harness defaults 注入。
## Phase 5 契约决策与风险（2026-08-14，PHASE_5_AGENT_ADAPTERS）

### 契约决策

- **CD-025**: Adapter = Renderer/Translator。语义决策全部来自 Phase 4；Adapter 不重算
  precedence、不解决 conflict、不修改输入（测试证明 profile/workflow 渲染前后深相等）。
- **CD-026**: 语义等价由构造保证——两平台共用 extract_semantics() canonical 语义字典，
  render 输出携带同一 semantics 字段；测试断言 codex.semantics == claude.semantics。
- **CD-027**: capability_map 数据驱动（adapters/<x>/adapter.yaml 经 adapter.schema.json 校验）：
  Codex：modify_source/shell/web_access=sandbox ENFORCEABLE、git_commit=approval、git_push=instruction GUIDANCE_ONLY；
  Claude：文件/commit/push/shell=permission_rules ENFORCEABLE（allow/ask/deny 规则集）、web_access=instruction GUIDANCE_ONLY。
  deny 语义永不放松：deny 的表达永远是 deny 桶（Claude deny rules / Codex DENY instruction）。
- **CD-028**: Profile status=BLOCKED → AdapterError(BLOCKED_PROFILE_CONFLICT)，拒绝生成，不忽略冲突。
- **CD-029**: 无法平台强制的 Enforcement（deny×GUIDANCE_ONLY、human_review required）记入
  diagnostics.unsupported_capabilities（{field, required_semantic, adapter, status}），
  降级资格由 capability_map 声明，Adapter 不自行决定。
- **CD-030**: merge_managed_section 纯函数：保留用户原文、幂等、malformed markers
  （缺对/顺序反/重复 begin）→ AdapterError(MALFORMED_MANAGED_MARKERS)，不静默覆盖；
  真实写盘留给 Bootstrap Install Phase。
- **CD-031**: minimum disclosure 延伸至 Adapter：只表达 effective constraint 与 ref ID；
  泄漏测试证明 SECRET 正文/内部路径零泄漏。

### 已知风险

- **RISK-007**: capability_map 的 ENFORCEABLE/GUIDANCE_ONLY 分级是 AEH 对宿主能力的**声明**
  （Phase 5 依据官方文档能力建模）；宿主版本演进可能改变实际能力，后续 Doctor 阶段可考虑
  运行时能力探测。
- **RISK-008**: Codex 的"approval/sandbox"渠道在 V0.1 只输出 instruction 级表达，
  未生成 Codex CLI 参数或配置（避免 Agent 配置格式漂移）；真实配置生成留给后续阶段。
## Phase 6 契约决策与风险（2026-08-14，PHASE_6_BOOTSTRAP_INSTALL）

### 契约决策

- **CD-032**: 安装拓扑机器化——aeh bootstrap <target> [--dry-run] [--answers] [--source-revision]；
  --dry-run 完整计算 + Install Plan + 零写盘（测试证明 target byte-for-byte 不变）。
- **CD-033**: Install Plan 确定性——content_hash 全部采用 semantic_hash（深度剔除
  scanned_at/answered_at/installed_at 等非语义时间字段）；plan 经 install-plan.schema.json 校验
  且每个 path 必须通过安全解析（无绝对路径、无 .. 段）。
- **CD-034**: manifest.installed_at 仅首次安装写入：apply 时 finalize_manifest 检测已存在则保留；
  二次 Bootstrap 对已存在且内容相同的文件一律跳过写（零 diff、零 mtime 抖动）。
- **CD-035**: Runtime snapshot = core/*.yaml + schemas/*.json（skills/ 尚无内容不创建空目录）；
  安装后重算 digest 与 manifest 对比，不一致 → BLOCKED_RUNTIME_INTEGRITY。
- **CD-036**: Atomic Apply = staged 内存态 → 逐文件 tmp+os.replace → 失败反向回滚（journal
  记录原字节），用户原文不丢失；任何失败绝不返回 BOOTSTRAP_COMPLETE。
- **CD-037**: 私有边界双重防线——answers 走私额外字段（private_body 等）被 answers.schema
  拒绝 → BOOTSTRAP_FAILED_VALIDATION 且目标不变；合法私有约束只以 ref id 进入 profile。
- **CD-038**: .gitignore 只追加 .aeh/private/ 单行（幂等、不重复、不 ignore 整个 .aeh/）；
  .aeh/private/ 与 .aeh/changes/ 以目录操作创建（无空文件填充）。

### 已知风险

- **RISK-009**: apply 的原子性为"逐文件 os.replace + 失败回滚"，非全目录事务；
  极端断电场景可能留下部分写入（回滚路径已覆盖可预期异常）。
- **RISK-010**: manifest.source_revision 默认 "dev"（AEH 仓库尚未 git 化）；发布前应注入真实 git sha。
- **RISK-011**: 第二次 Bootstrap 若答案语义变化会重写 profile 等文件（这是预期行为，
  非"无意义 diff"）；测试保证的是"相同 semantic input → 零 diff"。
## Phase 7 契约决策与风险（2026-08-14，PHASE_7_DOCTOR_AND_RUNTIME_PREFLIGHT）

### Phase 6 术语归一（正式记录）

- **apply_semantics**（Phase 6 安装语义冻结）：
  staged=true；per_file_atomic_replace=true；rollback_capable=true；repository_wide_atomic=false。
- **RISK-INSTALL-CRASH-001（deferred risk）**：多文件 Apply 在断电/进程强杀/磁盘故障/回滚自身失败时
  可能留下 partial installation。Phase 7 Doctor 通过 install.staging_residue 检查（*.aeh-tmp /
  *.aeh-rollback 残留 → BLOCKED_INCOMPLETE_INSTALL）发现此类残留，只报告不修复。
  不为此重写 Phase 6 安装器。

### 契约决策

- **CD-039**: Doctor = observe/validate/diagnose；只读、无网络、不修复。检查模型
  {check_id, domain, status(PASS/WARN/BLOCKED), message, evidence, remediation}；
  overall = BLOCKED（任一 BLOCKED）> READY_WITH_WARNINGS（任一 WARN）> READY。
- **CD-040**: runtime/core contract 被篡改 → BLOCKED_RUNTIME_INTEGRITY，Doctor 不得基于被篡改
  契约声明 READY；版本不匹配 → BLOCKED_VERSION_INCOMPATIBLE（upgrade 属后续阶段）。
- **CD-041**: Adapter capability 语义：deny+GUIDANCE_ONLY → WARN（不静默 PASS）；
  deny+UNENFORCEABLE → BLOCKED（按 Contract 阻塞，Doctor 不自行放宽 deny）。
- **CD-042**: .aeh/private/ 未 gitignore → BLOCKED（有 .gitignore 时违反冻结 P-13）；
  .gitignore 缺失 → WARN（git 可能未初始化）。Doctor 结构性保证不读 private 文件内容，
  evidence 不回显 private 原文（有泄漏测试）。
- **CD-043**: 环境检查诚实降级：git 不可用 → WARN(UNKNOWN_ENVIRONMENT)，不猜测、不安装、不联网。
- **CD-044**: runtime_preflight 为纯逻辑（verdict + blocking_checks + warnings），不创建 CHG、
  不修改任何东西；只回答"下一阶段是否具备基本条件"。--change 扩展边界预留，本阶段未实现
  Change 检查、未创建任何空 CHG 工件。
- **CD-045**: compute_digests 改为动态遍历（core/*.yaml + schemas/*.json 全量），与
  runtime_digest_at 公式一致；避免新增 schema 文件后 manifest 与快照 digest 漂移
  （Phase 7 修复的 Phase 6 契约缺陷）。
## Phase 8 契约决策与风险（2026-08-14，PHASE_8_RUNTIME_CHANGE_WORKFLOW）

### 契约决策

- **CD-046**: change new 前置 Runtime Preflight：BLOCKED → BLOCKED_PREFLIGHT 不创建 Change；
  READY_WITH_WARNINGS → 继续并把 warnings 写入 change.yaml.preflight_warnings。
- **CD-047**: Change ID 确定性安全分配：年份 + 已有目录 max+1 + 存在性递增，绝不覆盖；
  每个 Change 独立 .aeh/changes/CHG-YYYY-NNNN/，无任何全局 current-change 文件。
- **CD-048**: Classification 引擎：LLM 可建议（--level），机器强制 hard escalation——
  8 域任一命中 → CRITICAL，不可降级；结果保存 reasons/evidence/suggested_level/escalated。
  无建议且无命中默认 STANDARD（fail-safe，CD 记录）。
- **CD-049**: classifications.yaml 增加 keyword_hints（8 域通用中英关键词，零公司硬编码）作为
  检测启发式；过度触发是 fail-safe（升级），漏触发由调用方显式 hits 修正。
- **CD-050**: gates.yaml 增加 phase 字段（gate 守护的进入阶段）；transition 进入某阶段前，
  若存在守护 gate 且 change.gates 非 PASS → BLOCKED_GATE_UNSATISFIED；
  条件边（如 RED→LOCK_TEST condition=VALID_RED）需显式 --condition 匹配，否则 BLOCKED_CONDITION_REQUIRED。
- **CD-051**: transition 前先跑 Doctor：overall=BLOCKED → BLOCKED_DOCTOR（含 runtime digest
  篡改场景）；只信任已安装快照 .aeh/runtime/core/states.yaml + gates.yaml。
- **CD-052**: change.schema.json 演进（向后兼容）：classification 允许对象（level/reasons/evidence/
  suggested_level/escalated）或旧字符串；新增 workflow{level,phases} 与 preflight_warnings[]。
  Phase 1 fixtures 兼容性由回归锁定。
- **CD-053**: 本阶段只建 Workflow Shell：GROUND→SPEC 等深层迁移被 GROUNDING gate 阻断
  （Grounding Runtime 属 Phase 9）；不伪造 evidence/spec/test 文件；status 子命令纯只读。

### 已知风险

- **RISK-012**: keyword_hints 可能对含"权限/登录"等词的 DIRECT 级任务过度升级为 CRITICAL
  （fail-safe 方向）；后续 Pilot 阶段可按真实误报率校准词表。
- **RISK-013**: gates 状态目前只能由创建（classification PASS）与未来 Runtime 阶段写入；
  Shell 阶段无法推进 Standard/Critical 的深层状态（符合设计：Gate 未满足禁止 transition）。
## Phase 9 契约决策与风险（2026-08-14，PHASE_9_GROUNDING_AND_EVIDENCE_RUNTIME）

### 契约决策

- **CD-054**: Evidence 机器真值新增 schemas/evidence-index.schema.json 与 Change 内 evidence.yaml
  （机器真值）；evidence.md 保持人类叙述、绝不当 Gate 真值。不改变 Phase 0 语义（机器事实 YAML）。
- **CD-055**: Evidence 最小模型 = {id(EV-*), type, location{path,symbol,line}, finding, confidence(DIRECT/
  INDIRECT/INFERRED), relevance{kind}, source_state{base_commit,dirty,file_hash,rel_path}, query,
  test_result(FOUND/NOT_FOUND/NOT_VERIFIED), limitations}；七类通用类型（SOURCE/TEST/CALL_PATH/CONFIG/
  ARCHITECTURE_CONSTRAINT/NEGATIVE_SEARCH/UNKNOWN），零平台专属。
- **CD-056**: NOT_FOUND 必须有 NEGATIVE_SEARCH 证据（记录搜索规则与范围），禁止"没找到→推断不存在"；
  资源上限触发 → unknowns{LIMITED_BY_RESOURCE_BOUND}，不伪造。
- **CD-057**: Grounding Gate 按风险分层（bootstrap/grounding.yaml 数据驱动）：DIRECT 无要求、
  LIGHTWEIGHT=source+test_search、STANDARD=+constraint_or_unknown、CRITICAL=+call_path+risk_domain_
  evidence+limitations；证据不足 → GROUNDING_INCOMPLETE，SPEC 不可达（gate 未 PASS）。
- **CD-058**: Classification feedback 单向安全：Grounding 发现新风险域 → 只升级（至 CRITICAL）并记录
  repository_evidence；绝不自动降级 Hard Escalation（有测试锁定）。
- **CD-059**: change.schema 再演进（向后兼容）：classification.evidence 条目允许对象
  {kind, domain, confidence}；state.previous 允许 null（初始态）。
- **CD-060**: STALE 检测：check_stale 以 source_state.file_hash 与当前文件对比；文件变化 → 证据 stale，
  不得让过时证据永久支撑后续 Spec。
- **CD-061**: change ground 对 INTAKE 状态先执行合法 INTAKE→CLASSIFY 迁移再 grounding；
  写入仅限 .aeh/changes/CHG-*/；Doctor BLOCKED → BLOCKED_DOCTOR 不执行。

### 已知风险

- **RISK-014**: CALL_PATH 目前是"关键词共现"推断（confidence=INFERRED，附 limitations 声明非符号级
  验证）；真实调用链验证属后续 Phase。
- **RISK-015**: 风险域 grounding 扫描 8 域全部关键词，可能对含通用词（db/接口/安全）的仓库产生
  escalation；fail-safe 方向（只升级），Pilot 阶段可按误报率校准。
## Phase 10 契约决策与风险（2026-08-14，PHASE_10_SPECIFICATION_RUNTIME）

### 契约决策

- **CD-062**: spec.schema.json 向后兼容演进：REQ 新增可选 kind(CURRENT/DESIRED/CONSTRAINT)、
  source{type(EVIDENCE_DERIVED/USER_REQUIREMENT/POLICY_CONSTRAINT),refs}、failure_behavior、
  scope_tags；spec 顶层新增可选 scope{in,out}、unknowns、assumptions、generated_at。
  Phase 1 fixtures 全部原样通过（回归锁定）。
- **CD-063**: 三种来源语义机器分离：EVIDENCE_DERIVED ⇒ supported_by 非空且 EV 存在
  （否则 BLOCKED_UNSUPPORTED_REQUIREMENT / BLOCKED_INVALID_EVIDENCE_REFERENCE）；
  USER_REQUIREMENT 无需虚构 EV；POLICY_CONSTRAINT 只存 effective constraint + ref，零正文泄漏。
- **CD-064**: CURRENT 与 DESIRED 不混淆：kind 字段强制区分，测试断言 CURRENT 行为文本不得
  包含用户目标语句、DESIRED 不得引用 EV。
- **CD-065**: 稳定 ID：按 (kind, source_type, behavior) stable key 排序后分配；重跑时语义未变的
  REQ/AC 复用原 ID（测试锁定重跑 ID 不变与语义相等）。
- **CD-066**: CRITICAL 更严格：每 REQ 需 invariant AC 或 failure_behavior；critical unknown
  未解决 → SPEC_INCOMPLETE。STANDARD 最低：REQ + AC + 来源 + scope。
- **CD-067**: scope 控制：req.scope_tags ∩ scope.out ≠ ∅ → UNSCOPED_REQUIREMENT 阻断（V0.1 不实现
  复杂 scope inference）。
- **CD-068**: stale 检查前置：REQ 依赖的 EV 若 file_hash 失配 → BLOCKED_STALE_EVIDENCE，
  SPEC Gate 不 PASS，须重新 Grounding。spec.md 仅作人类叙述投影（由机器 spec 派生）。
- **CD-069**: spec Runtime 写入仅限 CHG 目录（有 byte-for-byte 快照测试）；SPEC Gate PASS 才
  允许 SPEC→TEST_DESIGN（gate 未 PASS 被 BLOCKED_GATE_UNSATISFIED 拒绝，有测试）。

### 已知风险

- **RISK-016**: 稳定 ID 复用基于 (kind,source,behavior) 文本匹配；行为文本改写会导致重编号
  （V0.1 不做复杂 semantic diff，符合冻结边界）。
- **RISK-017**: AC type 沿用 Phase 1 冻结小写枚举 automated/manual/invariant；文档示例的大写
  AUTOMATED/MANUAL/INVARIANT 语义等价，未改架构。
## Phase 11 契约决策与风险（2026-08-14，PHASE_11_TEST_DESIGN_AND_RED）

### 契约决策

- **CD-070**: test-plan.schema.json 向后兼容演进：tests 增加 verifies(AC-*)/intent/required/
  expected_before_fix{type,signature}/fixture|spec_mismatch|test_defect_signatures/execution；
  kind 枚举扩展 property/contract/runtime/platform；顶层增加 test_files{src,dest} 与
  non_automatable。Phase 1 fixtures 兼容（回归锁定）。
- **CD-071**: AC 覆盖规则：每个 automated AC → ≥1 TEST；TEST.verifies 必须指向真实 AC
  （否则 BLOCKED_INVALID_AC_REFERENCE）；MANUAL AC 不强制伪造自动化测试；
  CRITICAL invariant AC 必须有测试或声明 non_automatable。
- **CD-072**: 测试文件安装位置受控：dest 必须落在 grounding 测试目录或匹配测试文件模式
  （否则 BLOCKED_TEST_LOCATION）；生产文件 byte-for-byte 不变（有快照测试）。
- **CD-073**: RED verdict 确定性分类（数据驱动，不依赖 LLM）：exit 0 → NO_RED_ALREADY_GREEN；
  匹配 expected signature → VALID_RED；匹配 test_defect/spec_mismatch/fixture 声明签名 →
  对应 INVALID 路由；匹配环境签名（ModuleNotFoundError 等）→ INVALID_RED_ENVIRONMENT；
  其余 → INVALID_RED_UNEXPECTED_FAILURE。不新增模糊 FAILED 吞掉语义。
- **CD-074**: red.yaml（schemas/red.schema.json）机器记录：test_id/command/exit_code/output_ref/
  output_hash/expected|actual_failure/base_commit/changed_files_hash/test_files_hash/commit/verdict
  ——冻结字段全部落地；原始输出落 CHG evidence 目录。
- **CD-075**: test-lock.yaml（schemas/test-lock.schema.json）：test files + hash + repository state +
  locked_at（非语义时间戳）；Phase 12 GREEN 将基于此 Lock 校验。
- **CD-076**: RED 阶段生产快照（排除 __pycache__ 生成物）；前后不一致 →
  BLOCKED_PRODUCTION_CHANGED_DURING_RED；全部 VALID_RED → red gate PASS →
  RED→LOCK_TEST（condition=VALID_RED）；RED_INVALID 时 LOCK_TEST 不可达（gate 未 PASS）。
- **CD-077**: 稳定 TEST ID：按 (verifies,intent,kind) stable key 复用既有 ID，不整表重编号。

### 已知风险

- **RISK-018**: RED 命令经 shell=True 执行测试命令；命令来自 test-plan（Agent/用户编写），
  执行权限语义属后续 Enforcement Phase（V0.1 假设可信 plan 作者）。
- **RISK-019**: verdict 分类依赖签名文本匹配；测试输出与签名弱匹配可能误路由
  （fail-safe 方向为 UNEXPECTED_FAILURE/INVESTIGATE，不会误判 VALID_RED）。
## Phase 12 契约决策与风险（2026-08-14，PHASE_12_GREEN_TEST_LOCK_AND_REFACTOR）

### 契约决策

- **CD-078**: AEH=Harness/Controller/Validator，Codex/Claude=代码修改执行者；AEH 不实现 Coding
  Model，只做 precondition/scope manifest/snapshot/post-change validation/test execution/
  evidence/transition。
- **CD-079**: GREEN 前置 Gate：state=LOCK_TEST、grounding/spec/red 三 gate PASS、test-lock schema
  PASS、Test Lock 哈希一致、protected 哈希一致（spec/evidence/profile/workflow）——
  任一失败 BLOCKED_GREEN_PRECONDITION，不得改生产代码。
- **CD-080**: Test Lock 强制双向：GREEN 前 hash==lock，GREEN 后 hash==lock；变化 →
  BLOCKED_TEST_CHANGED，即使全部 PASS 也不输出 GREEN。
- **CD-081**: test-lock 扩展 protected{path:hash}（Phase 12 契约演进，Phase 11 的 red.py 同步
  记录）；实现期受控修改的 changed_files 从 stale 检测中排除（区分 expected implementation
  mutation 与 unexpected external mutation），其余证据 stale → BLOCKED_RUNTIME_CONTEXT_STALE。
- **CD-082**: Production Scope Guard：changed_path ∈ allowed_paths（默认来自 Grounding source
  rel_paths；或显式 scope manifest）；after_hash 与当前文件一致；越界 → BLOCKED_SCOPE_VIOLATION。
- **CD-083**: RED-GREEN 配对：red.yaml 中 VALID_RED 的 test ids 必须在 GREEN 中真实执行且 exit 0；
  缺失/失败 → GREEN 不成立。
- **CD-084**: 执行安全边界：argv 结构化优先；command string 为 compatibility path（记录）；
  cwd 必须落在 target 内（_resolve_cwd realpath+commonpath，越界 → BLOCKED_CWD_ESCAPE）；
  timeout 有限（默认 120s）。不实现 sandbox（deferred risk）。
- **CD-085**: green.yaml（schemas/green.schema.json）机器记录：test_lock_hash、production
  before/after hash、tests（output_ref/output_hash）、changed_files{code_id CODE-*、
  path、before_hash、after_hash}、verdict GREEN_PASS/REFACTOR_PASS——为 Phase 13
  REQ→AC→TEST→CODE 链预留稳定 machine refs。
- **CD-086**: REFACTOR：仅 GREEN 成立后可进入；只改 allowed scope 内 production；目标测试 +
  regression 全绿；失败 → REFACTOR_REGRESSION；不改 tests/spec/evidence/profile/workflow。
- **CD-087**: 路径比较统一用 / 分隔符归一化（Windows backslash 与清单 forward slash 对齐）。

### 已知风险

- **RISK-020**: command string 仍经 shell=True 执行（compatibility path）；正式发布前应迁移
  至 argv-only 或 project-approved executor（Owner Phase 11 提示的收敛方向，已在 CD-084 冻结边界）。
- **RISK-021**: 生产修改由外部 Coding Agent 完成后 AEH 才验证（事后校验模型）；无法阻止
  Agent 在验证前修改任意文件——scope violation 靠 hash 比对事后阻断，属 Contract 层而非 OS 层。
## Phase 13 契约决策与风险（2026-08-14，PHASE_13_VERIFY_TRACEABILITY_AND_APPROVAL）

### 契约决策

- **CD-088**: VERIFY 是最终工程闭环而非合并动作：AEH 产出 verification.yaml/traceability.yaml/
  review.md 并置 verify gate，但绝不 merge/push/PR——停在 MERGE_READY 即为终点。
- **CD-089**: 风险分级验证：CRITICAL 必须声明 ≥1 integration/contract 验证项
  （否则 BLOCKED_VERIFICATION_PLAN_INSUFFICIENT）；STANDARD/LIGHTWEIGHT 不强制附加类型，
  只执行 GREEN 记录的 target tests + 声明式 regression + 声明式 verification 项。
- **CD-090**: 总体裁决三态：MERGE_READY / READY_WITH_WARNINGS / BLOCKED（verification.schema
  overall 枚举）；任何 fail → BLOCKED_VERIFICATION_FAILED；manual 项无证词 → BLOCKED_MANUAL_VERIFICATION_PENDING；
  警告只影响 READY_WITH_WARNINGS，不产生假 MERGE_READY。
- **CD-091**: 可信人工批准路径（ENF-APPROVAL-001 落地）：唯一写入 approvals.yaml 的代码是
  approval.record_approval（CLI aeh change approve）；actor.type 恒 human + actor.id 必填
  （诚实证词，V0.1 无签名）；runtime 模块从不写 APPROVED；verify 对 approvals.yaml 做
  schema 校验，system 伪造 APPROVED → BLOCKED_INVALID_APPROVALS。
- **CD-092**: 批准不能推翻技术失败：MERGE_GATE APPROVED 只解除 CRITICAL 的人工门禁并记入警告，
  任何 VER fail/manual 缺口照常 BLOCKED；MERGE_GATE REJECTED 对任何级别直接 BLOCKED_HUMAN_MERGE_REJECTED。
- **CD-093**: approvals gate 取值域与 core/gates.yaml human_approval_gates 严格一致
  （SPEC_REVIEW/RED_GATE/MERGE_GATE，contract test 冻结该不变量）；Phase 13 不为手动验证
  新增批准 gate——手动验证一律 pending，由 REVIEW 阶段完成。
- **CD-094**: traceability.yaml 五段链 REQ→AC→TEST→CODE→VER：CODE 归属 = 测试 targets 声明的
  生产文件（plan tests.targets，Phase 13 起成为可追溯契约）；无 targets 声明的 changed_files
  判 orphan code；verifies 指向未知 AC 判 orphan test；regression 类 VER（无 verifies）
  视为 change-wide，链入全部 REQ。任何孤儿/缺口 → BLOCKED_TRACEABILITY_INCOMPLETE。
- **CD-095**: review.md 是纯人工叙事投影（非机器事实）；change_review 只读重建、绝不写 APPROVED；
  verification.yaml/traceability.yaml/approvals.yaml 才是机器真相。
- **CD-096**: verification.schema 兼容演进：results 保留 Phase 1 字段（method/status/test_ref/evidence
  可选）并新增 type/verifies/verdict/exit_code/output_ref/output_hash/argv/command；red block
  维持 output_hash required 与 6 值 verdict 枚举（旧 legal/illegal fixtures 继续成立）；
  新增 overall/blocked_reason/warnings/verified_at。test-plan.schema 新增可选 verification 数组；
  traceability code item 新增可选 code_id；approvals gate 枚举 +VERIFY_MANUAL。
- **CD-097**: 手动验证（type=manual）不伪造自动化：无 command/argv → verdict pending →
  BLOCKED_MANUAL_VERIFICATION_PENDING（记录 overall=BLOCKED + blocked_reason）；MERGE_GATE
  批准不能把 manual 缺口变为已通过；V0.1 由 REVIEW 阶段人工完成手动项。
- **CD-098**: VERIFY gate 与状态迁移只随技术全绿发生（REFACTOR/GREEN→VERIFY）；
  人工批准缺口、manual 缺口、traceability 缺口均不置 gate；verify 幂等（VERIFY→VERIFY 不重复迁移）。
- **CD-099**: 测试夹具新增 tdd-neutral（无硬升级域关键字的订单提交 TDD 夹具），使
  STANDARD/LIGHTWEIGHT 验证路径可被端到端诚实覆盖（tdd-repo 因仓库级风险域标记
  grounding 必然升级 CRITICAL，属 fail-safe 设计而非缺陷）。
- **CD-100**: BLOCKED 也要落 verification.yaml（overall=BLOCKED + blocked_reason，status
  enum 增 pending）；失败的验证留下可审计机器记录而非静默无痕；verify gate 只随技术
  全绿置位。

### 已知风险

- **RISK-022**: 手动验证项在 V0.1 只能 pending 到 REVIEW 阶段，无独立批准 gate；
  Phase 14 需定义 REVIEW 阶段如何把 manual VER 转成有证词的完成态（人/工具链）。
- **RISK-023**: 人工批准身份为字符串证词（actor.id），无签名/凭据校验；真正不可伪造需
  out-of-band 签名，属 post-v0.1（延续 ENF-APPROVAL-001 的 known_deferred 语义）。
- **RISK-024**: CODE 归属依赖 test targets 声明；Agent 漏声明将判 orphan code 而 BLOCKED
  （fail-safe，宁可阻断不静默通过），但可能对未写 targets 的旧计划造成误阻断。
## Phase 13 正式批准与 Phase 14 Feature Freeze（2026-08-14）

- **OWNER-APPROVAL-P13**: PHASE_13_VERIFY_TRACEABILITY_AND_APPROVAL = APPROVED（225/225 PASS）；
  关键裁决确认：VERIFY_MANUAL 回退正确（不修改旧 Contract 迎合新实现）、BLOCKED 落
  verification.yaml 长期保留、MERGE_READY ≠ Merge（V0.1 控制边界）、Human Attestation
  定位可接受（强身份认证 post-v0.1）。
- **OWNER-P14-FREEZE**: Phase 14 进入 FEATURE FREEZE。禁止新增 repair/recover、upgrade、
  CI 深集成、RAG、Web UI、Mutation Testing、Impact Analysis、Multi-Agent Orchestrator、
  新审批体系、新工作流等级等 V0.2 功能。只允许：Pilot 暴露的真实 Bug、P0/P1 release
  blocker、安装/CLI/跨平台问题、安全问题、文档错误、明显 UX 阻塞。所有修复记 release-fix。
- **RELEASE-FIX-001（install）**: 仓库此前无 pyproject.toml/README/LICENSE 等根级资产；
  Phase 14 补齐打包与发布资产；V0.1 安装路径 = 可编辑安装（pip install -e .），
  非可编辑安装的数据文件重定位（core/schemas/bootstrap/adapters 不在 site-packages）
  记为 P2 post-release。
## Phase 14 发布证据与 Release-Fix（2026-08-14，PHASE_14_DOGFOOD_PILOT_AND_V0_1_RELEASE）

### release-fix（全部有测试）

- **RELEASE-FIX-001（install）**: 补齐根级发布资产（pyproject.toml pip install -e .、
  .gitignore、README/LICENSE/CONTRIBUTING/CHANGELOG、examples/）；V0.1 安装路径 =
  可编辑安装（clean-room 全新 venv 验证通过）。
- **RELEASE-FIX-002（P1，dogfood 发现）**: AEH 无法 bootstrap 自己的仓库——多语言/
  多结构事实（repository.language/documentation、architecture.structure）同级冲突
  BLOCKED_POLICY_CONFLICT。修复：discovery-rule 增 multi_fields，compiler 将同 field
  多 repository_fact 确定性折叠为排序列表值（置信度取最强、origin_ref=merged:*）；
  冻结的同级冲突语义对非 multi 字段不变。测试：test_compiler.py +5（22/22）。
- **RELEASE-FIX-003（P1，dogfood 发现）**: grounding TEST 证据 rel_path 相对 tests/
  目录，导致下一阶段必然 stale；且 rebase 时 os.path.relpath 对相对路径按进程 cwd
  绝对化，跨盘（D:→C:）抛 ValueError。修复：rel_path 锚定仓库根 + cwd 无关 join。
  测试：test_grounding.py +1（18/18）。
- **RELEASE-FIX-004（dogfood 修复移植）**: adapters/render.py 模板读取句柄泄漏
  （ResourceWarning）→ with 语句 + _read_text；测试：test_adapters.py +1（16/16）。

### Dogfood 记录

- AEH 对自身仓库完成真实 Change CHG-2026-0001：修复模板句柄泄漏；STANDARD 分类 →
  grounding 硬升级 CRITICAL（自身测试夹具含经济域关键字，fail-safe）→ RED/GREEN/
  REFACTOR/VERIFY + MERGE_GATE 人工证词 → VERIFY_COMPLETE / READY_WITH_WARNINGS。
  全程未伪造；GREEN 一次失败来自 pilot 驱动脚本写入的坏缩进（操作者错误），AEH
  正确判 GREEN_FAILED，修复后 GREEN_COMPLETE——验证器尽职。详见 docs/pilots/dogfood.md。
- 教训（P2，README 已记录）：ground 升级 CRITICAL 后，plan 必须声明 integration/
  contract 验证项；升级在 ground 报告中可见，verify 的 BLOCKED 信息给出明确补救。

### Pilot Matrix（docs/pilots/pilots.md）

- PILOT-A Lightweight: LIGHTWEIGHT → 全链 → MERGE_READY（8 步，0 人工，0 阻塞，7.2s）。
- PILOT-B Standard: STANDARD → MERGE_READY（8 步，0 阻塞，6.4s）。
- PILOT-C Critical: CRITICAL + integration 验证 + 1 次人工批准 → READY_WITH_WARNINGS
  （9 步，6.7s）。
- PILOT-D Explore: HYPOTHESIS/EXPERIMENT/EVIDENCE/DECISION，tdd_forced=false。

### 双平台（docs/pilots/adapters.md）

- 同一 profile → codex/claude 均 RENDERED，semantics 完全相等；deny 字段一致
  （git_push/web_access）；GUIDANCE_ONLY 诚实暴露（codex: git_push + review；
  claude: web_access + review）；managed section 落盘且保留原文。

### Clean-room

- 全新 venv：pip install -e . PASS；aeh doctor（未 bootstrap）诚实 BLOCKED +
  补救提示；aeh bootstrap（无 --answers）fail-safe 默认 + default_applied/UNKNOWN
  provenance；aeh doctor PASS；aeh change new（README 命令形式）PASS。

### Release blocker 分类

- P0: 0。P1: 0（release-fix 002/003 已修复并有回归测试）。P2: 4（manual 验证
  REVIEW 前 pending；CRITICAL 升级后 plan 需含 integration/contract；可编辑安装
  限制；人工批准为证词级）。
## Release Safety Review（2026-08-14，R0–R5，READY_FOR_OWNER_RELEASE）

- **R0 基线冻结**: 无独立 git 仓库（AEH 目录在父仓库内且 untracked）；以
  RELEASE_BASELINE.sha256 内容哈希快照冻结（R0 digest a820587a…，最终 digest
  b27242a8…，184 文件，0 残留）；standalone git init/首次 commit 留待 Owner。
- **R1 公共安全**: secrets 0（全部命中为假 fixture 或领域关键词提示）；
  机器绝对路径 0；private policy 原文 0 泄漏；公开文档中的私有项目名
  （Ares/ET6 等）已泛化改写（RELEASE-FIX-006，语义不变；测试中的禁用词表保留为
  fixture 角色）；egg-info/__pycache__/pyc 清理；.gitignore 覆盖生成物且未整体
  ignore .aeh/。verdict: PUBLIC_SAFE。
- **R2 回归 + Clean-room**: README 推荐命令（unittest discover）此前发现 0 测试 →
  RELEASE-FIX-005（tests/*/__init__.py）修复后 232/232 PASS；全新 venv +
  git 项目：install/bootstrap×2（semantic diff 0、installed_at 稳定、managed 块
  不重复）/doctor READY_WITH_WARNINGS/完整标准链 first change → MERGE_READY，33/33。
- **R3 冷启动**: 全新子代理仅凭仓库公开文档独立回答全部 10 问（安装/bootstra
  p/doctor/首改/五级/扩展/限制），PASS；发现并修复 answers 示例可发现性、
  panorama 目标形态歧义、upgrade 表述（RELEASE-FIX-007）。
- **R4 打包**: README 13 节（第一屏 What/Why/Agents/Install/Quick Start）；LICENSE
  MIT（版权主体 "Adaptive Engineering Harness contributors"，Owner 可替换）；
  CONTRIBUTING 完整（环境/测试/freeze/规则/适配器/契约/ADR/安全上报）；CHANGELOG
  v0.1.0 + 修复 + 限制；examples/minimal、generic-business、answers.yaml；
  版本 0.1.0 一致。
- **Release blockers**: P0=0；P1=0（RELEASE-FIX-005/006 已修复并回归）；
  P2=4（manual 验证 REVIEW 前 pending；CRITICAL 升级后 plan 需 integration/contract；
  仅可编辑安装；证词级批准）。
- **RELEASE-FIX-005**: unittest discover 需包标记 → tests/*/__init__.py；回归 232/232。
- **RELEASE-FIX-006**: 公开安全改写（私有项目名泛化）；语义不变；全量回归 PASS。
- **RELEASE-FIX-007**: 冷启动可发现性（answers 示例/panorama banner/upgrade 表述）。
- **OWNER-RELEASE-EXEC (2026-08-14)**: Owner 裁决：版权主体=YIMO691、公开发布=是、
  P2 限制=接受、push=授权。已执行：git init（main 分支，作者 YIMO691 <noreply>）、
  首个 commit 9c2a1e2131754b7f0f0591c52c9c800073591780、公开仓库 https://github.com/YIMO691/aeh、tag v0.1.0、
  push main + tag 成功；Owner 随后授权补发 GitHub Release 页面：
  https://github.com/YIMO691/aeh/releases/tag/v0.1.0（tag v0.1.0 重定到 main 头
  87061a3，Release Notes 从 CHANGELOG 生成，release id 370637806）。
  未发布 PyPI（未授权）。

## V0.2 M2 Repair / Recovery（2026-08-19）

- **CD-101**: `aeh repair <target>` 默认只生成 `repair.plan`；写入必须显式 `--apply`。
  Doctor 保持只读，诊断权与修复写入权不合并。
- **CD-102**: bootstrap、repair 与未来 upgrade 共用 `aeh.transaction-journal`：第一项
  目标写入前必须落 PREPARED journal 和 before backup；每项写入后记录状态；异常反向回滚。
- **CD-103**: runtime repair source authority = 当前 AEH 包内 canonical runtime，且其 digest
  必须与目标 manifest 的 `source_hashes.runtime` 完全一致；不一致时
  `BLOCKED_REPAIR_SOURCE_MISMATCH`，不得把 upgrade 冒充 repair。
- **CD-104**: Repair plan 只公开相对路径、action、reason、source_ref 与 before/after hash，
  不携带正文；`.aeh/private` 不进入 residue 扫描或 repair backup。
- **CD-105**: 显式 rollback 是全计划 drift gate：已完成事务要求每项等于 after-state；
  中断事务只接受可证明的 before/after-state。任一文件落在两者之外时整体
  `BLOCKED_ROLLBACK_DRIFT`，零写入，不覆盖后续用户修改。apply 也在每项写入前复核
  before-state，漂移项不写并反向恢复本事务此前已写项目。
- **CD-106**: managed block 自动修复只允许替换可界定的 marker envelope，并保留 envelope
  外全部非 marker 文本；无有序 begin/end envelope 时 `BLOCKED_REPAIR_UNSAFE_MANAGED`。
- **CD-107**: `aeh change repair --kind test|spec` 只是冻结状态机条件边的 UX 投影：
  GREEN→TEST_REPAIR 仍需 BLOCKED_TEST_CHANGED，GREEN→SPEC_REPAIR 仍需
  SPEC_CHANGED_IN_GREEN；不得绕过 Doctor、Gate 或审批。
- **CD-108**: transaction path 在计划与应用阶段统一拒绝绝对路径、`..`、跨卷和 symlink
  越界；journal/backup 是机器真值，叙事报告不得替代。

## V0.2 M3 Upgrade（2026-08-19）

- **CD-109**: `aeh upgrade <target>` 默认只生成 `upgrade.plan`；写入必须显式
  `--apply`。M3 完成形成软件 `0.2.0` candidate，但不授权 tag/Release/PyPI。
- **CD-110**: 自动迁移写边界仅为 `.aeh/runtime/core|schemas`（overwrite/remove）与
  `.aeh/manifest.yaml`（merge）。profile、effective workflow、bootstrap answers、private、
  changes/approvals、AGENTS/CLAUDE 和 gitignore 必须 byte-preserved。
- **CD-111**: upgrade 前必须证明 actual installed runtime digest 等于旧 manifest expected
  digest；否则 `BLOCKED_UPGRADE_SOURCE_INTEGRITY`，必须使用匹配旧版本 repair，当前包不得猜测修复。
- **CD-112**: 目标版本高于当前包时阻断 downgrade；版本相同但 runtime digest 不同时
  `BLOCKED_UPGRADE_VERSION_COLLISION`，禁止用同版本号传播可变内容。
- **CD-113**: Upgrade source authority 是当前可信包内 canonical runtime；计划逐文件公开
  action/policy/reason/source_ref/before-after hash，不公开正文或 private 内容。
- **CD-114**: manifest merge 保留 installed_at、未知扩展字段和既有 history；追加的 history
  仅记录 from/to version、revision、runtime digest。时间与逐项状态由 UPG journal 记录。
- **CD-115**: UPG 复用 `aeh.transaction-journal`、before backups、apply drift、异常反向回滚
  与显式 rollback drift gate；rollback 恢复旧版本后 Doctor 版本阻断是诚实结果，不是假失败。
- **CD-116**: M3 不实现 profile recompile、adapter regeneration、任意历史迁移、网络发现、
  自动升级、增量 patch 或多版本并存；这些必须另立迁移契约与授权。

## V0.2.0 Release Safety Review（2026-08-19）

- **RSR-001**: V02-0、M1、M2、M3 按 PR #1→#4 依赖顺序合并；最终 M3 merge commit
  `cc7d93f` 的 tree 与已验收 M3 head `e6f8d5a` 完全一致。
- **RSR-002**: Handbook 确定性校验 PASS（00–26、A–G、Registry、总稿与 SHA-256
  清单）；公开路径 ASCII，secret/private path scan PASS。
- **RSR-003**: 本地集成回归 273/273 PASS；GitHub main 在 Windows/Linux、Python
  3.10/3.11 与双平台 clean-room wheel gate 全部通过。
- **RSR-004**: 固定 `SOURCE_DATE_EPOCH` 双重 wheel 构建哈希一致；wheel metadata、
  console entry point、runtime/core/schema/repair/upgrade 资源边界检查 PASS。
- **RSR-005**: clean-room bootstrap → repair → v0.1-shaped snapshot → upgrade →
  Doctor → first change PASS；repair/upgrade 分别产生 RPR/UPG journal。
- **RSR-006**: Release blocker：P0=0、P1=0；测试代码中的既有文件句柄
  `ResourceWarning` 记为 P2 工程债，不影响当前确定性或功能验收。
- **RSR-VERDICT**: `READY_FOR_OWNER_RELEASE`。此裁决不自动授权或执行 tag、
  GitHub Release、PyPI；产品有效性仍为 `NOT_YET_PROVEN`，Phase 2 / 72-run 未授权。

## V0.2.0 Owner Release Execution（2026-08-20）

- **OWNER-RELEASE-EXEC-V020**: Owner 指令“执行”在前序明确选项下按安全默认解释为
  GitHub 发布：合并发布状态记录、创建轻量 tag `v0.2.0`、创建公开 GitHub Release，
  并附加经固定 build epoch 双重构建验证的 relocatable wheel。PyPI 属独立分发渠道，
  未获明确授权，不执行。
- **RELEASE-BOUNDARY-V020**: GitHub 发布不改变研究裁决；产品有效性继续为
  `NOT_YET_PROVEN`，Phase 2 / 72-run 继续未授权，M4 亦未自动启动。

## Post-eval Machine Truth Isolation（2026-08-25）

- **CD-117**: RED 成功进入 LOCK_TEST 后、Coding Agent 开始前，Controller 在受管仓库外
  保存 change-scoped YAML/JSON 的精确路径集合与 SHA-256；GREEN、VERIFY、REVIEW 及
  此后的 trusted approval 在读取机器真值前必须比对，added/removed/modified/symlink 均返回
  `BLOCKED_MACHINE_TRUTH_PROVENANCE`。
- **CD-118**: Controller state root 默认使用 OS user-state 目录；
  `AEH_CONTROLLER_STATE_DIR` 仅作部署与测试覆盖，解析后位于 target 内必须阻断。
  仓库内普通 hash 不构成所有权证明。
- **CD-119**: 旧版本进行中的 Change 若没有外部检查点，GREEN/VERIFY fail closed 为
  `BLOCKED_CONTROLLER_CHECKPOINT_MISSING`，必须经 governed repair 重放 RED 或重启 Change；
  GREEN/VERIFY 不得在首次看到现有机器真值时自动信任并补建检查点。
- **CD-120**: 测试命令属于仓库控制的不可信执行。Repeated RED、GREEN/REFACTOR、VERIFY
  在测试子进程退出后、读取批准或写入/重封存机器真值前必须再次核对 Controller
  checkpoint，阻断测试期 evidence/approval laundering。Change 工作区根及其父级中的
  symlink/Windows reparse point 同样 fail closed；强隔离仍依赖 OS/filesystem boundary。

## V0.2.1 Integrity Patch Preparation（2026-08-26）

- **CD-121**: v0.2.1 是仅承载 CD-117–120/RUN-F055 修复的补丁候选，不自动吸收 M4、
  分类调优、评测协议重构、A01–A08 或新的平台能力。
- **CD-122**: 包、Bootstrap manifest、Doctor compatibility 与 Discovery scanner 的公开
  软件版本统一提升为 `0.2.1`；compiler compatibility 与 runtime schema version 不变。
- **CD-123**: 从完整性有效的 v0.2.0 manifest 升级到 v0.2.1 必须走现有 plan-first
  upgrade，并只产生可解释的 manifest/runtime 差异；项目 profile、workflow、private、
  changes、approvals 和 agent files 继续 byte-preserved。
- **CD-124**: 补丁准备权限止于 review PR。tag、GitHub Release、PyPI、模型复测、
  A01–A08 与 PR merge 均保留独立 Owner Gate；候选不得把漏洞修复表述成有效性证明。

## AEW Integration Boundary（2026-08-26）

- **CD-125**: Agent Engineering Workspace（AEW）与 AEH 不合并。AEW/外部系统拥有
  Project/Task/Run、Provider、Runtime 与恢复状态；AEH 继续唯一拥有工程 Change 的
  Ground/Spec/RED/GREEN/Test Lock/Verify 语义及接受判定。
- **CD-126**: 集成采用只读、确定性、Schema 校验的导出 envelope。外部 Task/Run ID
  是引用，不写入或镜像成 AEH 的第二套可变任务真值；导出不包含证据正文，只包含相对
  路径、类型与 SHA-256。
- **CD-127**: 每个导出显式表达 Scope、Ownership、Authority、Lifecycle、Provenance、
  Cost。Portable verdict 仅作跨系统映射，AEH 原生 `MERGE_READY / READY_WITH_WARNINGS /
  BLOCKED` 始终保留且具有工程治理权威。
- **CD-128**: SCM inspection 只执行本地、无网络、无写入、资源有界的检测。支持识别
  Git、SVN、无 SCM 和有限深度的嵌套仓库；SVN 识别不等于完整 AEH 生命周期已经取得
  SVN 认证。
- **CD-129**: AEW State Store、Memory、通用 Runtime/Sandbox、多 Agent 编排和证据
  大规模复制均不进入 AEH Core。后续采用适配器与引用集成，并以实际 Pilot 的成本收益
  决定是否扩展。

## M4 Approval and Manual Verification Governance（2026-08-26）

- **CD-130**: `VERIFY_MANUAL` 是独立的人工作证 Gate，不与 `MERGE_GATE` 合并。只要
  test plan 声明 manual verification，该项必须得到有效人类证词；成功结果写为
  `verdict=approved`，不得伪装成 automated test pass。
- **CD-131**: `APPROVED` 可声明 1–2,678,400 秒 TTL 并派生 `expires_at`。为兼容旧
  `approvals.yaml`，缺少 expiry 的批准继续有效但在消费时产生显式 WARN；过期批准一律
  不满足 Gate。
- **CD-132**: 显式撤销只作用于已有 APPROVED 记录，保留原 `actor/decided_at`，追加
  `revoked_by/revoked_at` 与可选证据引用；不存在或非 APPROVED 的记录不可被伪造为撤销。
- **CD-133**: CRITICAL plan 缺 integration/contract verification 时必须在 TEST_DESIGN
  阻断，早于测试文件和 test-plan 机器真值写入；VERIFY 保留同一校验以覆盖旧的进行中
  Change 与纵深防御。
- **CD-134**: M4 的本地实施授权不包含版本选择、push、PR、merge、tag、Release 或
  PyPI。v0.2.1 候选的冻结边界不被此 feature branch 静默改写。

## M4 Post-Merge Version Reconciliation（2026-08-27）

- **CD-135**: M4 已通过 PR #11 合并到 `main`；其合并前 12/12 检查和合并后 6/6
  `main` 作业均通过。此前“本地已验证、未合并”的表述不再是当前事实。
- **CD-136**: M4 是向后兼容但用户可见的治理能力增量，因此进入新的 minor 开发线
  `0.3.0.dev0`，不得静默塞入仅承载完整性修复的冻结 v0.2.1 patch candidate。
- **CD-137**: `.dev0` 明确表示源码与 wheel 尚非最终 `v0.3.0` Release；最新公开版本
  继续为 `v0.2.0`，tag、Release 与 PyPI 仍需独立 Owner 决策。
- **CD-138**: 当前升级比较器只扩展到严格的 `X.Y.Z` 与 `X.Y.Z.devN`。排序冻结为
  `0.2.1 < 0.3.0.dev0 < 0.3.0.dev1 < 0.3.0`；其他预发布格式继续 fail closed。
- **CD-139**: `docs/releases/v0.2.1/` 与关联冻结证据保持版本绑定，不因后续 M4 合并
  或版本线调整而回写。
