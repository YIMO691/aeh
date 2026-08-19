# 附录 A · 术语表

| 术语 | 定义 |
|---|---|
| Agentic Coding | Coding Agent 能自主搜索、规划、编辑、执行和迭代的软件开发方式。 |
| Generator | 负责生成/修改实现的 Agent。 |
| Change | 一次有边界的软件变更单元。 |
| Change Assurance | 对某次具体 Change 是否具备足够工程可信度的判断。 |
| Agent Claim | Agent 自己声称的完成状态。 |
| Task Outcome | 功能事实上的验收结果。 |
| Assurance Outcome | 工程可信性与接受条件的结果。 |
| Acceptance Authority | 有权产生接受/阻断判定的权威路径或机制。 |
| Contract | 定义本次 Change 必须满足的机器可判定约束。 |
| Evidence | 支持或反证工程 Claim 的可检查事实。 |
| Provenance | Evidence 来自谁、何时、哪个版本/环境/命令。 |
| Freshness | Evidence 对当前 Source State 是否仍有效。 |
| Oracle | 判断实现是否正确的外部成功标准。 |
| Oracle Integrity | Oracle 在被用于验收时未被被验证实现无痕改写。 |
| Test Lock | AEH V0.1 用 Hash 冻结 Test/Protected Artifact 的机制。 |
| Scope | 本次 Change 被授权修改的范围。 |
| Scope Integrity | 实际变更与授权 Scope 一致。 |
| Traceability | REQ→AC→TEST→CODE→VER 的映射。 |
| Artifact Integrity | 机器工件内容与预期 Hash/来源一致。 |
| Trusted Mutation Boundary | 规定谁有权修改机器真值的边界。 |
| Guidance | 告诉 Agent 应怎样做，但本身不决定合法性。 |
| Normative Contract | 定义合法数据/状态/迁移。 |
| Enforcement Engine | 独立读取真实状态并阻止非法迁移。 |
| Evaluation | 多 Task/Trial 层面测量 Agent/Harness/System 表现。 |
| PoV | Proof-of-Value，证明 AEH 是否有增量产品价值的实验。 |
| MERGE_READY | AEH 的接受判定，不等于实际 merge。 |
| GUIDANCE_ONLY | 控制只有指导语义，没有硬 Enforcement。 |
| ENFORCEABLE | 当前平台/路径能够实际执行相应控制。 |
| BLOCKED | 证据或条件不足，禁止进入目标状态。 |
