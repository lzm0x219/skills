# mise 官方文档任务路由清单

> 快照：2026-07-29（Asia/Shanghai）。本文件用于任务路由与链接完整性检查，不是 mise CLI API 的离线副本。实施时仍需打开涉及能力的官方页面，确认当前版本细节。

## 权威入口与使用边界

- 官方机器可读目录：[llms.txt](https://mise.jdx.dev/llms.txt)。它列出 Guides、Configuration、Dev Tools、Environments、Tasks、Plugins、Advanced 和 CLI Reference 下的当前文档入口。
- 官方站点索引：[sitemap.xml](https://mise.jdx.dev/sitemap.xml)。它与 `llms.txt` 一起用于发现移动、删除或新增的页面。
- 本清单仅选择日常项目配置所需的主题页，不声称复制整个官方站点。精确命令、设置、后端、模板、平台支持和安全行为仍应来自实时页面。
- 在本 Skill 目录运行 `node scripts/verify-official-docs-inventory.mjs --check`，可验证本清单主题 URL 是否仍出现在当前官方 `llms.txt` 或 sitemap 中。从仓库根目录运行时使用 `node skills/development/tools/mise/scripts/verify-official-docs-inventory.mjs --check`。`--verify-links` 会额外请求每个记录页面。检查通过只证明链接与索引状态，不能证明任何机器、shell、IDE、CI 或工具后端上的配置可用。

## 1. 安装、激活、IDE 与 CI

用本组页面决定交互式 shell 与非交互环境的安装和加载策略。不要把某个平台的安装步骤、PATH 或 shell hook 写死到通用配置中。

- [Getting Started](https://mise.jdx.dev/getting-started.html) — 安装、一次性执行、工具、任务、信任与环境变量概览。
- [Installing mise](https://mise.jdx.dev/installing-mise.html) — 按操作系统和包管理器选择安装方式。
- [Shims](https://mise.jdx.dev/dev-tools/shims.html) — 比较 shell 激活、shims 及不同运行环境的能力边界。
- [IDE Integration](https://mise.jdx.dev/ide-integration.html) — 在 IDE 中加载 mise 工具与环境的方法。
- [Continuous Integration](https://mise.jdx.dev/continuous-integration.html) — 在 CI 中提供项目工具；对不受控 PR 配置，遵循当前页面并以 `MISE_SAFE=1` 限制执行。
- [`mise activate`](https://mise.jdx.dev/cli/activate.html) — 初始化当前 shell 会话。
- [`mise doctor`](https://mise.jdx.dev/cli/doctor.html) — 检查安装与常见配置问题。

## 2. 配置、环境与信任边界

这些页面决定项目配置发现、分层、环境注入及可能的代码执行范围。配置、hooks、模板或密钥来源不清楚时，先审查再信任。

- [`mise.toml`](https://mise.jdx.dev/configuration.html) — 配置文件、工具、环境及其他项目级选项。
- [Settings](https://mise.jdx.dev/configuration/settings.html) — 当前设置键、作用域和入口。
- [Configuration Environments](https://mise.jdx.dev/configuration/environments.html) — 在同一目录中组织不同环境配置的方法。
- [Environment Variables](https://mise.jdx.dev/environments/) — 在项目目录中加载并导出环境变量。
- [Secrets](https://mise.jdx.dev/environments/secrets/) — 敏感环境变量的支持方式与边界。
- [Hooks](https://mise.jdx.dev/hooks.html) — 激活会话期间的 hooks 及其执行前提。
- [direnv](https://mise.jdx.dev/direnv.html) — 与 direnv 联用时的环境管理边界。
- [`mise trust`](https://mise.jdx.dev/cli/trust.html) — 信任配置文件的当前行为与范围。
- [`mise env`](https://mise.jdx.dev/cli/env.html) — 为一次性使用导出 mise 环境变量。

## 3. 工具、后端、锁定与供应链

工具来源、版本解析、锁文件和验证数据都具有时效性。选择或升级后端、改变锁文件策略、支持多平台或处理 GitHub 限流时，打开本组对应页面。

- [Dev Tools Overview](https://mise.jdx.dev/dev-tools/) — 安装项目工具、切换版本与自动激活概览。
- [Backends](https://mise.jdx.dev/dev-tools/backends/) — 可提供工具的包生态／后端及其安装边界。
- [Registry](https://mise.jdx.dev/registry.html) — 默认工具别名的当前注册表。
- [`mise.lock` Lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html) — 锁文件生成、精确版本、校验和与可复现性边界。
- [Security](https://mise.jdx.dev/security.html) — 不同后端可用的供应链控制及覆盖范围；以及用 `MISE_SAFE=1` 限制不受控项目配置执行。
- [`mise use`](https://mise.jdx.dev/cli/use.html) — 安装工具并写入 `mise.toml`。
- [`mise install`](https://mise.jdx.dev/cli/install.html) — 安装指定工具版本。
- [`mise exec`](https://mise.jdx.dev/cli/exec.html) — 在指定工具上下文中运行命令。
- [`mise ls`](https://mise.jdx.dev/cli/ls.html) — 列出已安装与已激活的工具版本。
- [`mise lock`](https://mise.jdx.dev/cli/lock.html) — 更新指定平台的锁文件 URL 和校验和。

## 4. 任务、任务文件与 monorepo

任务是项目执行接口，而不仅是命令别名。修改任务时也要检查依赖、参数、工作目录、环境、退出语义与 CI 可执行性。

- [Task Overview](https://mise.jdx.dev/tasks/) — 定义并运行项目构建、测试、lint、部署等任务。
- [Task Architecture](https://mise.jdx.dev/tasks/architecture.html) — 发现、依赖与执行模型。
- [Running Tasks](https://mise.jdx.dev/tasks/running-tasks.html) — 列出、选择与运行任务。
- [TOML Tasks](https://mise.jdx.dev/tasks/toml-tasks.html) — 在 `mise.toml` 中定义简单或详细任务。
- [File Tasks](https://mise.jdx.dev/tasks/file-tasks.html) — 将独立脚本定义为任务的目录与约定。
- [Task Arguments](https://mise.jdx.dev/tasks/task-arguments.html) — 支持的任务参数形式与推荐传递方式。
- [Task Configuration](https://mise.jdx.dev/tasks/task-configuration.html) — 完整任务配置属性。
- [Task Templates](https://mise.jdx.dev/tasks/templates.html) — 复用任务定义与模板。
- [Monorepo Tasks](https://mise.jdx.dev/tasks/monorepo.html) — 跨项目／目标路径组织任务。
- [Sandboxing](https://mise.jdx.dev/sandboxing.html) — `mise exec` 与 `mise run` 的进程隔离控制。
- [`mise run`](https://mise.jdx.dev/cli/run.html) — 运行一个或多个任务。
- [`mise tasks validate`](https://mise.jdx.dev/cli/tasks/validate.html) — 检查任务中的常见错误与问题。

## 刷新规则

- 当 `--check` 报告缺失 URL、官方站点新增主题，或任务需要本清单未覆盖的能力时，从官方 `llms.txt` 和 sitemap 重新发现页面。保留规范 HTTPS URL，并按上述任务路由扩展，而非复制整个站点。
- 版本变更、迁移、插件开发、bootstrap、OCI、MCP、package plugins、模板、特定后端或平台兼容性等情况，应按需打开官方页面。本清单未列出不代表该能力不存在。
- 不把本清单或链接检查通过视为配置可运行、密钥安全、供应链可信或多平台支持的证据；这些结论仍需在相关环境中实际验证。
