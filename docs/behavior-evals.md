# 行为评测如何工作

本仓库的行为评测检查 Skill 对代表性请求的最终可见回答。它补充静态验证，但不声称能够观测模型内部是否加载了某个 Skill。

## 契约和固定回答

每个 `evals/<skill-name>.behavior.json` 都是一份机器可读契约，包含：

- Skill 源码必须保留或禁止出现的正则
- 必需场景的标识、类别和调用方式
- 发送给模型的用户请求
- 最终回答必须匹配或不得匹配的正则

`evals/fixtures/<skill-name>/<case-id>.txt` 保存离线回归使用的固定回答。固定回答只证明评测执行器和断言能够处理已知输出，不证明当前模型仍会产生相同回答。

## 显式和隐式场景

每个场景通过 `invocation` 声明调用方式：

- `explicit`：提示中显式调用隔离后的 `$skill-name-working-tree-eval`
- `implicit`：提示中不注入 `$skill-name`，只提交普通用户请求

两种方式都只检查最终可见输出。`implicit` 场景可以验证无关请求没有出现 Skill 术语，但不能证明 Skill 在模型内部一定未被加载。

## 运行离线评测

使用 `--answers` 读取固定回答，不调用模型，也不需要凭据：

```sh
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
python3 scripts/run_behavior_evals.py \
  --skill mise --answers evals/fixtures/mise
```

可以列出场景或只运行一个场景：

```sh
python3 scripts/run_behavior_evals.py --skill napi-rs --list
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --case generic-binding-design
```

## 运行真实模型评测

省略 `--answers` 后，执行器使用已认证的 Codex CLI：

```sh
python3 scripts/run_behavior_evals.py --skill dsa-design
python3 scripts/run_behavior_evals.py --skill napi-rs
python3 scripts/run_behavior_evals.py --skill mise
```

真实评测会把场景提示和 Skill 内容发送给配置的 Codex 服务。结果只对应运行时使用的 CLI、模型、Skill 版本和场景断言。

## 隔离已安装的同名 Skill

真实评测先把工作树中的目标 Skill 复制到临时工作区，并改成唯一评测名称。子进程同时使用临时 `CODEX_HOME` 和 `HOME`，因此不会继承以下用户级 Skill：

- `$CODEX_HOME/skills`
- `$HOME/.agents/skills`

如果原 `CODEX_HOME` 包含 `auth.json`，执行器只把该文件复制到临时目录，并把权限设为仅当前用户可读写。临时工作区、用户目录和认证副本会在执行器退出时删除。

评测会话使用只读 sandbox 和 `--ephemeral`。这些设置减少文件副作用和会话残留，但不替代对提示、Skill 脚本和外部服务权限的审查。

## 当前覆盖的行为

`dsa-design` 覆盖：

- 纯文案请求不产生 DSA 输出
- 常规 CRUD 不强制多方案比较
- 重大 Top-K 决策比较方案，并在未获授权时等待选择
- 用户已委托选择时不因方案选择暂停

`napi-rs` 覆盖：

- 无关任务直接回答
- 通用绑定设计
- 生命周期和并发边界
- 未授权发布边界
- 官方文档覆盖检查
- 禁止项目专属术语重新进入 Skill

`mise` 覆盖：

- 无关任务直接回答
- 项目级工具、环境与 task 设计
- 未审查配置的 trust 安全边界
- 不受控拉取请求配置的 safe mode 边界
- lockfile 与 CI 的可复现性验证边界
- 官方文档路由的索引检查
- 禁止项目专属术语重新进入 Skill

这些场景是回归基线，不代表对所有提示、模型和运行环境的穷举验证。
