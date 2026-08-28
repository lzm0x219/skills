---
name: mise
description: 使用 mise 管理项目开发工具、版本、环境变量、任务、锁文件、CI 或 IDE 集成及故障排查。适用于新增或维护 mise.toml、mise.local.toml、.mise/tasks/，以及运行 mise use、install、exec、run、trust、doctor 等相关操作。涉及精确 CLI 参数、工具后端、设置、任务属性或版本兼容性时，先查阅当前 mise 官方文档。
---

# mise 通用工作流

按照当前项目的语言、包管理器、CI 与安全约定管理开发环境。不要仅为使用 mise 而迁移既有工具链、重写 shell 配置或增加全局默认值。若请求与 mise、项目工具、环境变量或任务无关，直接完成原任务，不输出本 Skill 的流程或术语。

## 先确定边界

1. 检查既有的 `mise.toml`、`mise.local.toml`、`.mise/tasks/`、`mise.lock`、语言版本文件、包管理器、CI 配置与 `.gitignore`。不要假定存在特定仓库、工具版本、shell、CI 平台、密钥来源或本地配置文件。
2. 先界定要解决的问题：一次性执行、项目级可复现环境、个人全局默认值、交互式 shell、CI／IDE 或任务编排。优先选择可审阅的项目级配置；仅在用户明确要求时修改全局配置或 shell rc 文件。
3. 修改前确认配置范围、支持平台、工具来源和版本策略，以及是否应随项目提交 `mise.lock`。不要把本机已安装的版本视为团队兼容性承诺。

## 使用当前官方文档

1. 先阅读 [官方文档任务路由](references/official-documentation-inventory.md)，再打开与当前工作直接相关的官方页面。
2. 当精确 CLI 参数、工具后端、设置、任务属性或版本兼容性重要时，始终以当前官方页面为准。不要从本 Skill 推断精确参数、默认值或支持矩阵。
3. 只有在刷新路由清单或声称本地链接仍有效时，才在本 Skill 目录运行 `node scripts/verify-official-docs-inventory.mjs --check`；发布前或刷新后再加 `--verify-links`。从仓库根目录运行时使用 `node skills/development/tools/mise/scripts/verify-official-docs-inventory.mjs --check`。

| 工作                                   | 优先查阅的官方主题                                                                                                                       |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 安装、激活、shell、IDE 或 CI           | Getting Started、Installing mise、Shims、IDE Integration、Continuous Integration、`mise activate`、`mise doctor`                         |
| 项目配置、配置层、环境切换             | `mise.toml`、Settings、Configuration Environments                                                                                        |
| 工具版本、后端、锁定与供应链风险       | Dev Tools、Backends、Registry、`mise.lock`、Security、`mise use`、`mise install`、`mise exec`                                            |
| 环境变量、密钥、hooks 或 direnv        | Environment Variables、Secrets、Hooks、direnv、`mise trust`                                                                              |
| 构建、测试、lint、脚本与 monorepo 任务 | Task Overview、Task Architecture、TOML/File Tasks、Task Arguments、Task Configuration、Monorepo Tasks、`mise run`、`mise tasks validate` |

只读取实际触及能力对应的页面。例如，为 monorepo 增加带环境变量的 CI 任务时，还要读取配置、环境、任务、锁文件和 CI 页面。

## 配置与安全边界

- 团队工具版本、任务与非敏感环境规则写入项目配置。不要把个人路径、机器专属设置或明文凭据悄悄写进可提交文件。
- 将 `mise.toml`、环境指令、模板、hooks 与任务视为可执行边界。先审查他人提供的配置及其引用文件；未经用户明确授权，不运行 `mise trust`、不信任未知配置，也不放松信任限制。
- 不依赖「检测到 CI」自动信任配置。对于 PR 分支或自动化 bot 等不受控配置，只能在当前官方 Security／CI 页面允许的范围内，以 `MISE_SAFE=1` 解析版本或更新锁文件。安全模式会禁用项目环境、hooks、任务、模板执行及部分插件操作，不能替代经过审查的常规 CI 信任策略。
- 不在回答、日志、任务定义、提交或 fixture 中输出密钥。需要密钥时，先按当前官方 Secrets 指引确认安全来源和注入方式，并验证缺失密钥时的可执行报错。
- 不把 `mise self-update`、全局 `mise use`、全局设置、shell rc 修改、生成或重写 CI 文件、下载／安装不受信任工具、发布或部署视为无副作用操作。未经用户明确授权不得执行。
- 选择工具后端、版本范围、锁文件和校验和策略时遵循项目既有供应链策略。不要只因另一个后端可用就替换已批准来源。

## 实施与验证

1. 最小化修改配置：将工具放入 `[tools]`，只表达项目确实需要的环境和任务行为。任务应有清晰名称、输入、依赖、工作目录、失败语义和可复现输出；不要把交互式本地步骤伪装成无人值守 CI 任务。
2. 只在已授权范围内安装或同步工具，并以当前官方页面确认命令。随后通过 `mise exec` 或 `mise run` 执行真实项目命令；不能只因存在配置文件或 `mise install` 成功就声称工具链可用。
3. 项目使用锁文件时，生成或更新后审查 diff、目标平台和提交策略。锁文件能固定当时已解析的版本和校验数据，但不能替代实际下载、运行或跨平台测试。
4. 为任务运行当前项目的构建、测试或 lint；当功能与当前版本适用时，再运行 `mise tasks validate`。处理环境问题时，将 `mise env` 输出与预期进程环境比较，不打印敏感值。
5. 只有在真实环境中验证后，才声称 shell、IDE、CI 或目标平台集成可用。`mise activate`、shims 和 `mise exec` 适用边界不同；未运行的环境保持为未验证。

## 诊断顺序

1. 先确认读取的是哪份配置、其范围和信任状态，再检查当前 mise 版本与 shell／CI 入口。
2. 使用当前官方 `mise doctor` 以及配置、工具、任务检查命令定位问题层级：配置发现、信任、工具解析与安装、环境导出、任务定义，或宿主 shell／IDE／CI。
3. 在 mise 上下文中用最小命令复现，再检查实际工具版本、PATH、环境变量与任务退出状态。修复后重跑原项目命令；不能只验证诊断命令本身。

## 本地资源

- [官方文档任务路由](references/official-documentation-inventory.md)：来自官方 `llms.txt`、sitemap 与当前任务主题的可审计入口，不是离线 CLI API 副本。
- [官方文档清单验证器](scripts/verify-official-docs-inventory.mjs)：检查本地路由中的官方页面是否仍在当前官方索引中，也可验证链接可达性。
