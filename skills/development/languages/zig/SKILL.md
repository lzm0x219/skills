---
name: zig
description: 构建、修改、调试、测试、优化、迁移和审查 Zig 应用与库。适用于 `.zig` 源码、编码风格、API 设计、`build.zig`、`build.zig.zon`、依赖、Zig 构建系统、`comptime`、allocator 与所有权、error unions、C 互操作、交叉编译、性能和编译器诊断以及 Zig package 维护。编码风格、最佳实践、语法、标准库 API、Build API、编译器选项和目标行为必须匹配目标 Zig 版本；用户与仓库都未指定版本时，查询 Zig 官网并使用当时最新稳定版。
---

# Zig 开发

## 通用工作流

### 确定仓库与版本边界

- 提出改动前，读取仓库指引、`git status`、`build.zig`、`build.zig.zon`、版本固定文件、相邻源码和测试。
- 按此顺序确定任务目标 Zig 版本或支持范围：用户显式要求；否则仓库版本固定、manifest 约束、CI 配置或项目 toolchain；均无证据时，查询官方 [Download](https://ziglang.org/download/) 或 [Learn](https://ziglang.org/learn/) 页面，并使用当时最新稳定版。
- 区分最低版本、支持范围、当前编译器版本和 formatter 版本。`minimum_zig_version` 一类下界不是精确固定版本。项目支持多个版本时保留 CI 矩阵，并为每次验证选择明确编译器；默认至少验证最低支持版和支持范围内最新稳定版。
- 使用仓库指定的 formatter 版本；未单独指定时，用当前验证编译器运行 `zig fmt`。不同编译器格式化结果不同则遵循仓库指定版本并报告差异。
- 没有版本证据时，不使用记忆中的版本号，也不将 master/nightly 视为“最新版本”；只在用户明确要求开发版时才以 master/nightly 为目标。
- 本地存在 Zig 时，将 `zig version` 与目标版本比较。本地版本与用户或仓库版本冲突时，把它视为不同环境，不自动迁移项目。
- 官方网站不可用且没有其他版本证据时，报告无法验证最新稳定版并请求版本信息，不静默回退到历史版本。
- 请求与 Zig 源码、构建配置、toolchains 或 diagnostics 无关时，直接完成请求，不引入 Zig 专属流程。

完成条件：目标文件、支持版本范围、当前编译器、formatter 版本、版本证据、既有命令入口与请求范围均已明确。

### 使用版本匹配的证据

精确语法、标准库 API、Build API、编译器选项、目标行为或版本兼容性必须依赖与目标版本匹配的官方证据：

- 使用 `zig env` 与已安装编译器附带的标准库源码确认实际 toolchain。
- 确认官网当前稳定版时运行 [官方发布验证脚本](scripts/verify-official-release.mjs)；发布或刷新版本数据前加 `--verify-links`。此联网检查只证明查询时的官方索引和链接状态。
- 稳定版使用目标版本的 [语言参考](https://ziglang.org/documentation/)、Style Guide、标准库文档、发布说明和编译器附带源码；只有用户目标为 master 时才使用 master 文档。不要让其他版本的 Style Guide 覆盖目标版本规则。
- 使用官方 [构建系统指南](https://ziglang.org/learn/build-system/) 理解概念，再用目标编译器验证 API；Build API 持续演进。
- 使用 `zig <command> --help` 与项目声明的 build steps/options，不套用其他版本记忆中的选项。
- 语言参考不足时检查官方 Zig 源码，并将由源码得出的结论标为实现细节。

报告版本敏感结论时，说明目标版本、选择依据和文档来源，并区分已验证事实、工程默认值和迁移建议。

### 按任务读取规则

- 编写、重构或审查 Zig 代码，或涉及最佳实践、编码风格、运行时安全或非法行为边界时，读取 [编码最佳实践与风格](references/best-practices-and-style.md)。
- 修改 `build.zig`、`build.zig.zon`、依赖、package metadata、版本约束或 Zig 版本时，读取 [构建、依赖与版本迁移](references/build-packages-and-migrations.md)。
- 使用 C headers、C libraries、`@cImport`、`zig translate-c`、`extern`、callbacks 或 ABI 间数据时，读取 [C 互操作边界](references/c-interop.md)。
- profile、benchmark 或优化编译时间、二进制大小、内存、吞吐或延迟时，读取 [以测量驱动性能优化](references/performance-optimization.md)。

完成条件：已完成细则要求的检查，并在设计、实现和验证计划中体现每项适用边界。

### 明确构建与测试证据

- 将 `build.zig` 视为可执行项目代码；`zig build --help` 也会加载构建图。不受信任项目中，运行任何 `zig build` 子命令前先审查构建脚本、依赖声明和每个可达的系统命令步骤。
- 从当前 `build.zig` 和 `zig build --help` 推导 step 名称和 `-D` 选项，并保留项目既有 target 与 optimization 选项模型。
- 区分“测试产物已编译”“已执行”和“已通过”。只有产物实际运行并成功后，才报告测试通过；确认 test step 依赖的是运行产物的 step。
- 依赖解析、下载、全局 toolchain 改动、package publication 或其他范围外外部副作用前，明确影响并确认授权。

完成条件：构建步骤、测试执行路径、依赖副作用与成功标准均可解释。

### 实施最小兼容改动

- 遵循相邻代码与 [编码最佳实践与风格](references/best-practices-and-style.md) 中适用规则。
- 首个改动应小到可由一次定向编译或测试迅速否决。
- 测试放在所保护行为附近；allocation 或 I/O 改动覆盖失败与清理路径。
- 只对修改过的 Zig 路径运行 `zig fmt`；只读检查使用 `zig fmt --check`。
- 请求未包含版本迁移或大范围重写时，保持既有语言版本和改动边界。

### 分层扩大验证

优先使用仓库既有命令；否则只在项目支持范围内扩大验证：

1. 对修改的 Zig 文件运行 `zig fmt --check`。
2. 运行最小适用的 `zig test`，或运行具名 `zig build` 测试 step 并确认它实际执行测试产物。
3. 使用项目固定的编译器运行项目构建和其余测试。
4. 改动影响可移植性、安全、ABI 或性能时，覆盖项目声明的 target 与 optimization 组合。
5. 在兼容环境运行生成二进制或集成测试。交叉编译成功不能证明目标运行时正确。

验证本 Skill 的最小示例时，对每个代表性 toolchain 运行 [toolchain smoke script](scripts/run-toolchain-smoke.mjs)。它在隔离临时目录检查格式、构建图和真实测试执行，不替代目标仓库的测试矩阵。

分别报告精确 Zig 版本、命令、target、optimization mode 和观察结果；将 `compiled`、`executed`、`passed` 与当前不可用检查分开标记。

## 诊断顺序

1. 用项目固定编译器和最小命令复现失败。
2. 在处理后续错误前，先读取首个因果诊断及其 compile-time reference trace。
3. 将失败归类为语言语义、版本漂移、所有权／生命周期、`comptime` 求值、构建图、依赖解析、C ABI／链接、目标行为或性能回归。
4. 缩小失败边界，同时保留相关 allocator、target、optimization mode 和外部依赖。
5. 行为存在争议时，检查版本匹配的语言参考、本地标准库源码、Build API、发布说明或编译器源码。
6. 只有证据指向 cache 时才处理；将动作限制在特定项目或隔离 cache 路径，并保留无关产物。

结论包含根因、最小已验证修复、回归覆盖，以及仍未验证的平台、运行时或性能边界。
