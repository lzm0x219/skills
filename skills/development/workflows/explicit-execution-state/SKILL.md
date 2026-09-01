---
name: explicit-execution-state
description: 为需要跨上下文压缩、恢复或交接的长程任务维护有界、可回放、可验证的执行状态；也适用于需要幂等对账的外部副作用，或必须外部化的超大、高噪声观察。短小无状态任务不适用。
---

# 显式执行状态

把当前执行状态作为长程任务的规范工作视图；把仓库、Git、测试、工具回执和权威外部系统作为事实来源。状态用于继续工作，不替代事实核验，也不保存完整会话。

理论来源：本 Skill 的核心思想基于 Sanket Badhe、Priyanka Tiwari、Jonghyun Chung 的论文 [《SKILL.state: Scalable Long-Horizon Agent Skills》](https://arxiv.org/html/2608.26263v2)。SQLite 事务存储、授权协议、故障注入与行为评测是本仓库面向 Codex 的工程扩展，不代表论文原始实现。纯 Skill 无法控制宿主每轮注入哪些历史或何时丢弃旧推理，因此只能实现显式状态协议，不能单独保证论文依赖宿主运行时的 `O(1)` prompt/token 性质。

## 1. 通过适用性门槛

满足以下任一条件时启用：

- 任务需要跨恢复、上下文压缩或交接继续；
- 多个相互依赖的动作共享会变化的事实；
- 外部副作用需要幂等、恢复或审计；
- 原始观察过大或噪声过多，不适合继续留在会话中。

短小、无状态的任务直接退出本 Skill，不创建状态存储。

若请求限定为规划、说明或禁止执行，只输出适用的状态与转换协议，并明确未联网、未写文件、未执行外部副作用。规划涉及外部副作用时，完整读取 [状态转换协议](references/transition-protocol.md)，写明授权、请求 hash 和 fail-closed 门槛。

完成条件：已明确任务需要显式状态的具体原因；否则已退出本 Skill。

## 2. 初始化任务状态

使用环境指定的 scratch 目录；若环境没有约定，则使用目标工作区内的 `work/agent-state/<task-slug>/`，不要写入运行时保留的 `.codex/`。并发任务使用不同目录。先读取 [状态模型](references/state-model.md)，再准备稳定的 task ID、单一目标、可验证完成条件和已确认约束。

调用本 Skill 目录下的 `scripts/statectl.py`，通过 `init` 创建 SQLite 存储。Agent 只读取生成的 `state.snapshot.json`；该状态存储的所有写入都通过 `statectl.py` 完成。

`verify` 只检查数据库、snapshot、版本和 pending action 的内部一致性，不访问外部证据。完成条件：`verify` 成功，且已另外确认 snapshot 中的目标、完成条件和约束与当前请求一致。

## 3. 维护有界观察

每轮只把最新观察中会改变下一步决策的信息写入状态。大日志、原始响应和历史事件保存在外部证据文件中，状态只保存稳定引用、当前值和必要摘要。确认事实与假设分开；推断不能覆盖权威事实。

使用 `apply-patch` 提交最小局部补丁；高风险或复杂补丁先用 `validate-patch` 做无写入检查。补丁必须基于当前 `state_version`，通过 schema、允许路径和状态不变量校验。省略字段保持不变，模型输出不能替换完整状态或整个状态集合。

完成条件：接受的补丁具有当前版本和证据引用，核心状态仍在大小预算内。

## 4. 执行外部动作

首次执行有副作用的动作前，完整读取 [状态转换协议](references/transition-protocol.md)。先取得真实授权引用；宿主必须在模型不可修改的信任域中选择并固定验证器，再调用 `begin-action`。CLI 对路径和权限的检查不是信任根。没有宿主固定的验证器时停止并请求授权。

`--allow-reference-authorization` 仅用于不会调用外部副作用的演练或隔离测试；它会把授权明确记录为 `reference-only`，不能作为生产授权。随后执行工具，并使用权威回执调用 `resolve-action`；只有已观察到的效果才能写入确认事实。

失败或部分成功时记录真实结果，并选择明确的重试、补偿或升级路径。本地协议只去重动作登记；真实副作用必须由外部系统接受同一幂等键，或由宿主 outbox/executor 保证。结果未知且缺少该保证时先对账，不盲目重试。状态冲突或无效补丁只做有界重试；重复失败后改用确定性替代或请求用户输入。

完成条件：真实副作用具有 `trusted-verifier` 授权记录和权威回执；确定结果已转为 confirmed 或 failed，部分或未知结果仍明确保持 pending；状态与环境一致。

## 5. 恢复与对账

恢复时先运行 `show` 和 `verify`；`verify` 会从事件账本重放并核对当前状态。再核验 Git、文件、测试或外部系统中容易漂移的事实。出现差异时先通过带证据的补丁对账，再选择下一动作。只有状态和证据仓库缺少必要信息时，才从会话历史精确恢复该信息。

若用户只要求说明恢复顺序，必须明确这是未执行的顺序，不得声称已经运行 `show`、`verify` 或测试。

多 Agent、版本冲突、工具超时、部分成功或迟到回执按 [状态转换协议](references/transition-protocol.md) 处理。

完成条件：当前 snapshot 通过验证，所有漂移事实均已确认或明确标为 blocker/hypothesis。

## 6. 完成任务

为每个完成条件写入当前证据引用，清空已解决 blocker，并确认不存在 unresolved pending action。先实际访问或运行外部证据与 required checks，再调用 `complete`；该命令验证内部完成门槛并写入最终状态，不替代外部核验。

最终回复报告完成结果、主要证据、未解决风险和最终产物。私有逐步推理、秘密和无关历史不进入状态、事件或交付物。

完成条件：`complete` 成功，所有完成条件有证据，required checks 通过，pending action 为零。

## 确定性资源

- [状态模型](references/state-model.md)：首次初始化、设计字段、状态超限或事实/假设边界不清时读取。
- [状态转换协议](references/transition-protocol.md)：副作用、恢复、冲突、并发或部分失败时读取。
- [评测协议](references/evaluation.md)：基准测试、回归评测或声称长程收益时读取。
- `references/schemas/`：集成其他运行时或检查 JSON 接口时使用。
- `scripts/statectl.py`：稳定 CLI 和状态存储的唯一写入口；内部 `statectl_runtime/` 模块不是 Agent 调用接口。运行 `--help` 查看当前命令。
