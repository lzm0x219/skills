# 状态转换协议

## 局部补丁

每个补丁携带 `expected_version`。运行时验证 JSON 结构、允许路径、类型、状态不变量和权限后，在单个事务中应用补丁并递增 `state_version`。版本不匹配时重新读取当前状态并重算；不得把陈旧补丁强行套用到新状态。

模型只提出 `add`、`replace` 或 `remove` 局部操作。集合根路径不可写；`add` 不得覆盖已有 key，更新已有值必须显式使用 `replace`。省略字段保持原值，完整状态替换不是有效补丁。复杂补丁先运行 `validate-patch`，确认候选版本、大小和不变量后再提交。

## 两阶段外部动作

1. `begin-action` 先通过宿主固定的授权验证器核验批准与请求 hash，再在事务中校验版本、当前任务状态和结构化前置条件，写入授权证明、pending action 与幂等键。
2. 事务提交后再执行外部工具，避免持锁等待网络、进程或人工审批。
3. 保存退出码、外部对象 ID、观察时间和权威回执引用。
4. `resolve-action --outcome confirmed` 只接受 `succeeded` 回执，`--outcome failed` 只接受 `failed` 回执。
5. `partial` 或 `unknown` 回执使用 `--outcome pending`：记录最新观察和已确认的局部效果，但不清除 pending。
6. 部分成功进入显式 retry、compensation 或 escalation，不伪装成原子成功。

重复提交同一幂等键和相同请求时先返回原动作，不重新要求授权或创建登记；相同幂等键配不同请求时拒绝。这个约束只保证本地登记去重：执行器必须把同一幂等键传给支持幂等的外部系统，或通过宿主 outbox 把一次登记对应到至多一次派发。两者都没有时，不得声称 exactly-once；意图中的效果在权威回执出现前保持 pending/unknown。

动作请求中的 `preconditions` 使用可判定 JSON Pointer 条件，operator 仅为 `exists`、`absent`、`equals` 或 `not_equals`。`authorization_ref` 必须指向真实用户授权或既有策略；不得由模型虚构。

```json
{
  "idempotency_key": "deploy:release-1",
  "tool": "deploy",
  "args": { "release": "1" },
  "authorization_ref": "user-request://turn-42",
  "preconditions": [
    {
      "path": "/completion_evidence/tests-pass",
      "operator": "exists"
    }
  ]
}
```

同一 action 的相同 outcome、回执和补丁可安全重试，即使调用者仍携带提交前的旧版本；不同结果仍要求最新版本。任务完成后拒绝新的补丁和动作。

每个回执必须带回原动作的 `idempotency_key`；运行时要求它与 action 记录完全一致，避免迟到或串线回执解决错误动作。

## 授权验证器

真实副作用默认 fail closed。`begin-action` 要求 `--authorization-verifier <absolute-path>`；路径必须指向状态目录之外、可执行且不可被 group/world 写入的宿主程序。运行时不经 shell 调用它，超时为 5 秒。

验证器从 stdin 接收规范 JSON：

```json
{
  "request": { "tool": "deploy", "args": {} },
  "request_sha256": "sha256-of-canonical-request"
}
```

其中 hash 基于完整动作请求的 UTF-8、key 排序、无多余空白 JSON。验证器成功时从 stdout 返回不超过 64 KiB 的单个 JSON 对象：

```json
{
  "authorized": true,
  "authorization_ref": "approval://release-1",
  "request_sha256": "sha256-of-canonical-request",
  "verifier_ref": "host-policy://production-release/v3",
  "verified_at": "2026-09-01T00:00:00Z",
  "expires_at": "2026-09-01T00:10:00Z"
}
```

`expires_at` 可省略；提供时必须晚于验证时间且在验证时尚未过期。运行时要求授权引用和请求 hash 精确匹配，并把证明写入 pending action 与事件账本。验证器必须由宿主选择并固定在模型不可修改的信任域；模型自行创建、修改或选择的程序不构成可信授权。CLI 只执行防误配检查，不能判断调用者是否真正处于该信任域。

`--allow-reference-authorization` 是显式降级，只允许不会实际调用外部动作的演练或隔离测试。它记录 `reference-only` 与 `unverified://explicit-downgrade`；一旦选择该模式，后续执行器也必须保持无副作用，不能用它绕过生产授权。

## 并发和恢复

本地 SQLite 使用单写事务和 `state_version` 乐观锁。两个 Agent 可以并行读取，但冲突写入必须有一个失败并重算，不能静默 last-write-wins。

隔离测试可设置 `STATECTL_FAULT_POINT=<operation>.before-commit` 或 `<operation>.after-commit` 注入确定性故障；operation 为 `init`、`apply-patch`、`begin-action`、`resolve-action` 或 `complete`。commit 前故障必须回滚；commit 后故障表示调用结果未知，恢复时先 `show`/`verify`，再按版本或幂等键对账。不要在真实任务中设置该变量。

崩溃恢复顺序：

1. 从 SQLite 读取规范状态并重新生成只读 snapshot；
2. 查找 pending action；
3. 通过幂等键或外部对象 ID 查询真实结果；
4. 依据回执 resolve，而不是盲目重放动作；
5. 与权威事实源对账后继续。

`verify` 在单个 SQLite 只读事务中，从 `initialized` 事件开始按序流式重放全部局部转换，并要求得到与同一数据库快照中的当前状态以及 actions 请求/回执投影完全相同的结果；`replay` 可单独输出事件数量、状态字节数与最终状态 hash。snapshot 损坏或缺失时从 SQLite 重建，不从 snapshot 反向覆盖数据库。

迟到回执只能解决对应 action ID，且必须与原幂等键和请求匹配。无法判定结果时保持 unknown/pending 并升级，不通过猜测清除。

## 完成门槛

任务仅在以下条件全部成立时完成：

- 每个 completion criterion 都有非空、当前的证据引用；
- `pending_actions` 为空；
- `blockers` 为空；
- 状态通过 schema 与数据库一致性检查；
- 必需的外部检查真实运行并成功。

其中 `verify` 与 `complete` 只执行内部一致性门槛；调用者负责重新访问外部证据并确认其新鲜度与真实性。
