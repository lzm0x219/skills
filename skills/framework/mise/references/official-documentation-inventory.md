# mise 官方文档任务路由清单

> 检索快照：2026-07-29（Asia/Shanghai）。此文件是任务路由和链接完整性检查用的官方页面目录，不是 mise CLI API 的离线副本；实现时仍须打开涉及能力的官方页面确认当前版本细节。

## 权威入口与使用边界

- 官方机器可读目录：[llms.txt](https://mise.jdx.dev/llms.txt)；它按 Guides、Configuration、Dev Tools、Environments、Tasks、Plugins、Advanced 与 CLI Reference 列出当前文档入口。
- 官方站点索引：[sitemap.xml](https://mise.jdx.dev/sitemap.xml)。它与 `llms.txt` 一起用于发现页面移动、删除或新增。
- 本目录选择日常项目配置所需的主题页，而非宣称完整复制官网。精确命令、settings、后端、模板、平台支持和安全行为均应以运行时页面为准。
- 在本 Skill 目录运行 `node scripts/verify-official-docs-inventory.mjs --check` 会验证本目录中的主题 URL 仍出现在当前官方 `llms.txt` 或 sitemap；在本仓库根目录运行时，使用 `node skills/framework/mise/scripts/verify-official-docs-inventory.mjs --check`。`--verify-links` 另行请求每个记录页。检查通过只证明链接与索引状态，不证明某项配置在任意机器、shell、IDE、CI 或工具后端可用。

## 1. 安装、激活、IDE 与 CI

这些页面用于决定安装方式、交互 shell 与非交互环境的加载策略；不要把某个平台的安装步骤、PATH 或 shell hook 写死到通用配置。

- [Getting Started](https://mise.jdx.dev/getting-started.html) — 安装、一次性执行、工具、任务、trust 与环境变量的总览。
- [Installing mise](https://mise.jdx.dev/installing-mise.html) — 按操作系统和包管理器选择安装方式。
- [Shims](https://mise.jdx.dev/dev-tools/shims.html) — 比较 shell activation、shims 与不同运行环境的能力边界。
- [IDE Integration](https://mise.jdx.dev/ide-integration.html) — 在 IDE 中加载 mise 工具和环境的方式。
- [Continuous Integration](https://mise.jdx.dev/continuous-integration.html) — 在 CI 中提供项目所需工具的配置方式；对不受控的拉取请求配置，按当前页面以 `MISE_SAFE=1` 限制配置执行。
- [`mise activate`](https://mise.jdx.dev/cli/activate.html) — 初始化当前 shell session。
- [`mise doctor`](https://mise.jdx.dev/cli/doctor.html) — 检查安装和常见配置问题。

## 2. 配置、环境与可信边界

这些页面决定项目配置的发现、层级、环境注入和潜在代码执行范围。涉及来源不明的配置、hook、模板或 secret 时，先审查再 trust。

- [`mise.toml`](https://mise.jdx.dev/configuration.html) — 配置文件、工具、环境与其他项目级选项。
- [Settings](https://mise.jdx.dev/configuration/settings.html) — settings 的当前键、作用域和设置入口。
- [Configuration Environments](https://mise.jdx.dev/configuration/environments.html) — 同一目录中不同环境配置的组织方式。
- [Environment Variables](https://mise.jdx.dev/environments/) — 随项目目录加载和导出环境变量。
- [Secrets](https://mise.jdx.dev/environments/secrets/) — 敏感环境变量的受支持做法和边界。
- [Hooks](https://mise.jdx.dev/hooks.html) — activate session 期间的 hook 与其执行前提。
- [direnv](https://mise.jdx.dev/direnv.html) — 与 direnv 同用时的环境管理边界。
- [`mise trust`](https://mise.jdx.dev/cli/trust.html) — 信任配置文件的当前行为与作用域。
- [`mise env`](https://mise.jdx.dev/cli/env.html) — 一次性导出 mise 环境变量。

## 3. 工具、后端、锁定与供应链

工具来源、版本解析、lockfile 与验证信息都是时效性事实。选择或升级后端、改变 lockfile 策略、跨平台支持或处理 GitHub 限流时，打开本组对应页面。

- [Dev Tools Overview](https://mise.jdx.dev/dev-tools/) — 项目工具安装、版本切换和自动激活的概览。
- [Backends](https://mise.jdx.dev/dev-tools/backends/) — 可提供工具的包生态/后端及其安装边界。
- [Registry](https://mise.jdx.dev/registry.html) — 默认工具别名的当前注册表。
- [`mise.lock` Lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html) — lockfile 的生成、精确版本、checksum 与可复现性边界。
- [Security](https://mise.jdx.dev/security.html) — 不同后端可获得的供应链控制与覆盖限制，以及以 `MISE_SAFE=1` 对不受控项目配置建立代码执行边界。
- [`mise use`](https://mise.jdx.dev/cli/use.html) — 安装工具并写入 `mise.toml`。
- [`mise install`](https://mise.jdx.dev/cli/install.html) — 安装指定工具版本。
- [`mise exec`](https://mise.jdx.dev/cli/exec.html) — 在指定工具上下文执行命令。
- [`mise ls`](https://mise.jdx.dev/cli/ls.html) — 查看已安装和已激活的工具版本。
- [`mise lock`](https://mise.jdx.dev/cli/lock.html) — 为指定平台更新 lockfile 的 URL 和 checksum。

## 4. 任务、任务文件与 monorepo

任务是项目执行接口而非简单命令别名。修改任务时一并审查依赖、参数、工作目录、环境、退出语义和 CI 可执行性。

- [Task Overview](https://mise.jdx.dev/tasks/) — 定义和运行项目 build、test、lint、deploy 等 task。
- [Task Architecture](https://mise.jdx.dev/tasks/architecture.html) — task 的发现、依赖与运行模型。
- [Running Tasks](https://mise.jdx.dev/tasks/running-tasks.html) — 列出、选择和运行 task。
- [TOML Tasks](https://mise.jdx.dev/tasks/toml-tasks.html) — 在 `mise.toml` 中定义简单和详细 task。
- [File Tasks](https://mise.jdx.dev/tasks/file-tasks.html) — 用独立脚本文件定义 task 的目录和约定。
- [Task Arguments](https://mise.jdx.dev/tasks/task-arguments.html) — task 参数的支持形式和推荐方式。
- [Task Configuration](https://mise.jdx.dev/tasks/task-configuration.html) — task 的完整配置属性。
- [Task Templates](https://mise.jdx.dev/tasks/templates.html) — 复用 task 定义与模板。
- [Monorepo Tasks](https://mise.jdx.dev/tasks/monorepo.html) — 跨项目/目标路径的 task 组织。
- [Sandboxing](https://mise.jdx.dev/sandboxing.html) — 对 `mise exec` 和 `mise run` 的进程隔离控制。
- [`mise run`](https://mise.jdx.dev/cli/run.html) — 运行一个或多个 task。
- [`mise tasks validate`](https://mise.jdx.dev/cli/tasks/validate.html) — 检查 task 的常见错误和问题。

## 刷新规则

- 当 `--check` 报告缺失 URL、官方新增主题，或一个任务需要此目录没有覆盖的能力时，从官方 `llms.txt` 和 sitemap 重新发现页面；保留 canonical HTTPS URL，按上面的任务路由补充，而不是把整站复制进 Skill。
- 版本变更、迁移、插件开发、bootstrap、OCI、MCP、package plugins、templates、specific backend 或平台兼容性属于按需打开的官方页面；本目录没有覆盖它们不表示这些能力不存在。
- 不要把本目录或成功的链接检查当作配置可运行、secret 安全、供应链可信或多平台兼容的证据；这些结论仍需要相应环境中的实际验证。
