# 项目初始化 Skill：首版技术栈官方资料研究

核对日期：2026-08-14。范围仅包括首版拟支持的 Zig、Rust、TypeScript/Node.js、Python 和 Go。

本文只把语言官网、官方文档、官方源码/注册表，以及由项目维护方发布的一手文档作为事实来源。下文将“不会修改受版本控制的项目文件”称为**源码只读**；构建缓存、依赖目录、字节码、测试自身的副作用另行说明，不能因为源码只读就声称命令对文件系统完全无写入。

## 结论摘要

| 技术栈               | 2026-08-14 当前稳定版本                               | 官方/原生初始化能力                                                             | 原生质量基线的主要缺口                                                                            |
| -------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Zig                  | 0.16.0                                                | `zig init` 创建通用包骨架，同时含 executable 和 library 示例                    | 没有按库/CLI/服务选择的形态参数，也没有随编译器提供的独立 lint 命令                               |
| Rust                 | 1.97.1                                                | `cargo new` / `cargo init`，可选 `--bin` 或 `--lib`                             | Clippy 和 rustfmt 是官方工具链组件，但不是 Cargo 内建命令本体，需确保组件可用                     |
| Node.js + TypeScript | Node.js 26.7.0 Current；24.19.0 LTS；TypeScript 7.0.2 | `npm init` 只建立 npm package；`tsc --init` 只建立 TypeScript 配置              | 无官方统一的应用/库脚手架、formatter 或完整 TypeScript lint 基线；TypeScript 7.0 暂无稳定编程 API |
| Python               | 3.14.7                                                | 标准库只有 `venv` 环境初始化；PyPA 教程要求手工建立项目结构并选择 build backend | 无标准库项目脚手架、formatter、linter、静态类型检查器或统一 build backend                         |
| Go                   | 1.26.6                                                | `go mod init` 只建立 module；应用/库源码需另建                                  | 无按项目形态生成源码的官方脚手架；`gofmt -d` 可做格式门，但需使用其退出码而非仅观察输出           |

版本号是核对日快照，不应永久写死进 Skill。执行时应遵循“用户指定 → 已有仓库约束 → 当日官方稳定来源”的解析顺序，并写入精确版本；这是本文基于可复现性的**工程建议**，不是五种语言共同规定的规范。

## Zig

### 官方事实

- 官网 Download 页面把 `master` development build 与 tagged release 分开列出；最新 tagged release 是 **0.16.0**（2026-04-13），Learn 页面称其为 Latest Stable。[Downloads](https://ziglang.org/download/) · [Learn](https://ziglang.org/learn/)
- `zig init` 在当前目录创建 `build.zig`、`build.zig.zon`、`src/main.zig` 和 `src/root.zig`。官方 Overview 展示的输出同时包含 executable 入口和 library root，没有记录 `--lib`、`--bin` 等形态选择参数。[Overview](https://ziglang.org/learn/overview/) · [Getting Started](https://ziglang.org/learn/getting-started/)
- `zig build` 执行项目的 `build.zig` 构建图；`zig build test` 只有在构建脚本定义并连接相应 test step 时才有该语义。官方 Build System 文档说明 test artifact 还需由 `addRunArtifact` 建立运行 step，不能把“编译了测试”当作“执行了测试”。[Build System: Testing](https://ziglang.org/learn/build-system/#Testing)
- 对单一 source file，`zig test file.zig` 创建并运行 test build；官方语言参考明确说明默认 runner 会运行解析到的 `test` declarations。[Zig Test](https://ziglang.org/documentation/0.16.0/#Zig-Test)
- `zig fmt` 原地格式化；`zig fmt --check` 检查格式并在存在不合规文件时失败，不覆盖源码。[0.16.0 Language Reference](https://ziglang.org/documentation/0.16.0/) · [compiler `fmt` source](https://codeberg.org/ziglang/zig/src/branch/master/src/fmt.zig)

### 文件副作用

- **修改项目文件：** `zig init`；`zig fmt`（不带 `--check`）。
- **源码只读、可作 CI 门：** `zig fmt --check .`；`zig test …`；正确配置后的 `zig build test`。后二者会使用 Zig 的本地/全局构建缓存，测试代码本身也可能有任意运行时副作用。
- **不能作为通用 CI 断言：** 仅调用 `zig build test` 而未审计 `build.zig` 是否真正定义并运行测试 artifact。

### 对 Skill 的建议

- `zig init` 只能作为创建通用最小骨架的官方入口；“library、CLI、service”等项目形态需由 Skill 在用户确认后对生成结果做窄幅整理，不能声称这些是 `zig init` 原生模板。
- 至少验证 `zig fmt --check .` 和 `zig build test`，并静态确认测试 step 连接了运行 artifact。

## Rust

### 官方事实

- Rust Release Team 最新稳定公告是 **1.97.1**（2026-07-16）。[Release announcement](https://blog.rust-lang.org/2026/07/16/Rust-1.97.1/) · [Release index](https://blog.rust-lang.org/releases/)
- `cargo new PATH` 在新目录创建 package；`cargo init [PATH]` 在已有目录创建 manifest，并复用典型命名的现有 Rust source。两者均支持 binary（默认/`--bin`）或 library（`--lib`）；`cargo init` 在没有对应源码时生成 `src/main.rs` 或 `src/lib.rs`。[Creating a New Package](https://doc.rust-lang.org/cargo/guide/creating-a-new-project.html) · [`cargo init`](https://doc.rust-lang.org/cargo/commands/cargo-init.html)
- Cargo 默认还可能初始化 VCS；可用 `--vcs none` 禁止。这意味着在 Skill 已经管理目标仓库时必须显式控制该参数。[`cargo init`](https://doc.rust-lang.org/cargo/commands/cargo-init.html)
- `cargo check` 检查 package 与依赖，但跳过最终 code generation；它会把编译 metadata 写入磁盘，而且部分只有 code generation 才产生的诊断不会出现。[`cargo check`](https://doc.rust-lang.org/cargo/commands/cargo-check.html)
- `cargo build` 执行完整构建；`cargo test` 编译并执行 unit、integration 和 documentation tests。[Cargo commands](https://doc.rust-lang.org/cargo/commands/cargo.html) · [`cargo test`](https://doc.rust-lang.org/cargo/commands/cargo-test.html)
- rustfmt 是 Rust 官方项目工具；`cargo fmt` 会改写文件，`cargo fmt --all -- --check`（新版本也支持 `cargo fmt --check`）只检查并以退出码表达差异。rustfmt 通过 `rustup component add rustfmt` 安装。[rustfmt](https://github.com/rust-lang/rustfmt)
- Clippy 是随 Rust toolchain 分发的可选组件，不是 Cargo 内建命令；`cargo clippy` 做检查，`cargo clippy --fix` 会应用修改。官方 CI 指南建议与编译器使用相同 toolchain，并可用 `-Dwarnings` 使 warning 导致失败。[Clippy installation](https://doc.rust-lang.org/stable/clippy/installation.html) · [Clippy usage](https://doc.rust-lang.org/stable/clippy/usage.html) · [Clippy CI](https://doc.rust-lang.org/clippy/continuous_integration/)
- Cargo 命令需要解析 dependency graph 时可能创建或更新 `Cargo.lock`；`--locked` 要求 lockfile 存在且解析不得改变它，否则失败。[Dependency resolution](https://doc.rust-lang.org/cargo/reference/resolver.html) · [`cargo test --locked`](https://doc.rust-lang.org/cargo/commands/cargo-test.html)

### 文件副作用

- **修改项目文件：** `cargo new`、`cargo init`、`cargo fmt`、`cargo fix`、`cargo clippy --fix`。
- **源码只读、可作 CI 门：** `cargo fmt --all -- --check`；`cargo check --locked`；`cargo clippy --locked -- -D warnings`；`cargo test --locked`。check/clippy/test 仍会写 `target/` 与共享缓存；tests/build scripts/procedural macros 还可能有额外副作用。
- **可能改变 lockfile：** 不带 `--locked` 的 build/check/test 等依赖解析命令；新 package 首次解析依赖时尤其如此。

### 对 Skill 的建议

- 新项目按用户确认的 library 或 binary 选择 `cargo new --lib` / `--bin`；在已存在仓库内用 `cargo init --vcs none`，且只在确认不会覆盖现有 manifest/source 后执行。
- 把 rustfmt 与 Clippy 声明为同一精确 Rust toolchain 的组件；CI 对已经提交 lockfile 的项目使用 `--locked`。

## TypeScript / Node.js

### 版本与项目初始化的官方事实

- Node 官方 distribution index 在核对日的最高 Current release 是 **v26.7.0**；最新 LTS 线是 **v24.19.0 Krypton**。Node 官方说明生产应用应使用 Active LTS 或 Maintenance LTS，因此“当前最高版本”和“项目默认生产版本”不是同一概念。[Distribution index](https://nodejs.org/dist/index.json) · [Release policy](https://nodejs.org/en/about/previous-releases)
- npm registry 的 `typescript` `latest` dist-tag 在核对日是 **7.0.2**。[Official npm registry metadata](https://registry.npmjs.org/typescript/latest) · [TypeScript 7 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)
- 无 initializer 参数的 `npm init` 询问 package metadata 并写 `package.json`；`npm init -y` 跳过问答。已有字段保持不变。`npm init <initializer>` 实际会解析并执行 `create-<initializer>` package；其生成内容和副作用属于所选生态 initializer，不属于 npm 自身保证。[`npm init`](https://docs.npmjs.com/cli/commands/npm-init/) · [Creating `package.json`](https://docs.npmjs.com/creating-a-package-json-file/)
- `tsc --init` 只创建 `tsconfig.json`；它不是应用、库或 CLI 代码脚手架。[tsc CLI](https://www.typescriptlang.org/docs/handbook/compiler-options.html)
- `tsc` 默认按最近的 `tsconfig.json` 做 type-check 与 emit；`--noEmit` 禁止 JavaScript、source map 和 declaration 输出，可把编译器用作源码 type checker。若启用 `incremental`/`composite`，仍可能写 `.tsbuildinfo`。[tsc CLI](https://www.typescriptlang.org/docs/handbook/compiler-options.html) · [`noEmit`](https://www.typescriptlang.org/tsconfig/noEmit.html) · [`incremental`](https://www.typescriptlang.org/tsconfig/incremental.html)
- Node 自带的 TypeScript type stripping 不做 type checking，并忽略 `tsconfig.json`；完整 TypeScript 语法支持需要第三方 package。因此 `node file.ts` 成功不能替代 `tsc --noEmit`。[Node TypeScript modules](https://nodejs.org/api/typescript.html)
- Node 自带的 `node:test` runner 已稳定，可用 `node --test` 发现并执行测试；它不替代 formatter、linter 或 TypeScript compiler。[Node test runner](https://nodejs.org/api/test.html)

### 必须做出的生态工具选择

- TypeScript/Node 官方工具链没有统一 formatter。Prettier 的一手文档区分 `prettier . --write`（改写）与 `prettier . --check`（只检查），并明确建议把精确版本作为本地 dev dependency；这是**生态方案**，不是 Node/TypeScript 规范。[Prettier installation](https://prettier.io/docs/install.html)
- Node/TypeScript 没有原生通用 lint 基线。ESLint 官方 initializer 是 `npm init @eslint/config@latest`，会根据问答创建配置；对 TypeScript 还需 parser/plugin 生态。[ESLint Getting Started](https://eslint.org/docs/latest/use/getting-started) · [typescript-eslint Getting Started](https://typescript-eslint.io/getting-started/)
- 核对日 `typescript-eslint` 明确支持的 TypeScript 范围是 `>=4.8.4 <6.1.0`，而 TypeScript 最新稳定版已是 7.0.2。TypeScript 7.0 官方也说明它尚无稳定 programmatic API，并给出并行安装 TypeScript 6 compatibility package 的过渡方案。因此 Skill 不能机械组合“最新 TypeScript 7 + 最新 typescript-eslint”并宣称官方兼容。[typescript-eslint dependency versions](https://typescript-eslint.io/users/dependency-versions/) · [TypeScript 7 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)
- TypeScript 编译器负责 type-check/emit，不承担打包。若项目形态需要 browser bundle、单文件 library output 或 framework app，必须再确认 bundler/framework initializer；TypeScript 6 官方已明确把 bundling 交给 external bundlers。[TypeScript 6 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/)

### 文件副作用

- **修改项目文件：** `npm init`、`tsc --init`、`npm install`（依赖目录并通常更新 lockfile/package metadata）、`prettier --write`、`eslint --fix`，以及任何 `npm init <initializer>`。
- **冻结依赖元数据但仍大量写磁盘：** `npm ci` 不写 `package.json` 或 lockfile，但会删除并重建 `node_modules`，还可能运行 lifecycle scripts。[`npm ci`](https://docs.npmjs.com/cli/commands/npm-ci/)
- **源码只读、可作 CI 门：** `tsc --noEmit`（同时关闭 `incremental` 或把 `.tsbuildinfo` 明确放入缓存目录）；`node --test`；`prettier . --check`；不带 `--fix`/`--cache` 的 `eslint .`。测试和依赖 scripts 仍可能产生任意副作用。
- **会创建缓存文件：** ESLint 的 `--cache` 默认创建 `.eslintcache`；TypeScript incremental 创建 `.tsbuildinfo`。[ESLint CLI](https://eslint.org/docs/latest/use/command-line-interface) · [`incremental`](https://www.typescriptlang.org/tsconfig/incremental.html)

### 对 Skill 的建议

- Node 版本默认值应区分通用实验/工具与生产项目；生产型新项目优先当前 LTS，而不是最高 Current。
- 先让用户确认 package 形态（library、CLI、service、browser/framework app）和 package manager；仅 `npm init` + `tsc --init` 不足以表达这些形态。
- TypeScript 7.0 过渡期内，把“纯 `tsc` 基线”和“需要 TypeScript compiler API 的 lint/framework 基线”分开解析兼容版本，遇到不兼容就报告而不是静默降级。

## Python

### 官方事实

- Python 官网核对日最新稳定 bugfix release 是 **3.14.7**（2026-08-05）；3.15 仍为 pre-release。[Python downloads](https://www.python.org/downloads/)
- 标准库 `python -m venv .venv` 创建虚拟环境目录、解释器链接/副本、`pyvenv.cfg` 和 site-packages；它不是项目源码脚手架。Python 3.13 起还默认在环境目录创建 Git `.gitignore`。[`venv`](https://docs.python.org/3.14/library/venv.html)
- PyPA 官方 Packaging Tutorial 要求建立 `pyproject.toml`、README、license、`src/<package>/` 与 tests，并明确必须选择 build backend；教程默认演示 Hatchling，也列出 Setuptools、Flit、PDM 等，未指定唯一官方 backend。[Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/) · [Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- `python -m build` 是 PyPA 教程的标准 build frontend 调用，会在 `dist/` 产生 sdist 和 wheel；`build` package 与实际 build backend 都不是 Python 标准库。[Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- 标准库 `python -m unittest` 等价于 discovery，默认匹配 `test*.py` 并导入测试模块后执行测试。[`unittest`](https://docs.python.org/3/library/unittest.html)
- Python runtime 不强制函数/变量类型注解，官方 `typing` 文档明确把静态检查交给第三方 type checker。[`typing`](https://docs.python.org/3/library/typing.html)

### 必须做出的生态工具选择

- Python 标准库没有 project initializer、formatter、linter、静态 type checker 或统一 build backend；至少要分别确定项目生成/依赖管理、format/lint、typing、build backend。
- `uv init` 是 Astral 维护的生态入口，可创建 application（默认）、packaged application（`--package`）或 library（`--lib`），但不属于 Python/PSF 标准库；选它会同时引入 uv 的 environment、lockfile 和 build backend 约定。[uv Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- Ruff 是生态 formatter/linter：`ruff format` 改写，`ruff format --check` 只检查；`ruff check` lint，`ruff check --fix` 改写。Ruff 默认使用 `.ruff_cache`，可用 `--no-cache` 避免项目缓存。[Ruff formatter](https://docs.astral.sh/ruff/formatter/) · [Ruff linter](https://docs.astral.sh/ruff/linter/) · [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- mypy 是一种第三方静态 type checker，而不是 Python 官方唯一选择。[mypy Getting Started](https://mypy.readthedocs.io/en/stable/getting_started.html)

### 文件副作用

- **修改项目文件/目录：** `python -m venv .venv`、`python -m build`、`uv init`、`uv sync`、`ruff format`、`ruff check --fix`。
- **源码只读但默认可能写缓存：** `python -m unittest` 可因 module import 写 `__pycache__`；Ruff 默认写 `.ruff_cache`；mypy 默认写 cache；build/test code 自身也可能有副作用。
- **更接近 CI 源码只读：** `PYTHONDONTWRITEBYTECODE=1 python -m unittest`、`ruff format --check --no-cache .`、`ruff check --no-cache .`、静态 type checker 的无 cache/外置 cache 配置。依赖同步需使用所选工具的 frozen/locked 模式；例如 uv 提供 `uv lock --check` 与 `uv sync --locked`。[uv locking](https://docs.astral.sh/uv/concepts/projects/sync/)

### 对 Skill 的建议

- 项目形态必须先确认：script/application、packaged CLI/application、library 的结构和 build 要求不同。
- 若首版采用 uv + Ruff + 某一 type checker，应明确标为 Skill 的**有意生态基线**，不能表述为 Python 官方默认；build backend 同样应由项目形态或用户选择决定。

## Go

### 官方事实

- Go 官方下载 JSON 在核对日把 **go1.26.6** 标为 stable。[Download JSON](https://go.dev/dl/?mode=json)
- `go mod init [module-path]` 只初始化并写入新的 `go.mod`，现有 `go.mod` 会导致失败；它不会生成 application 或 library source。[Go Modules Reference](https://go.dev/ref/mod#go-mod-init)
- Go 官方教程对 library 与 executable 都先运行 `go mod init`，然后由作者创建 `.go` source；可执行命令必须使用 `package main`。因此 Go 原生初始化器没有 `--lib` / `--bin` 形态模板。[Create a Go module](https://go.dev/doc/tutorial/create-module) · [How to Write Go Code](https://go.dev/doc/code)
- `gofmt -w` 覆盖不合规文件；`gofmt -d` 输出 diff、不改源码，并在格式不同的时候返回非零退出码。只用 `gofmt -l` 会列文件但不会因差异自动失败。[gofmt command](https://pkg.go.dev/cmd/gofmt) · [official `gofmt` source](https://go.dev/src/cmd/gofmt/gofmt.go)
- `go build` 构建 packages；构建单个 main package 时默认可能在当前目录写 executable，而构建多个 package 或非-main package 时丢弃结果并主要充当 build check。[`go` command](https://pkg.go.dev/cmd/go)
- `go test` 编译并执行每个 package 的测试 binary，并在构建测试时运行一组高置信度 `go vet` 检查；显式 `go vet ./...` 可作为单独入口。[`go` command: test](https://pkg.go.dev/cmd/go)
- module-aware build/test/list/vet 等命令读取 dependency graph。默认通常表现为 `-mod=readonly`，发现需要改变 `go.mod` 时失败；`-mod=mod` 则允许更新 `go.mod`/`go.sum`。`go mod tidy` 明确用于修改 module metadata 使其与源码匹配。[Go Modules Reference](https://go.dev/ref/mod#build-commands)

### 文件副作用

- **修改项目文件：** `go mod init`、`go mod tidy`、`gofmt -w`、`go fmt`；`go generate` 会运行任意 generator，意图就是创建或更新 source。
- **源码只读、可作 CI 门：** `gofmt -d .`；`go vet -mod=readonly ./...`；`go test -mod=readonly ./...`。它们会写共享 build/module/test cache，测试与 cgo/build tools 也可能有其他副作用。
- **构建入口需谨慎：** `go build ./...` 适合作为 package-wide build check，通常把产物放入 cache；对单个 main package 直接 `go build` 可能在项目目录写 executable。[`go` command](https://pkg.go.dev/cmd/go)

### 对 Skill 的建议

- 先要求 module path 与项目形态。执行 `go mod init` 后，由 Skill 生成一个无业务语义的 `package main` 或 library package 以及 smoke test；这部分是 Skill 模板，不是 Go initializer 输出。
- 本地修复任务使用 `gofmt -w`；CI 使用 `gofmt -d .` 并依赖非零退出码，同时为 dependency-sensitive commands 显式设置 `-mod=readonly`，让意外 metadata 漂移失败。

## 跨技术栈的事实边界与设计建议

### 可以统一的流程

以下是从上述官方能力归纳出的**工程建议**，不是任何单一语言的官方规范：

1. 先识别目标目录是新项目还是已有项目，并读取已有 manifest、lockfile、源码和工具链约束。
2. 询问项目形态；只凭语言不能推断 library、CLI、service 或 framework application。
3. 优先使用语言官方 initializer；官方 initializer 不覆盖所需形态时，只生成最小、无业务语义、可构建且含 smoke test 的补充文件。
4. 明确拆分 `format`（会写源码）、`format-check`（不写源码）、`check`、`test`、`build` 和 `ci` 任务；不能让 CI 调用会改源码或 lockfile 的任务。
5. CI 的“只读”应定义为“不改变受版本控制的项目文件”，同时公开 cache、artifact、dependency directory、bytecode 和测试运行副作用。
6. 有 lockfile 的生态在 CI 使用 frozen/locked/readonly mode；初始化阶段负责有意生成并验证 lockfile。
7. 初始化完成不能只证明命令退出 0：至少应有一个无业务语义的 smoke test，证明测试发现和执行入口实际工作。

### 不能统一、必须保留的决策点

- **项目形态：** Rust 只有 bin/lib；Zig initializer 同时生成两种入口；Node、Python、Go 需要 Skill 或生态 initializer 补充。
- **Node/TypeScript：** package manager、module system、runtime vs emitted JavaScript、formatter/linter、bundler/framework，以及 TypeScript 7 compiler API 兼容性。
- **Python：** application/library/packaged CLI、project/dependency manager、build backend、formatter/linter、type checker。
- **Go：** module path 是 import identity，不能仅用本地目录名随意生成将来要发布的 module path。
- **版本策略：** Node 的 highest Current 与 production LTS 不同；TypeScript 最新稳定与依赖 compiler API 的工具当前可能不兼容。

## 未覆盖与待验证项

- 本文未选择 mise、Lefthook、GitHub Actions 的具体版本或配置，也未研究不同 package manager（npm/pnpm/yarn/bun）、Python manager/backend、framework initializer 的组合；这些应在 Skill 的工具层另行调查。
- 没有在五种最新工具链上逐一执行所有命令并记录精确生成文件快照；initializer 模板和 CLI 参数仍须由实现测试锁定，并在版本升级时刷新 fixture。
- 没有证明任一测试命令对运行环境无副作用。测试、build script、lifecycle script、generator 与 compiler plugin 都能运行项目代码；Skill 只能保护自身生成的命令和版本控制文件边界。
- TypeScript 7.0 的 compiler API 生态仍处过渡期；实现前必须重新检查 `typescript-eslint`、framework 和 bundler 的官方兼容范围。
