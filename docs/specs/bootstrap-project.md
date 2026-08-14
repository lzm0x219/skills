# bootstrap-project 规格

## Problem Statement

新建项目和既有项目经常缺少一致、可验证的开发基线：运行时与工具版本未固定，本地命令与 CI 分叉，提交钩子过重或会扩大暂存范围，依赖更新配置缺失，代码骨架也可能与真实技术栈不匹配。通用脚手架容易覆盖已有约定，或把某一生态的工具强加到其他技术栈。

需要一个仅由用户手动触发的 `bootstrap-project` Skill。它应在明确目标目录、技术栈和项目形态后，创建最小代码骨架或补齐既有项目基线，同时保护用户文件、报告冲突，并用真实命令验证结果。

## Solution

实现一个 portable Composite Skill，支持 Zig、Rust、TypeScript/Node.js、Python 和 Go 的单语言、单包或单模块项目。Skill 分为“新项目”和“既有项目”两种模式，统一生成或补齐 `mise`、Lefthook、GitHub Actions、Renovate、编辑器与忽略规则，并按技术栈创建最小可构建、可测试的库或 CLI/application 骨架。

Skill 采用先盘点、再计划、后写入、最后验证的事务式流程。所有版本和命令都必须有可追溯来源；遇到工具迁移、文件覆盖、技术栈歧义、monorepo 边界或无法安全处理的暂存状态时，暂停并请求用户确认。

## User Stories

1. 作为用户，我可以显式调用 `$bootstrap-project`，避免模型在普通编码任务中自动初始化或改造项目。
2. 作为用户，我可以指定新目录并选择技术栈与项目形态，得到最小、真实可运行的代码骨架。
3. 作为用户，我可以对既有仓库运行 Skill，只补齐缺失的开发基线而不重建业务代码。
4. 作为用户，我可以选择 Zig、Rust、TypeScript/Node.js、Python 或 Go。
5. 作为用户，我可以选择 library 或 CLI/application；v1 不要求先理解 Web、GUI 或服务框架。
6. 作为用户，在未明确技术栈时，Skill 会优先读取可信项目清单和源码证据。
7. 作为用户，当证据指向多个技术栈或项目边界不清时，我会先收到澄清问题。
8. 作为用户，在 monorepo 中必须指定目标子项目，避免全仓误写。
9. 作为用户，我可以显式指定版本；该版本优先于仓库约束和当前稳定版本。
10. 作为用户，若仓库已有明确版本约束，Skill 会复用它并检查跨文件一致性。
11. 作为用户，若没有版本约束，Skill 会从权威来源选择执行时的当前稳定版本并精确固定。
12. 作为用户，我会看到计划写入、修改、保留和冲突的文件清单，再发生高风险变更。
13. 作为用户，已有文件默认被保留；Skill 不会静默覆盖未知内容。
14. 作为用户，若仓库已有 asdf、Volta、Husky、pre-commit 等替代方案，Skill 会先询问是否迁移到 `mise` 或 Lefthook。
15. 作为用户，新仓库在没有 Git 元数据时会执行 `git init`，但不会创建初始提交。
16. 作为用户，新项目优先使用官方 initializer，并清理与目标形态无关的示例代码。
17. 作为用户，当官方 initializer 不足以表达 library 或 CLI/application 时，Skill 会补充最小模板。
18. 作为用户，每个新骨架至少包含一个非领域化 smoke test，用来证明测试入口实际执行了测试。
19. 作为用户，既有项目不会为了统一目录结构而移动源码或重命名模块。
20. 作为用户，我会得到精确固定的 `mise` 运行时和项目工具，并可通过项目内任务运行全部质量检查。
21. 作为用户，我可以统一运行 `mise run format`、`format-check`、`lint`、`check`、`test`、`build` 和 `ci`。
22. 作为用户，不适用的任务不会用成功的空命令伪装；任务必须有真实语义或明确报告不支持。
23. 作为用户，Lefthook 的 pre-commit 会先检测同一文件同时存在 staged 与 unstaged 修改的情况。
24. 作为用户，遇到部分暂存文件时，hook 会停止并给出处理方法，不会扩大提交范围。
25. 作为用户，pre-commit 只格式化匹配的 staged 文件，并重新暂存格式化结果。
26. 作为用户，pre-commit 随后执行 staged lint 和项目级快速 type/compile check。
27. 作为用户，完整测试与构建不会进入 pre-commit，以保持提交反馈快速。
28. 作为用户，格式化写入与只读检查不会被并行执行，从而避免时序竞争。
29. 作为用户，CI 在 Ubuntu 上安装与本地相同的精确工具链，并只调用 `mise run ci`。
30. 作为用户，GitHub Actions action 版本以 commit SHA 固定，并交给 Renovate 更新。
31. 作为用户，项目会获得 `.github/renovate.json`，扩展 `config:recommended`，启用 semantic commits，并为更新 PR 添加 `dependencies` 标签。
32. 作为用户，Renovate 不会默认 auto-approve、automerge、添加仓库 schedule 或启用 lockfile maintenance。
33. 作为用户，Skill 不会安装或授权 Renovate GitHub App，只生成仓库配置。
34. 作为用户，新项目会获得最小 `README.md`、`.gitignore` 和 `.editorconfig`。
35. 作为用户，许可证、贡献指南和发布流程只在我明确要求时生成。
36. 作为 TypeScript/Node.js 用户，我会获得 Node LTS、pnpm、ESM、strict TypeScript、oxfmt、oxlint、`tsc --noEmit` 和 Vitest。
37. 作为 TypeScript/Node.js 用户，我不会被加入 Prettier、ESLint、typescript-eslint 或 `node:test`。
38. 作为 Python 用户，我会获得 uv、Ruff、mypy 和 pytest，并通过 `uv run` 执行项目命令。
39. 作为 Rust 用户，我会获得 rustfmt、Clippy、check、test 和 build 基线。
40. 作为 Zig 用户，我会获得 `zig fmt`、build 和真实执行测试的基线。
41. 作为 Go 用户，我会获得 gofmt、vet、test 和 build 基线。
42. 作为用户，依赖安装和锁文件生成属于初始化结果，并在失败时得到明确状态。
43. 作为用户，Lefthook 安装完成后，Skill 会验证 hook 入口已生效。
44. 作为用户，验证失败不会被描述为成功；报告会区分 completed、partial 和 blocked。
45. 作为用户，当网络、权限或工具不可用时，我会得到已完成内容、失败命令和可重复的后续步骤。
46. 作为用户，Skill 不会修改全局 shell 配置；Git 与 mise 是显式主机前置条件。
47. 作为用户，我可以在 macOS 和 Linux 上使用 v1，并清楚知道 Windows 不在保证范围内。
48. 作为维护者，我可以通过离线 fixtures 验证生成计划和文件内容，而不依赖实时网络。
49. 作为维护者，我可以用真实工具链 smoke tests 验证生成项目能格式化、检查、测试和构建。
50. 作为维护者，我可以用一个 Ziwei 风格的既有 Zig fixture 验证增量补齐、版本一致性和 hook 顺序修复。

## Implementation Decisions

1. **调用与定位**：`bootstrap-project` 是 Composite Skill，必须手动触发。`SKILL.md` frontmatter 设置 `disable-model-invocation: true`；`agents/openai.yaml` 设置 `policy.allow_implicit_invocation: false`。仓库 validator 同步允许并校验这两个字段的一致性。
2. **输入契约**：必需输入为目标目录；技术栈、模式、项目形态和版本可由用户提供。仅当既有仓库证据唯一且可信时才推断技术栈。monorepo 必须提供子项目边界。
3. **执行阶段**：固定为 inventory、resolve、plan、apply、verify、report。前三阶段只读；`apply` 前形成确定的文件操作计划；`verify` 不得掩盖写入或命令失败。
4. **冲突模型**：文件分为 create、merge、preserve、conflict。已存在且可结构化合并的配置才能 merge；未知内容、工具迁移和破坏性变更进入 conflict，并等待确认。
5. **版本模型**：优先级为用户指定、既有约束、权威来源的当前稳定版本。写入精确版本，同时保证语言清单、`mise.toml`、包管理器和 CI 一致。
6. **代码骨架**：优先调用官方 initializer；模板只补充官方工具未覆盖的最小文件。移除生成器演示内容时必须按已知清单删除，不使用宽泛递归清理。
7. **项目范围**：v1 只支持单语言、单 package/module 的 library 与 CLI/application。服务、Web、GUI 和多包 monorepo 需要后续 capability。
8. **通用文件**：按需创建或合并 `README.md`、`.gitignore`、`.editorconfig`、`mise.toml`、`lefthook.yml`、`.github/workflows/validate.yml` 和 `.github/renovate.json`。
9. **mise 任务契约**：所有支持栈暴露 `format`、`format-check`、`lint`、`check`、`test`、`build`、`ci`。`ci` 只组合只读质量门；不能依赖前序写入型 `format`。
10. **Lefthook 顺序**：pre-commit 顺序为 partial-stage guard、staged formatter、restage、staged lint、project quick check。会修改文件的步骤不与读取工作树的步骤并行。完整 `test` 和 `build` 留给开发命令及 CI。
11. **TypeScript/Node.js baseline**：Node LTS + pnpm + ESM + strict TypeScript；oxfmt 负责格式化，oxlint 负责 lint，稳定 `tsc --noEmit` 负责类型检查，Vitest 负责测试。使用 pnpm lockfile，不加入被排除的旧工具链。
12. **Python baseline**：uv 管理项目、Python 与锁文件；Ruff 同时承担格式和 lint；mypy 类型检查；pytest 测试。项目任务使用 `uv run`，CI 使用锁定同步语义。
13. **Rust baseline**：Cargo 官方初始化；rustfmt 格式检查；Clippy lint；`cargo check`、`cargo test`、`cargo build` 分别对应检查、测试和构建。
14. **Zig baseline**：以 `build.zig.zon` 和 `build.zig` 作为核心清单；`zig fmt --check`、`zig build` 与实际运行测试的 build step 构成质量门。不默认引入无法确认与目标 Zig 版本兼容的第三方 linter。
15. **Go baseline**：`go mod init` 与最小 package/command；gofmt 格式；`go vet` lint；`go test ./...` 测试；`go build ./...` 构建。
16. **CI baseline**：仅 Ubuntu 与单一默认版本，不生成 OS 或版本矩阵。workflow 安装 mise，恢复安全缓存后调用 `mise run ci`；所有第三方 actions 使用完整 commit SHA。
17. **Renovate baseline**：`.github/renovate.json` 扩展 `config:recommended`，设置 semantic commits 和 `dependencies` label，并覆盖 mise、Cargo、npm/pnpm、PEP 621/uv、Go modules 与 GitHub Actions 的可识别清单。不启用自动合并、自动批准、schedule 或 lockfile maintenance。
18. **副作用边界**：允许在目标目录内创建文件、安装项目依赖、生成锁文件、初始化 Git 和安装本地 hooks。禁止创建 commit、push、PR、修改全局 shell 或授权外部 App。
19. **结果模型**：报告包含 mode、stack、shape、versions、created、modified、preserved、conflicts、commands、verification 和 status。`partial` 必须附恢复或重试步骤；`blocked` 不得留下未经说明的半配置状态。
20. **能力注册**：只为这一已确认 Composite 增加最小 `capabilities/map.json` 项，记录手动调用、输入、写入能力和安全边界；不批量预注册尚未实现的初始化器。

## Testing Decisions

1. **最高测试缝**：在临时目标 workspace 中显式运行 `$bootstrap-project`，随后检查文件树、配置内容、命令记录与验证结果。这是 workspace mutation 的主要验收面。
2. **runner 扩展**：现有只读 final-answer behavior runner 不足以证明写入行为。新增隔离的 fixture runner，复制输入仓库到临时目录，允许仅在该目录写入，并捕获 before/after manifest、diff、stdout、stderr 和 exit status。
3. **静态调用测试**：validator 必须验证 `disable-model-invocation: true`、`allow_implicit_invocation: false` 及其一致性；行为场景还要证明未显式调用时不会初始化项目。
4. **新项目矩阵**：五个技术栈各至少一个 fixture；library 与 CLI/application 在矩阵中都被覆盖。断言最小源码、smoke test、锁文件、mise tasks、Lefthook、CI 与 Renovate 配置。
5. **既有项目 fixture**：提供 Ziwei 风格 fixture：固定 Zig 和 Lefthook、已有 staged formatter 与 build test、缺少 CI 和完整只读检查。断言保留源码与版本，增量补齐缺口，并消除格式写入与测试并行的竞态。
6. **安全 fixture**：覆盖已有文件、替代工具冲突、技术栈歧义、monorepo 未指定目标、部分暂存同一文件、未知模板文件和不允许的全局修改。断言 Skill 停止或保留，不静默迁移或覆盖。
7. **任务契约测试**：解析 `mise.toml`，确认七个公共任务均存在真实命令，`ci` 只调用只读门禁，pre-commit 不包含完整测试或构建。
8. **hook 顺序测试**：在临时 Git 仓库制造 staged-only、unstaged-only 和 partial-stage 三种状态。验证 staged-only 可格式化并重新暂存；partial-stage 在写入前失败；命令顺序与计划一致。
9. **配置测试**：解析 workflow 与 Renovate JSON，验证 Ubuntu-only、action SHA 固定、CI 单一入口、`config:recommended`、semantic commits、`dependencies` label，以及所有禁止的自动化默认关闭。
10. **失败测试**：模拟网络失败、包安装失败、hook 安装失败和质量门失败。断言状态为 partial 或 blocked，并保留精确失败命令与恢复步骤。
11. **分层证据**：离线 fixtures 是每次提交必跑的确定性证据；真实工具链 smoke tests 在可用环境中运行；live Codex behavior eval 用于验证交互与判断，但不能作为唯一回归证据。
12. **真实 smoke tests**：对每个栈运行生成后的 `mise run format-check`、`lint`、`check`、`test`、`build` 和 `ci`。若某生态命令会写 cache 或 artifact，测试在临时 workspace 中运行并记录副作用。

## Out of Scope

- Web、GUI、服务框架或特定业务领域模板。
- 多语言、多 package/module monorepo 的自动编排。
- Windows 行为保证。
- 未经确认迁移 asdf、Volta、Husky、pre-commit 或其他既有工具链。
- 自动创建 commit、push 分支或创建 pull request。
- 安装或授权 Renovate GitHub App。
- Renovate auto-approve、automerge、自定义 schedule 和默认 lockfile maintenance。
- 默认生成许可证、贡献指南、发布、部署或制品发布流程。
- 将格式、构建、测试或更新依赖命令描述为绝对无副作用。

## Further Notes

- 版本与兼容性研究是有日期的证据快照；实现和维护默认版本前必须重新核对权威来源。
- Node/TypeScript 与 Python 的组合是本项目明确选择的生态基线，并非语言官方定义的唯一方案。
- Oxlint 的 type-aware type checking 不作为必需门禁；TypeScript 独立使用稳定 `tsc --noEmit`。
- Renovate 能识别所选配置位置及 mise、Cargo、npm/pnpm、PEP 621/uv、Go modules 等 manager，但“可识别”不等于授权执行潜在不安全的 lockfile 更新命令。
- Skill 验收以临时 workspace 的实际变更和真实命令结果为准，不能仅凭最终回答文本或静态文件存在性宣称完成。
