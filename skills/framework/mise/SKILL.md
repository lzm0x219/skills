---
name: mise
description: "使用 mise 管理项目开发工具、版本、环境变量、任务、锁文件、CI 或 IDE 集成与故障排查。适用于新增或维护 mise.toml、mise.local.toml、.mise/tasks/，以及执行 mise use、install、exec、run、trust、doctor 等工作；涉及精确 CLI 参数、工具后端、settings、任务属性或版本兼容性时，先查当前 mise 官方文档。"
---

# mise 通用工作流

使用当前项目的语言、包管理器、CI 和安全约定管理开发环境；不要为了使用 mise 而迁移已有工具链、改写 shell 配置或新增全局默认值。请求与 mise、项目工具、环境变量或任务无关时，直接完成原任务，不要输出本 Skill 的流程或术语。

## 先确定边界

1. 检查现有 `mise.toml`、`mise.local.toml`、`.mise/tasks/`、`mise.lock`、语言版本文件、包管理器、CI 配置和 `.gitignore`。不要假定某个仓库、工具版本、shell、CI 平台、密钥来源或本地配置文件存在。
2. 先明确要解决的问题：仅一次性运行、项目级可复现环境、个人全局默认、交互式 shell、CI/IDE，还是任务编排。优先项目级的、可审查的配置；只有用户明确要求时才修改全局配置或 shell rc 文件。
3. 变更前确认配置作用域、支持的平台、工具来源与版本策略，以及 `mise.lock` 是否应随项目提交。不要把本机已安装版本误当成团队的兼容承诺。

## 使用当前官方文档

1. 先阅读[官方文档任务路由](references/official-documentation-inventory.md)，再打开与当前工作直接相关的官方页面。
2. 涉及精确 CLI 参数、工具后端、settings、任务属性或版本兼容性时，始终以当前官方页面为准；不要从本 Skill 推断精确参数、默认值或支持矩阵。
3. 仅在刷新路由清单或声称本地链接仍有效时，在本 Skill 目录运行 `node scripts/verify-official-docs-inventory.mjs --check`；发布或刷新前再加 `--verify-links`。在此仓库根目录运行时，使用 `node skills/framework/mise/scripts/verify-official-docs-inventory.mjs --check`。

| 工作内容 | 优先查阅的官方主题 |
| --- | --- |
| 安装、激活、shell、IDE 或 CI | Getting Started、Installing mise、Shims、IDE Integration、Continuous Integration、`mise activate`、`mise doctor` |
| 项目配置、配置层级与环境切换 | `mise.toml`、Settings、Configuration Environments |
| 工具版本、后端、锁定与供应链风险 | Dev Tools、Backends、Registry、`mise.lock`、Security、`mise use`、`mise install`、`mise exec` |
| 环境变量、secret、hook 或 direnv | Environment Variables、Secrets、Hooks、direnv、`mise trust` |
| 构建、测试、lint、脚本与 monorepo 任务 | Task Overview、Task Architecture、TOML/File Tasks、Task Arguments、Task Configuration、Monorepo Tasks、`mise run`、`mise tasks validate` |

按实际触及的能力组合阅读页面。例如，为 monorepo 添加带环境变量的 CI task 时，同时阅读配置、环境、任务、锁文件与 CI 页面。

## 配置与安全边界

- 将团队需要的工具版本、任务和非敏感环境规则放在项目配置中；个人路径、机器专属设置和明文凭据不要悄悄写入可提交文件。
- 将 `mise.toml`、环境指令、模板、hook 与 task 视为可执行边界。先审查来自他人的配置及其引用文件；没有用户的明确授权，不运行 `mise trust`、不信任未知配置，也不关闭或放宽信任限制。
- 不要依赖“检测到 CI”便自动信任配置。对拉取请求分支或自动化机器人等不受控配置，只在当前官方 Security/CI 页面允许的范围内以 `MISE_SAFE=1` 解析版本或更新 lockfile；safe mode 会禁用项目环境、hook、task、模板执行与部分插件操作，不能替代经过审查的普通 CI 信任策略。
- 不在回答、日志、任务定义、提交记录或 fixture 中输出 secret。需要 secret 时，按当前官方 Secrets 指引确认安全来源和注入方式，并验证缺失 secret 时的可操作报错。
- 不把 `mise self-update`、全局 `mise use`、全局 settings、shell rc 改动、生成或改写 CI 文件、下载/安装不受信任工具、发布或部署当作无副作用操作。没有用户的明确授权，不运行它们。
- 选择工具后端、版本范围、lockfile 和 checksum 策略时，遵循项目现有供应链策略；不要仅因某后端可用就替换已批准来源。

## 实施与验证

1. 以最小变更维护配置：工具放入 `[tools]`，环境和任务只表达项目已经需要的行为。任务应有清晰名称、输入、依赖、工作目录、失败语义和可复现的输出；不要把交互式本地步骤伪装成无提示的 CI 任务。
2. 在用户授权的范围内安装或同步工具，并用当前官方页面确认命令。随后通过 `mise exec` 或 `mise run` 执行实际项目命令；不要只因配置文件存在或 `mise install` 成功就声称工具链可用。
3. 若项目采用 lockfile，生成或更新它后检查 diff、目标平台和是否应提交。锁文件能固定当时解析的版本与校验信息，但不能替代实际下载、运行或跨平台测试。
4. 为任务运行当前项目的构建、测试或 lint；再运行 `mise tasks validate`（若该能力和当前版本适用）。对环境问题，比较 `mise env` 输出与期望进程环境，并避免打印敏感值。
5. 只有在实际 shell、IDE、CI 或目标平台中运行验证后，才声称对应集成生效。`mise activate`、shims 与 `mise exec` 的适用边界不同；未运行的环境保持为未验证。

## 诊断顺序

1. 先确认正在读取哪个配置、作用域和可信状态，再检查当前 mise 版本与 shell/CI 入口。
2. 用官方当前的 `mise doctor`、配置/工具/任务查看命令定位问题层级：配置发现、trust、工具解析与安装、环境导出、task 定义，或宿主 shell/IDE/CI。
3. 用最小命令在 mise 上下文中重现，再检查实际工具版本、PATH、环境变量与 task 的退出状态。修复后重跑原始项目命令，不要只验证诊断命令本身。

## 本地资源

- [官方文档任务路由](references/official-documentation-inventory.md)：官方 `llms.txt`、sitemap 与当前任务主题的可审计入口；不是 CLI API 的离线副本。
- [官方文档清单验证器](scripts/verify-official-docs-inventory.mjs)：检查本地路由中的官方页面是否仍被当前官方索引收录，并可验证链接可达性。
