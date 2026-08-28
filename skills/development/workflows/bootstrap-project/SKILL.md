---
name: bootstrap-project
description: 创建或规划安全的项目脚手架与开发基线。
disable-model-invocation: true
---

# 项目初始化

在保留用户拥有的工作成果前提下，准备确定性的项目初始化计划。仅通过打包适配器，对受支持的新项目或严格识别的已有 Zig、Rust、TypeScript/Node.js、Python 和 Go 项目实施初始化。

## 执行工作流

### 1. 确定目标边界

解析绝对目标路径，并读取对它生效的全部仓库指引。只接受一种语言、一个 package 或 module，以及 library 或 CLI/application 其中一种形态。monorepo 必须指定精确子项目。将 Git 和 mise 视为宿主前置条件，不修改全局 shell 配置。

完成条件：目标、仓库边界、请求结果和适用指引均已明确。

### 2. 只读盘点

检查 manifests、源码布局、测试、lockfiles、Git 状态、CI、质量工具、构建命令、版本约束、环境管理器和 hook 系统，不修改 index。

技术栈或形态证据不完整时，读取 [stack-evidence.md](references/stack-evidence.md)。只有歧义会改变计划时才问一个简洁问题。冲突的技术栈证据或未命名的 monorepo target 均视为未解决。

完成条件：每项已发现事实均已记录或标为未知。

### 3. 确定模式、技术栈、形态与版本

缺失或有意为空的目标归类为 `new`；其他目标归类为 `existing`，并保留其源码布局。版本依次采用用户指定版本、既有约束、执行日从权威来源核查的当前稳定版本。

以下情况是阻塞冲突：

- 多个可信技术栈、packages 或 modules；
- service、Web、GUI、framework、多语言或多 package 请求；
- 需要迁移的 mise 或 Lefthook 替代方案；
- 相互矛盾的版本约束；
- 无法在不丢弃内容的情况下合并的未知配置。

完成条件：模式、技术栈、形态、版本证据和每个冲突均有明确值。

### 4. 制定改动计划

将每个相关路径恰好归类为 `create`、`merge`、`preserve` 或 `conflict`。覆盖代码骨架、脚手架 smoke test、精确版本固定、mise tasks、Lefthook、GitHub Actions、`.github/renovate.json`、README、ignore rules、EditorConfig、依赖与 lockfile 操作、Git 初始化、hook 安装和验证。

每项拟议改动记录其证据、路径、操作、命令或内容责任和验证。对不支持的质量门明确表示，而非生成一个空的成功任务。

完成条件：每一项预期写入均已归类，每个冲突都有精确的决策请求。

### 5. 路由并实施

模式、技术栈和形态确定后，完整读取且只读取一个技术栈 reference：

| 分支               | Reference                                     | 打包适配器                         |
| ------------------ | --------------------------------------------- | ---------------------------------- |
| 新 Zig             | [zig.md](references/zig.md)                   | `scripts/bootstrap_zig.py`         |
| 已有 Zig           | [zig-existing.md](references/zig-existing.md) | `scripts/baseline_existing_zig.py` |
| Rust               | [rust.md](references/rust.md)                 | `scripts/bootstrap_rust.py`        |
| TypeScript/Node.js | [node.md](references/node.md)                 | `scripts/bootstrap_node.py`        |
| Python             | [python.md](references/python.md)             | `scripts/bootstrap_python.py`      |
| Go                 | [go.md](references/go.md)                     | `scripts/bootstrap_go.py`          |

使用选定适配器及其 assets，不凭记忆重写生成文件。仅在用户要求初始化、选定 reference 接受目标、且计划不存在冲突时实施。仅规划请求或不支持形态返回 `planned`。

在首次写入或命令失败处停止。保留部分输出与适配器报告供诊断，保护用户拥有的文件和无关工作。

完成条件：适配器已返回报告，或存在受支持的原因阻止实施。

### 6. 验证并报告

选定适配器完成或跳过实施后，完整读取 [reporting.md](references/reporting.md)。将其通用结果契约与选定技术栈 reference 中的完成门结合。

完成条件：最终状态、改动、冲突、命令、验证证据、失败命令和下一步均已交代。绝不将检查或规划描述为成功初始化。
