# Adaptive Engineering Harness（AEH）

[![AEH regression](https://github.com/YIMO691/aeh/actions/workflows/regression.yml/badge.svg?branch=main)](https://github.com/YIMO691/aeh/actions/workflows/regression.yml)
[![Latest release](https://img.shields.io/github/v/release/YIMO691/aeh)](https://github.com/YIMO691/aeh/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) · [Codex 使用指南](docs/codex-usage.md) · [文档导航](docs/README.md)

> 状态：**CURRENT**
> 当前源码：`0.3.0.dev0`（未发布）· 最新 GitHub Release：`v0.2.0` ·
> M1–M6 已合并 · PyPI 未发布

AEH 是面向 AI 辅助软件开发的独立验收层。Codex 负责完成修改，AEH
负责把需求、测试、证据、人工批准和最终判断变成明确、可复核、可重放的记录。

它适合“出错成本明显高于重做成本”的工作，例如共享协议、权限、迁移、资金、
发布、基础设施、安全，以及高自主 Agent 执行的修改。

## 它实际解决什么问题

不用 AEH 时，同一个 Agent 可以写代码、运行自己选择的测试，再告诉你“已经安全”。
用了 AEH 后，实施与验收被分开：

```text
你的意图 -> 与风险匹配的流程 -> 实施 -> 独立检查 -> 你的决策
```

AEH 会记录任务要求、锁定测试证据、拒绝非法状态跳转，并在需要授权时停在人工
Gate。Agent 的解释和测试通过都很有价值，但不会单独被当成可信结论。

## 在 Codex 中怎么用

仓库安装 AEH 后，可以直接对 Codex 说：

> 使用 AEH 完成这个修改。先读取仓库规则，选择满足风险的最轻流程，创建 Change，
> 在本地实施并验证。除非我单独授权，否则停在 commit、push、PR、合并、发布或任何
> 需要凭证的 Gate 之前。

小 Bug 可以这样说：

> 修复空列表提示错误。这是一个小 Bug，请增加针对性回归测试，使用证据允许的最轻
> AEH 流程，只在本地修改和验证。

高风险修改可以这样说：

> 使用 AEH 修改支付权限判断。按 CRITICAL 处理，保留原始证据，并在每个人工 Gate
> 停下等待我的独立授权。

更多可复制提示词、阶段授权写法和 Codex 应报告的内容见
[《在 Codex 中使用 AEH》](docs/codex-usage.md)。

## 小 Bug 会不会太重

不会强制所有任务走同一套流程。AEH 按风险分级：

| 级别 | 适用场景 | 典型流程 |
|---|---|---|
| `DIRECT` | 很小、低风险、容易回退的修改 | 分类 → 实施 → 基础验证 |
| `LIGHTWEIGHT` | 能用一个聚焦回归测试描述的普通 Bug | 定向取证 → Bug 契约 → RED/GREEN → 验证 |
| `STANDARD` | 功能开发、跨文件行为变化 | 取证 → 规格 → 测试设计 → RED/GREEN → 审查 |
| `CRITICAL` | 安全、资金、身份、权限、迁移、发布或高影响自动化 | STANDARD，加独立人工 Gate 和更强证据 |

`EXPLORE` 用于允许丢弃的实验，也可以在证据成熟后提升为正式 Change。若仓库证据
显示影响范围更大，分类可以自动升级，Agent 不应静默降级。

## 安装

AEH 需要 Python 3.10 或更高版本。目前没有发布到 PyPI。

用于开发或你明确信任的源码检出：

```bash
git clone https://github.com/YIMO691/aeh.git
cd aeh
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX:   source .venv/bin/activate
python -m pip install -e .
aeh --help
```

如果使用正式发布版本，优先从可信的
[GitHub Release](https://github.com/YIMO691/aeh/releases/latest) 获取 wheel，并核对其中
记录的 SHA-256。不要根据项目名推断存在 PyPI 包。

## 给仓库接入 AEH

建议先在可丢弃仓库试用：

```bash
aeh bootstrap /path/to/project
aeh doctor /path/to/project
```

Bootstrap 会安装带版本的 `.aeh/` Runtime 快照和 Agent 管理说明。Codex 开始实施前会
读取 `AGENTS.md`、`.aeh/profile.yaml` 和 `.aeh/effective-workflow.yaml`。

如果你希望直接操作 CLI：

```bash
cd /path/to/project
aeh change new "fix duplicate claim side effect" --level LIGHTWEIGHT
aeh change status CHG-2026-0001
```

后续命令由有效工作流决定。完整生命周期、修复、升级、批准、CI replay 和协作边界见
[工程指南](docs/engineering-guide.md)。

## 授权要分阶段

AEH 不会把“实施”理解成“可以发布”。建议把授权拆开：

1. 检查与方案；
2. 本地修改与验证；
3. commit；
4. push 与创建 PR；
5. 合并；
6. tag、Release、部署或发布。

需要凭证的 Gate 还要单独授权。凭证应只绑定一个 Change 和一个 Gate，放在仓库与
证据之外，也不能复用于其他 Gate。

AEH 本身停在受治理的决策边界，不会自动 push、创建 PR、合并、部署或发布。

## 能力边界

AEH 当前提供版本化契约、证据完整性、测试锁定、显式写入边界、受约束进程启动、
凭证绑定批准、只读 CI replay，以及单机本地文件系统上的 Change 协作。

它不提供：

- 公钥身份、法律不可否认性、企业 IAM 或硬件密钥保管；
- 内核、容器、虚拟机、文件系统、网络、系统调用或完整进程树隔离；
- 不可绕过的托管 CI 服务或自动分支保护配置；
- 跨主机或网络文件系统协作正确性；
- 自动 push、PR、合并、部署、Release 或 PyPI 发布。

HMAC 只能证明持有配置的共享秘密，不能证明法律身份；仓库中的源码也不能证明外部
SCM 控制已经生效。精确边界见 [M5 安全](docs/m5-security.md)、
[M6.2 GitHub assurance](docs/m6-2-github-assurance.md) 和
[M6.3 协作](docs/m6-3-coordination.md)。

## 当前状态

当前源码版本是 `0.3.0.dev0`，最新公开版本是 `v0.2.0`。M1–M6 和
M6.3A/B/C 已合并，但当前源码线仍未发布，PyPI 也未发布。当前回归基线共 412 个
测试：408 个通过，4 个 Windows 符号链接权限用例按预期跳过。

精确合并和 CI 证据见[当前状态](docs/status.md)。
[V0.2 路线图](docs/roadmap-v0.2.md)现在是已完成、版本绑定的规划记录，不再承担当前
运行状态的权威来源。

## 继续阅读

- [在 Codex 中使用 AEH](docs/codex-usage.md)
- [文档导航](docs/README.md)
- [为什么需要 AEH](docs/about.md)
- [当前状态](docs/status.md)
- [当前架构](docs/architecture-current.md)
- [工程指南](docs/engineering-guide.md)
- [安全边界](docs/m5-security.md)
- [参与贡献](CONTRIBUTING.md)

## License

[MIT](LICENSE)
