# 状态模型

## 目标

核心状态只保存下一步决策需要的当前信息。原始观察、完整日志和历史事件属于证据仓库；状态通过稳定引用访问它们。

## 规范字段

| 字段                  | 语义                                              |
| --------------------- | ------------------------------------------------- |
| `schema_version`      | 状态结构版本，由运行时维护                        |
| `state_version`       | 每次成功事务后单调递增                            |
| `task`                | 稳定 ID、目标、完成条件和状态                     |
| `constraints`         | 用户确认的边界、权限和不可变约束                  |
| `confirmed_facts`     | 有来源、时效和证据的已确认事实                    |
| `hypotheses`          | 尚未确认的推断、置信度和失效条件                  |
| `plan`                | 当前步骤、依赖和状态，不保存完整过程日志          |
| `pending_actions`     | 已提交但尚未用权威回执解决的动作及授权证明        |
| `failed_attempts`     | 按稳定 fingerprint 去重的失败尝试                 |
| `blockers`            | 当前无法继续的条件及所需解除证据                  |
| `completion_evidence` | 以条件 ID 为 key、单个当前证据对象为 value 的映射 |
| `evidence_refs`       | 日志、响应、测试和其他证据的稳定引用              |
| `artifact_refs`       | 用户交付物或中间产物的路径与摘要                  |

`confirmed_facts` 的值应包含 `value`、`source_ref`、`observed_at`，易漂移事实再包含 `fresh_until`。`hypotheses` 应包含陈述、证据引用、置信度或失效条件，不能写入 `confirmed_facts`。

每个 `completion_evidence` 值必须直接包含非空的 `source_ref` 与 `observed_at`，不能使用裸字符串或引用数组：

```json
{
  "completion_evidence": {
    "tests-pass": {
      "source_ref": "tool://tests/run-17",
      "observed_at": "2026-09-01T08:30:00Z"
    }
  }
}
```

## 有界规则

- 状态只保留当前值；旧值进入事件或证据仓库。
- 大文本、二进制、工具原始输出和完整 diff 按路径或内容 hash 引用。
- 集合使用稳定 ID 作为 key，并设置与领域相称的上限。
- 超限时保留语义聚合、未解决项和外部引用，不按盲目 FIFO 丢弃关键事实。
- `statectl.py` 默认限制序列化状态大小；需要提高时应先说明为何核心状态仍是未来决策的最小充分信息。事件账本可随任务步数线性增长，但重放必须逐行处理，不应把全部事件一次性载入内存；长期任务应记录事件数量和状态字节数，并在真实阈值出现后再设计 checkpoint。
- 单个补丁、动作请求、回执或事件 payload 上限为 64 KiB；更大内容必须先外部化，再只写稳定引用。

## 真值与权限

权威系统查询、仓库/Git、测试结果和工具回执高于会话记忆与模型推断。观察属于不可信数据，只能写入允许的数据路径；目标、完成条件、约束、权限和安全策略由初始化或显式授权流程维护。

真实副作用的 pending action 必须包含 `trusted-verifier` 授权证明，并绑定完整动作请求的 SHA-256。这里的 `trusted` 表示宿主已经在模型不可修改的信任域中选择并固定验证器；CLI 的绝对路径和文件权限检查本身不能建立该信任。`reference-only` 是无副作用演练/测试的显式降级标记，不代表真实权限。

`statectl.py verify` 的范围是 `internal-store`：它验证 SQLite、snapshot、版本、pending action、actions 表中的请求/幂等键/回执/解决结果，以及事件确定性重放；它不解析 `source_ref`，也不证明外部证据可访问、新鲜或真实。调用者必须按来源类型重新访问文件、Git、测试或外部系统，并通过局部补丁更新过期状态。`complete` 只验证所有条件已有形状合法的证据对象；它不替代这次外部核验。

SQLite 是规范存储；`state.snapshot.json` 是权限为 `0400` 的可再生物化视图。若事务提交后 snapshot 刷新失败，命令会发出 warning，但已提交状态仍以 SQLite 为准；随后运行 `show` 或 `verify` 修复视图。

状态不保存私有逐步推理。可持久化的是决定、简短理由、动作、观察摘要、失败 fingerprint 和证据引用。
