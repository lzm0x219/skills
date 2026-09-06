# durable-execution-state 优化记录

日期：2026-09-07。基于 `a7fbbd8` 的工作树，检查入口、状态工具、宿主验证器接口和恢复评测。

## 已修正的问题

- 中文授权引用会触发 `hmac.compare_digest` 的非 ASCII 字符串异常。现以 UTF-8 字节进行精确比较，并通过公开 CLI 验证中文请求的登记与重放。
- 验证器响应缺少必填字段但含有 `expires_at` 时，原集合判断可能漏检并产生 `KeyError`。现分别检查必填字段完整性与允许字段集合；已记录授权证明使用相同修正。
- 非字符串授权模式、非 UTF-8 验证器输出现在返回可处理错误；无效响应不会新增 pending 或改变版本。
- 入口明确区分普通状态维护和真实外部动作；`reused=true` 只复用登记，不能直接触发再次派发。目标改变、提交后失败和快照损坏都有明确恢复分支。

## 可运行交付

- [宿主接入说明](../../skills/development/workflows/durable-execution-state/references/host-integration.md)：四种使用模式、固定 wrapper、批准文件和恢复决策。
- [批准文件验证器示例](../../skills/development/workflows/durable-execution-state/scripts/approval_file_verifier.py)：校验宿主预先批准的完整请求 hash、授权引用与有效期；不执行业务动作，也不自行建立信任根。
- [恢复演练](../../skills/development/workflows/durable-execution-state/scripts/rehearse_recovery.py)：只通过公开 CLI 操作临时状态，覆盖提交前回滚、提交后动作恢复、snapshot 重建、登记去重、回执恢复与回执去重。

宿主示例在隔离测试中可运行，但真实宿主仍须保护程序、解释器、wrapper 与批准文件。演练没有发布、发送消息或调用外部业务 API。

## 本机协议基线

运行 `rehearse_recovery.py --steps 100` 三次；Python 3.14.7，macOS 26.6.2，arm64。命令、源文件 SHA-256 和逐次结果保存在 [原始测量 JSON](durable-execution-state-rehearsal.json)。

| 运行 | patch median / P95 | replay    | 最终版本 / 事件数 |
| ---- | ------------------ | --------- | ----------------- |
| 1    | 36.980 / 57.461 ms | 37.218 ms | 104 / 105         |
| 2    | 37.256 / 38.725 ms | 35.459 ms | 104 / 105         |
| 3    | 36.151 / 38.027 ms | 36.990 ms | 104 / 105         |

三次都完成六项恢复检查，`verified=true`。这个固定样例的补丁阶段峰值序列化状态为 425 bytes，最终状态为 611 bytes。计时包括 Python 进程启动；这些是协议演练基线，不是模型 token、进程内存、生产系统性能或优化前后收益。

## 验证与实时抽样

行为契约从 8 个增至 15 个：14 个文本案例与 1 个既有 workspace 案例。新增覆盖状态维护无需验证器、自建验证器不可信、重复登记不能再次派发、提交后对账、外部证据失效、演练结论边界与目标交接。

本轮固定答案验证 14 个文本案例全部通过；workspace 场景仍由其专用运行器负责，本轮未重复执行 live workspace 场景。确定性单测检查了真实 CLI、Unicode 引用、畸形证明、示例验证器拒绝路径以及恢复演练。

最终全量单元测试 184 项：179 项通过，5 项因当前环境缺少 Pillow 而跳过，均为既有图片 helper 测试。格式检查、静态验证（9 个 Skill、52 个 Skill Markdown、81 个本地链接）与 `git diff --check` 通过。

实时抽样明确使用 GPT-6 Astra、`high` 推理强度，调用应用自带 Codex CLI 0.153.4。每个场景运行一次：状态维护无需验证器、自建验证器不可信、重复登记不能再次派发。原始输出保存在 [实时记录](durable-execution-state-live.txt)。

初次评分 2 项通过、1 项因漏认“阻塞发布”被误拒。补充该等价表达与单元回归后，对相同的三份已捕获回答重新评分全部通过，没有重新生成答案。未将这次抽样当作真实跨会话恢复或长程成功率证据。

此前用本机 CLI 0.146.0 尝试同样抽样，被服务端以 `The 'gpt-6-astra' model requires a newer version of Codex` 拒绝，没有获得模型答案；随后切换已安装的应用内 CLI，没有升级或修改全局配置。
