# Zig Agent Skill 官方资料研究

核对日期：2026-08-13。仅使用 Zig 官方网站与 `ziglang/zig` 官方源码。下面明确区分官方明确规则、目标版本的官方编码风格与本 Skill 的工程建议；具体 API、编码风格和最佳实践始终服从用户指定或项目实际使用的工具链版本。

## 当前版本快照与默认选择

- 截至核对日期，官网最新稳定版是 **Zig 0.16.0**，Download 页面标注发布日期为 2026-04-13；官网 Learn 页面将它标为 “Latest Stable (0.16.0)”。[Downloads](https://ziglang.org/download/) · [Learn](https://ziglang.org/learn/) · [0.16.0 release notes](https://ziglang.org/download/0.16.0/release-notes.html)
- 同日官网 `master` 下载快照是 **0.17.0-dev.1737+de207594e**，构建日期为 2026-08-12。它是持续变化的 development build，不是稳定版；精确版本和日期应在每次任务中重新读取 Download 页面或其官方 JSON，而不能长期固化。[Downloads](https://ziglang.org/download/) · [Download JSON](https://ziglang.org/download/index.json)
- 官网当前 Download 页面先列 `master`，再列 `0.16.0` 等 tagged releases；Learn 页面则明确称前者为 “Unstable (master)”、后者为 “Latest Stable (0.16.0)”。因此界面或上下文中的 “Latest Builds” 应理解为 `master` development builds，而不是 “Latest Stable”。[Downloads](https://ziglang.org/download/) · [Learn](https://ziglang.org/learn/)
- 版本解析顺序是：用户明确指定的版本 → 仓库约束或固定工具链 → 当前可执行的 `zig version`。若三者都不能确认，默认使用**核对当日官网最新稳定版**，不默认选择 `master`、nightly 或 development build；执行具体任务前应重新查询官网，不能永远假定是 0.16.0。官方 Getting Started 说明 tagged release 更适合有依赖且重视稳定性的项目，而 development build 面向参与 Zig 开发的人。[Getting Started](https://ziglang.org/learn/getting-started/)

## 官方文档版本路由

- 稳定版 `V` 使用版本化的 Language Reference `https://ziglang.org/documentation/V/`、Standard Library Documentation `https://ziglang.org/documentation/V/std/`，并在该版本 Download 条目提供时使用 `https://ziglang.org/download/V/release-notes.html`。以 0.16.0 为例：[Language Reference](https://ziglang.org/documentation/0.16.0/) · [Standard Library Documentation](https://ziglang.org/documentation/0.16.0/std/) · [Release Notes](https://ziglang.org/download/0.16.0/release-notes.html)
- 只有项目明确使用 nightly/development build 时，才路由到 [master Language Reference](https://ziglang.org/documentation/master/) 与 [master Standard Library Documentation](https://ziglang.org/documentation/master/std/)。Getting Started 也明确要求 nightly builds 使用 `master` docs；尚未发布的 master 没有对应的稳定版 release notes。[Getting Started](https://ziglang.org/learn/getting-started/)
- Download 页面每个 tagged release 分别链接该版本的 Language Reference、Standard Library Documentation，并在存在时链接 Release Notes；官方 JSON 也分别以 `docs`、`stdDocs`、`notes` 字段表达这些入口。[Downloads](https://ziglang.org/download/) · [Download JSON](https://ziglang.org/download/index.json)

## 官方明确规则与工具行为

1. **先确定版本，再读文档。** 按“用户指定 → 仓库/工具链证据 → 官网当前最新稳定版”的顺序选定版本；稳定版使用对应版本文档，nightly/master 才使用 master 文档。[Getting Started](https://ziglang.org/learn/getting-started/) · [Downloads](https://ziglang.org/download/)
2. **`build.zig` 是会执行的 Zig 代码。** build runner 导入构建脚本并调用其 `build` 函数；不应把它当作静态配置。`build.zig.zon`、Build API 与包规则会随版本演进。[Build System](https://ziglang.org/learn/build-system/) · [官方 build runner](https://github.com/ziglang/zig/blob/master/lib/compiler/build_runner.zig) · [0.16.0 release notes](https://ziglang.org/download/0.16.0/release-notes.html#Build-System)
3. **测试编译与运行是两个 step。** 构建系统创建测试 artifact 后，需要 `addRunArtifact` 建立运行 step；缺少它时测试不会执行。单文件可以使用 `zig test`，复杂 target、依赖与链接应通过项目构建图验证。[Build System: Testing](https://ziglang.org/learn/build-system/#Testing) · [Language Reference: Zig Test](https://ziglang.org/documentation/0.16.0/#Zig-Test)
4. **格式化写入与检查不同。** `zig fmt` 原地修改，`zig fmt --check` 只报告不合规文件并以错误退出；执行时仍以当前工具链的 `zig fmt --help` 为准。[0.15.2 `src/fmt.zig`](https://github.com/ziglang/zig/blob/0.15.2/src/fmt.zig) · [master `src/fmt.zig`](https://github.com/ziglang/zig/blob/master/src/fmt.zig)
5. **交叉编译成功不代表目标程序运行成功。** target 产物能否在当前主机、模拟器或真实 target 上执行是另一项证据。[Targets](https://ziglang.org/documentation/0.16.0/#Targets) · [Build System: Testing](https://ziglang.org/learn/build-system/#Testing)
6. **Zig 没有默认 allocator。** allocator 选择取决于生命周期和约束；`std.testing.allocator` 可用于测试泄漏。错误联合、`try`、`catch` 和 `errdefer` 是官方语言机制，标准库具体 API 按版本核对。[Memory](https://ziglang.org/documentation/0.16.0/#Memory) · [Choosing an Allocator](https://ziglang.org/documentation/0.16.0/#Choosing-an-Allocator) · [Errors](https://ziglang.org/documentation/0.16.0/#Errors)
7. **C 互操作有两种官方入口。** 简单 header 使用可评估 `@cImport`；需要独立 cflags 或可编辑翻译结果时使用 `zig translate-c`。`extern`/C ABI、libc、链接和 target 配置仍需单独核对。[C](https://ziglang.org/documentation/0.16.0/#C) · [@cImport vs translate-c](https://ziglang.org/documentation/0.16.0/#cImport-vs-translate-c)
8. **文档注释有编译器语义。** `///` 记录紧随其后的声明，`//!` 记录当前 module/container，并受放置位置约束。[Comments](https://ziglang.org/documentation/0.16.0/#Comments)

## 目标版本的官方编码风格

Zig 0.16.0 Language Reference 随该版本提供完整 [Style Guide](https://ziglang.org/documentation/0.16.0/#Style-Guide)，并明确说明这些编码约定不由编译器强制，而是随编译器文档发布的权威参考。它覆盖避免名称冗余、避免下划线前缀、空白、命名、示例与文档注释。

0.16.0 的命名基线是：类型和返回类型为 `type` 的 callable 使用 `TitleCase`，其他 callable 使用 `camelCase`，其他值通常使用 `snake_case`；类型文件使用 `TitleCase`，namespace 文件与目录使用 `snake_case`。缩写词同样服从所在类别，已有外部约定可以例外。空白基线包括 4 空格缩进、通常同一行放置左花括号、长于两项的列表逐项换行并保留尾随逗号，以及以约 100 字符为目标但按实际可读性判断。[Zig 0.16.0 Style Guide: Whitespace](https://ziglang.org/documentation/0.16.0/#Whitespace) · [Zig 0.16.0 Style Guide: Names](https://ziglang.org/documentation/0.16.0/#Names)

Style Guide 与最佳实践必须按已解析出的目标 Zig 版本读取：目标是稳定版 `V` 时使用 `documentation/V/` 中的 Style Guide、语言规则和 `std` 文档；目标明确是 development build 时才使用 `master`。仅当用户、仓库和已安装工具链都无法确认版本时，才使用官网当日最新稳定版作为默认值。`zig fmt` 负责机械格式，但不能替代目标版本 Style Guide 中的命名、文档和 API 设计约定。

## 版本敏感路由

- 先读取用户指定版本与项目版本约束，再用 `zig version` 核对实际工具链；证据冲突时停止并报告，不自动迁移。
- 使用 `zig env` 定位当前发行包的标准库源码；`zig env` 字段布局也可能变化，避免跨版本解析固定文本。[Standard Library](https://ziglang.org/documentation/0.16.0/#Zig-Standard-Library) · [`print_env.zig`](https://github.com/ziglang/zig/blob/master/src/print_env.zig)
- 多版本兼容优先进行 capability detection，例如目标版本支持时使用 `@hasDecl`/`@hasField`，而不是散落版本号判断。[Compile Variables](https://ziglang.org/documentation/0.16.0/#Compile-Variables)
- 修改 `build.zig`、`build.zig.zon`、标准库、allocator、I/O、C interop 或 target 配置时，查对应版本语言参考、标准库、CLI `--help` 与 release notes，不把 master 示例反向移植到稳定版。

## 本 Skill 的工程建议

以下是由官方机制推导的稳定工作方法，不声称是 Zig 编译器规范：

- 报告测试时区分 `compiled`、`executed` 和 `passed`。
- 修改远程依赖前核对来源、修订、许可证和副作用；由目标工具链生成或验证 hash，并在隔离缓存验证解析。`zig fetch` 的精确参数以目标版本 `zig fetch --help` 为准。
- 项目声明多版本支持时，区分最低版本、支持范围、当前执行编译器和格式化器版本；默认以最低支持版与范围内最新稳定版作为代表性工具链，而不是把版本下限当作精确固定。
- 外部输入失败返回普通错误；`unreachable` 只表达已证明的不变量。`@setRuntimeSafety(false)` 只在有测量、明确前置条件和测试保护的最小作用域使用。
- C adapter 保持窄边界，逐项记录 ABI、所有权、callback 生命周期和错误转换；验证分为编译、链接和目标环境运行。
- 显式版本迁移按 release notes 分类处理语言、标准库、Build API、manifest 和 target 变化，并保留回滚边界。
- 性能优化先固定版本、target、optimization mode、输入和环境，建立基线并定位瓶颈；相同条件下重复测量，同时保持正确性回归。Zig 官方没有在上述资料中规定统一 benchmark 框架。

## 本地验证边界

- 2026-08-13 使用本地 Zig 0.16.0 运行 `scripts/run-toolchain-smoke.mjs`，已验证 fixture 通过 `zig fmt --check`，且 `zig build test` 实际执行测试 artifact。
- 同一宿主上的 Zig 0.15.2 在 macOS 26.5 SDK 环境编译 build runner 时出现系统符号链接失败，因此没有声称该版本 smoke 通过。这一结果说明代表性版本仍需在兼容宿主或 CI 中分别验证，不能由 0.16.0 结果外推。
- 仍未对所有 CLI 参数、target 或项目级构建进行穷举验证；精确行为继续以目标工具链 `--help`、对应版本源码与真实项目验证为准。
