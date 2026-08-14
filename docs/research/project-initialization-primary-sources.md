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

### 核对日版本快照

| 工具   | 最新稳定版 | 发布日期（UTC） | 工具自身的 Python 要求                                                                                                                                                                                                                                          |
| ------ | ---------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python | 3.14.7     | 2026-08-05      | 不适用；3.15 仍是 pre-release。[Python 3.14.7](https://www.python.org/downloads/release/python-3147/)                                                                                                                                                           |
| uv     | 0.12.4     | 2026-08-13      | PyPI distribution 声明 `>=3.8`；官方同时提供 standalone installer。[release](https://github.com/astral-sh/uv/releases/tag/0.12.4) · [PyPI JSON](https://pypi.org/pypi/uv/0.12.4/json) · [installation](https://docs.astral.sh/uv/getting-started/installation/) |
| Ruff   | 0.16.3     | 2026-08-13      | PyPI distribution 声明 `>=3.7`；官方同时提供 standalone installer。[release](https://github.com/astral-sh/ruff/releases/tag/0.16.3) · [PyPI JSON](https://pypi.org/pypi/ruff/0.16.3/json) · [installation](https://docs.astral.sh/ruff/installation/)           |
| mypy   | 2.3.0      | 2026-07-13      | `>=3.10`。[PyPI JSON](https://pypi.org/pypi/mypy/2.3.0/json)                                                                                                                                                                                                    |
| pytest | 9.1.1      | 2026-06-19      | `>=3.10`。[PyPI JSON](https://pypi.org/pypi/pytest/9.1.1/json)                                                                                                                                                                                                  |
| build  | 1.5.0      | 2026-04-30      | `>=3.10`。[PyPI JSON](https://pypi.org/pypi/build/1.5.0/json)                                                                                                                                                                                                   |

`build` 1.5.1 虽然后来上传，但两个 distributions 都已被 yanked，官方理由是包含可能应作为新 major 发布的 breaking changes，因此“最新可选稳定版”仍应解析为 1.5.0。[build 1.5.1 PyPI JSON](https://pypi.org/pypi/build/1.5.1/json)

以上开发工具均可运行在 Python 3.14.7。版本号只是核对日快照；初始化器仍应按“用户指定 → 既有仓库约束 → 当日官方稳定来源”解析并精确记录，而不是永久依赖这张表。

### `uv init` 的结构与副作用

- `uv init` 是 Astral 维护的生态入口，不是 Python/PSF 标准库。当前 uv 0.12 的 application 已改为**默认 packaged**：`uv init --app <path>`（`--app` 可省略）生成 `.python-version`、README、`pyproject.toml` 和 `src/<module>/__init__.py`，并写入 `[project.scripts]` 与 `uv_build` build system；0.12 以前 application 默认没有 build system。[uv Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- `uv init --lib <path>` 创建 packaged library，使用同样的 `src/` layout，并额外生成 `py.typed`；library 不能使用 unpackaged 形态。`uv init --no-package <path>` 才创建没有 build system 的 application，源码入口是顶层 `main.py`。[uv Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- `uv init --bare <path>` 只写 `pyproject.toml`，不会生成 README、`.python-version`、源码树或 Git repository；若需要完全控制模板，这是最小副作用入口。[uv Creating projects: minimal project](https://docs.astral.sh/uv/concepts/projects/init/#creating-a-minimal-project)
- 普通 `uv init` 默认初始化 Git；`--vcs none` 可明确关闭。目标已有 `pyproject.toml` 时命令直接失败，因此既有模式不能把 `uv init` 当作结构化 merger。[uv CLI: `uv init`](https://docs.astral.sh/uv/reference/cli/#uv-init)
- `--python 3.14.7` 选择用于推导最低支持版本的解释器；默认 `.python-version` 只记录发现到的 **minor** version。因此 `.python-version` 不能代替 `mise.toml` 中的 exact patch pin。[uv CLI: `--python`](https://docs.astral.sh/uv/reference/cli/#uv-init--python) · [`--no-pin-python`](https://docs.astral.sh/uv/reference/cli/#uv-init--no-pin-python)
- uv 0.12.4 默认生成 `uv_build>=0.12.4,<0.13`，这是 backend compatibility range，不是 exact build-backend pin。若项目要求构建后端也完全可复现，需另行固定 `[build-system].requires` 或为 build frontend 提供 constraints，不能把 `uv.lock` 的存在当作 build isolation 已锁定。[uv Creating projects](https://docs.astral.sh/uv/concepts/projects/init/) · [uv build constraints](https://docs.astral.sh/uv/concepts/projects/build/#build-constraints)

### Lock、环境、运行与构建命令

- `uv lock` 解析依赖并创建或更新 `uv.lock`；`uv lock --check` 只核对 lockfile 是否存在且与 project metadata 一致，过期或缺失时失败。它不会仅因 registry 出现新版本就把 lockfile 判为过期。[uv Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/#checking-the-lockfile)
- `uv sync` 在需要时先 lock，再创建或更新项目根目录的 `.venv`。默认是 exact sync，会移除 lockfile 以外的包；`dev` group 默认包含，`--all-groups` 明确包含所有 dependency groups。`uv sync --locked --all-groups` 要求 `uv.lock` 存在且最新，失败时不更新 lockfile；`--frozen` 反而跳过一致性检查，可能忽略尚未进入 lockfile 的 `pyproject.toml` 变更，所以 CI 应优先 `--locked`。[uv Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- `uv run` 会在运行命令前自动 lock 和 sync，并在环境缺失时创建 `.venv`；它的 sync 默认是 inexact。`uv run --locked ...` 阻止隐式 lockfile 更新；若已先成功执行 locked sync，可追加 `--no-sync` 避免每个门禁重复同步，但该选项会隐含 `--frozen`，不能替代前置的 `uv lock --check` / `uv sync --locked`。[uv Running commands](https://docs.astral.sh/uv/concepts/projects/run/) · [uv CLI: `--no-sync`](https://docs.astral.sh/uv/reference/cli/#uv-run--no-sync)
- `uv build` 调用 `[build-system]` 声明的 backend，默认先建 sdist、再从 sdist 建 wheel，并把两个 artifacts 写入 `dist/`。它没有 `--locked`；`--no-sources` 仅表示解析时忽略 `tool.uv.sources`、按可发布 metadata 验证，并不锁定 build requirements。[uv Building distributions](https://docs.astral.sh/uv/concepts/projects/build/) · [uv CLI: `--no-sources`](https://docs.astral.sh/uv/reference/cli/#uv-build--no-sources)
- PyPA `build` 的可靠入口是 `python -m build`：默认同样先建 sdist、再从 sdist 建 wheel，写入 `dist/`，并创建临时 isolated build environment；`--installer=uv` 只切换 build dependency installer。采用本节精确 dev dependency 时可运行 `uv run --locked python -m build --installer=uv`，但 isolated backend requirements 仍受 `[build-system]` / build constraints 控制，而不是 dev group 的 `uv.lock`。[build Basic Usage](https://build.pypa.io/en/latest/how-to/basic-usage.html) · [build CLI](https://build.pypa.io/en/latest/reference/cli.html)

推荐的 Ubuntu CI 门禁顺序是：

```sh
uv lock --check
uv sync --locked --all-groups
uv run --locked ruff format --check --no-cache .
uv run --locked ruff check --no-cache .
uv run --locked mypy --cache-dir=/dev/null src tests
PYTHONDONTWRITEBYTECODE=1 uv run --locked python -m pytest -p no:cacheprovider
uv run --locked python -m build --installer=uv
```

- `ruff format` 会改写源码；`ruff format --check` 只报告会变化的文件并在有差异时返回 1。`ruff check` 默认只报告 lint，`--fix` 才改写；`--no-cache` 关闭 cache 使用。[Ruff formatter](https://docs.astral.sh/ruff/formatter/#exit-codes) · [Ruff linter](https://docs.astral.sh/ruff/linter/) · [Ruff CLI configuration](https://docs.astral.sh/ruff/configuration/)
- mypy 默认读取并写 `.mypy_cache`；仅 `--no-incremental` 仍会写 cache。Ubuntu CI 可用 `--cache-dir=/dev/null` 禁止写入，Windows 对应 `--cache-dir=nul`。[mypy command line: incremental mode](https://mypy.readthedocs.io/en/stable/command_line.html#incremental-mode)
- pytest 默认发现 `test_*.py` / `*_test.py`；`python -m pytest` 与 `pytest` 几乎等价，但会把当前目录加入 `sys.path`。默认 `cacheprovider` 会写 `.pytest_cache`，可用 `-p no:cacheprovider` 禁用；`PYTHONDONTWRITEBYTECODE=1` 避免 import 写 `__pycache__`。这些选项不能限制测试代码本身的副作用。[pytest invocation](https://docs.pytest.org/en/stable/how-to/usage.html) · [pytest cache](https://docs.pytest.org/en/stable/how-to/cache.html)

### GitHub Actions 与 mise 锁定建议

- 项目既然由 mise 管理环境，`mise.toml` 应 exact pin `python = "3.14.7"` 与 `uv = "0.12.4"`，并可设置 `UV_PYTHON = { value = "{{ tools.python.path }}", tools = true }`，让 uv 明确使用 mise 管理的解释器。存在 `uv.lock` 时，mise 也能识别 uv 项目及其 `.venv`，但自动创建/激活环境是可选设置，不应替代显式 locked sync。[mise Python](https://mise.jdx.dev/lang/python.html)
- workflow 可沿用单一 setup path：`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`，再用 `jdx/mise-action@3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518 # v4.2.5`、显式 `version: 2026.8.5` 安装项目工具，最后只调用串行的 `mise run ci`。这避免再用另一 action 重复安装 uv。[mise CI](https://mise.jdx.dev/continuous-integration.html) · [mise-action v4.2.5](https://github.com/jdx/mise-action/releases/tag/v4.2.5)
- 若未来放弃 mise 管理 uv，Astral 官方推荐 `setup-uv`；核对日最新是 `astral-sh/setup-uv@ae62891fec2bb8e7d6c99fc78c9fec3a63790f8d # v10.0.0`，并应另设 `version: "0.12.4"`。这只是替代方案，不应与 mise path 同时生成。[uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/) · [setup-uv v10.0.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.0.0)

### Renovate 的 PEP 621 与 uv 支持

- Renovate 的 `pep621` manager 默认匹配 `pyproject.toml`，通过 PyPI datasource 提取 `requires-python`、`project.dependencies`、optional dependencies、PEP 735 `dependency-groups`、`build-system.requires` 与 `tool.uv.*`。[Renovate `pep621` manager](https://docs.renovatebot.com/modules/manager/pep621/)
- 仓库存在 `uv.lock` 时，Renovate 能识别 uv，更新正式、可选和开发依赖，并同时更新 `pyproject.toml` 与 `uv.lock`。`pep621` manager 也支持对 `uv.lock` 做 lockfile maintenance；该功能默认关闭，不是启用 uv dependency updates 的前提。[uv Renovate guide](https://docs.astral.sh/uv/guides/integration/renovate/) · [Renovate lock file maintenance](https://docs.renovatebot.com/modules/manager/pep621/#lock-file-maintenance)
- 首版 `.github/renovate.json` 仍可使用通用 `config:recommended`、semantic commits 与 `dependencies` label，不启用 automerge、auto-approve 或 lockfile maintenance；Python 的 `pyproject.toml` / `uv.lock` 不需要额外 custom manager。

### 文件副作用总结

| 操作                                     | 可预期副作用                                                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `uv init`                                | 写 project metadata、README、Python pin 与源码；默认还创建 Git repository，除非使用 `--vcs none`       |
| `uv lock`                                | 创建或更新 `uv.lock`；`uv lock --check` 不更新                                                         |
| `uv sync`                                | 可能更新 lockfile；创建/更新 `.venv` 和 uv cache；exact sync 默认移除环境中的 extraneous packages      |
| `uv run`                                 | 默认在执行任意项目命令前 lock/sync；被执行代码可有任意副作用                                           |
| `ruff format` / `ruff check --fix`       | 改写源码；check-only 命令不改源码，但默认 cache 策略仍需单独控制                                       |
| mypy / pytest                            | 默认分别写 `.mypy_cache`、`.pytest_cache`，import 还可能写 `__pycache__`；测试代码本身可产生任意副作用 |
| `uv build` / `python -m build`           | 写 `dist/`，创建临时 build environment/cache，并可能下载、构建和执行 backend requirements              |
| `jdx/mise-action` / `astral-sh/setup-uv` | 下载工具并写 runner tool/cache directories；二者应二选一                                               |

### 对 Skill 的建议

- 项目形态必须先确认：packaged application/CLI、unpackaged application、library 的结构与 build 要求不同。首版若只承诺 library 与 CLI，应把两者都映射到 uv 0.12 的 packaged templates，并为生成源码补真实 pytest smoke test。
- uv、Ruff、mypy、pytest 与 build 都是 Skill 的**有意生态基线**，不能表述为 Python 官方默认。既有项目若已采用 Poetry、PDM、Hatch、Black、Pyright 等方案，应在写入前进入 migration conflict，而不是静默并存。

## Go

### 核对日版本与原生骨架边界

- Go 官方下载 JSON 在核对日把 **go1.26.6** 标为 stable；Lefthook 官方 latest release 是 **v2.1.10**。两者都只是核对日快照，生成时仍应解析后写 exact pin。[Go Download JSON](https://go.dev/dl/?mode=json) · [Lefthook v2.1.10](https://github.com/evilmartians/lefthook/releases/tag/v2.1.10)
- `go mod init [module-path]` 只在当前目录初始化并写入新的 `go.mod`；现有 `go.mod` 会导致失败。module path 是发布与 import identity，不应从任意目录名静默猜测。[Go Modules Reference](https://go.dev/ref/mod#go-mod-init)
- Go 官方教程对 library 与 executable 都先运行 `go mod init`，再由作者创建 `.go` source；可执行命令必须使用 `package main`。因此 Go 没有类似 `--lib` / `--bin` 的官方源码脚手架，library 的 package、CLI 的 `main.go` 与 smoke test 都属于 Skill 模板，而不是 `go mod init` 的输出。[Create a Go module](https://go.dev/doc/tutorial/create-module) · [How to Write Go Code](https://go.dev/doc/code)
- 最小 library 可在 module root 提供一个非 `main` package 和对应 `_test.go`；最小 CLI 可在 root 提供 `package main`、`func main()` 与同 package smoke test。官方只在同时包含 library 与 commands 或有多个 commands 时推荐 `cmd/<name>/`，这仍是 layout convention，不是 `go mod init` 的默认输出。[Organizing a Go module](https://go.dev/doc/modules/layout)

### 格式、分析、测试与构建

- `gofmt -w` 会覆盖不合规 source；Go 1.26.6 的 `gofmt -d` 输出 diff、不改 source，并在格式不同时通过 `errFormattingDiffers` 返回退出码 1。`gofmt -l` 只列文件，不具备这个差异退出码语义。[gofmt command](https://pkg.go.dev/cmd/gofmt) · [Go 1.26 `gofmt` source](https://go.dev/src/cmd/gofmt/gofmt.go)
- `go vet` 报告编译器未必捕获的可疑结构；命中问题或调用错误时返回非零，但官方明确说明它依赖 heuristics，不能证明程序正确。[`cmd/vet`](https://pkg.go.dev/cmd/vet)
- `go test ./...` 会为每个 package 编译并运行独立 test binary，并在构建测试时运行一组高置信度 vet checks；package-list mode 会缓存成功结果。测试代码本身是可执行代码，可能写任意文件、访问网络或启动子进程。[`go` command: test](https://pkg.go.dev/cmd/go)
- `go build` 会编译 packages 与 dependencies，但不 install。直接构建单个 `main` package 时，默认会把 executable 写到当前目录；构建多个 packages 或单个非-main package 时结果通常只进入 build cache/临时目录。若门禁必须保证仓库无 binary artifact，应显式 `-o` 到临时目录，而不是仅凭 `./...` 推断无写入。[`go` command: build](https://pkg.go.dev/cmd/go)
- module-aware 的 build/test/vet 默认通常按 `-mod=readonly` 工作；显式设置该值会在需要改 `go.mod` 时失败，但仍可能下载依赖并写 module cache。`-mod=mod` 可更新 `go.mod`，`go mod tidy` 会增删 `go.mod` requirements 与 `go.sum` entries；Go 1.26 的 `go mod tidy -diff` 才是只输出必要 metadata diff、差异时非零的只读门禁。[Go Modules Reference](https://go.dev/ref/mod#build-commands) · [`go mod tidy`](https://go.dev/ref/mod#go-mod-tidy)

建议的公共任务边界是：本地修复用 `gofmt -w .`；CI 串行执行 `gofmt -d .`、`go mod tidy -diff`、`go vet -mod=readonly ./...`、`go test -mod=readonly ./...`，并让 build task 把 `go build -mod=readonly -o <temporary-directory>/ ./...` 的产物放到仓库外。临时目录的创建和删除应由确定性 helper 负责，不能把 shell-specific `$TMPDIR` 直接固化为跨平台契约。

### mise、Lefthook 与 GitHub Actions 锁定

- `mise.toml` 应 exact pin `go = "1.26.6"` 与 `lefthook = "2.1.10"`，并生成、提交 `mise.lock`；`go = "1.26"` 在 mise 中表示该 minor line 的最新版本，不是 exact patch。Go 自身的 `GOTOOLCHAIN=auto` 还可能依据 `go.mod` 的 `go` / `toolchain` directive 查找或下载较新 toolchain；若基线要求只运行 mise pin，应设置 `GOTOOLCHAIN = "local"`，让不兼容约束直接失败。[mise Go](https://mise.jdx.dev/lang/go.html) · [mise lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html) · [Go Toolchains](https://go.dev/doc/toolchain)
- `lefthook install` 会把配置的 hooks 安装进 `.git/hooks/`；修改 `lefthook.yml` 后无需重装。`stage_fixed` 默认 `false`，设为 `true` 会自动 `git add` formatter 处理过的文件，因此有部分暂存安全要求的基线不应启用它，仍需在 formatter 前拒绝同文件 staged/unstaged overlap。[Lefthook install](https://lefthook.dev/usage/commands/install/) · [`stage_fixed`](https://lefthook.dev/configuration/stage_fixed/)
- workflow 可使用唯一 setup path：`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`，再用 `jdx/mise-action@3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518 # v4.2.5`、显式 `version: 2026.8.5` 安装项目工具，最后只调用 `mise run ci`；存在 `mise.lock` 时 action 会执行 locked install。无需再加入 `actions/setup-go` 形成第二套 Go 安装来源。[checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) · [checkout pinned commit](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1) · [mise-action v4.2.5](https://github.com/jdx/mise-action/releases/tag/v4.2.5) · [mise-action pinned commit](https://github.com/jdx/mise-action/commit/3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518) · [mise v2026.8.5](https://github.com/jdx/mise/releases/tag/v2026.8.5)

### Renovate 的 Go、mise 与 Actions 支持

- `gomod` manager 默认匹配所有 `go.mod`，提取 `go`、`toolchain`、direct/indirect requirements、replacements 与 Go 1.24+ `tool` dependencies。它默认不升级表示最低兼容版本的 `go` directive，但会跟踪表示建议精确工具链的 `toolchain` directive；普通 dependency update 可更新 `go.sum` artifact。[Renovate `gomod`](https://docs.renovatebot.com/modules/manager/gomod/)
- `mise` manager 默认匹配标准 `mise.toml` 变体，能提取 `[tools]` / task tools，并在存在 `mise.lock` 时更新 locked version。它支持 `mise.lock` 的 lockfile maintenance，但要求已有 lockfile，并通过受 Renovate execution/trust policy 约束的外部 `mise` 命令执行。[Renovate `mise`](https://docs.renovatebot.com/modules/manager/mise/)
- `github-actions` manager 默认匹配 `.github/workflows/*.yml` 等 workflow/action 文件，能更新 `uses:` 中的 action refs 与 digest；完整 SHA 后必须保留 `# v7.0.1` 一类可识别版本注释，裸 SHA 默认不会获得版本更新。这样既保持不可变执行目标，也让 updater 保留版本意图。[Renovate `github-actions`](https://docs.renovatebot.com/modules/manager/github-actions/)
- `lockFileMaintenance` 全局默认关闭，支持清单包含 `mise.lock`，不包含 `go.sum`；因此关闭它不妨碍常规 Go dependency PR 更新 `go.mod`/`go.sum`。首版 `.github/renovate.json` 应保持 `{ "lockFileMaintenance": { "enabled": false } }`，不要把 `go.sum` 描述为 Go lockfile。[Renovate lock file maintenance](https://docs.renovatebot.com/configuration-options/#lockfilemaintenance)

### 文件副作用总结

| 操作                                                | 受版本控制文件与其他磁盘副作用                                                                                                                                          |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `go mod init` / `go mod tidy`                       | 分别创建 `go.mod`，或更新 `go.mod` / `go.sum`；`go mod tidy -diff` 只读 metadata，但解析过程仍可能使用网络和 module cache                                               |
| `gofmt -w` / `go fmt`                               | 改写 source；`gofmt -d` 对 source 只读，Go 1.26 在差异时返回 1                                                                                                          |
| `go vet -mod=readonly ./...`                        | 对 project metadata/source 只读；会编译分析并写 build/module cache，cgo 或外部 build tools 可能引入额外副作用                                                           |
| `go test -mod=readonly ./...`                       | 对 metadata 默认只读，但写 build/module/test cache；测试代码可产生任意副作用                                                                                            |
| `go build -mod=readonly ...`                        | 写 build/module cache；单个 `main` package 默认还可能在当前目录写 executable，显式 `-o` 到仓库外才能控制 artifact 位置                                                  |
| `mise install` / `lefthook install` / `mise run ci` | 前者下载工具并写 mise data/cache；Lefthook 写 `.git/hooks/`；CI 又会产生上述 Go cache、临时 build artifact 与测试自身副作用                                             |
| `actions/checkout` / `jdx/mise-action`              | checkout 写 runner workspace；mise-action 下载 action、mise 与项目工具并写 runner tool/cache directories。workflow 不改 project source 不等于 runner 文件系统完全无写入 |

### 对 Skill 的建议

- 先确认 module path 与 library/CLI 形态，再运行 exact mise Go 下的 `go mod init` 并生成无业务语义的 source 与真实 smoke test。既有 `go.mod`、`go.work`、`.go-version`、asdf 或自定义 build system 应先进入保留/冲突判断，不能重新初始化或静默增加第二个版本来源。
- hook 只承担快速 staged formatter 与只读 vet；完整 test/build 留给公共 mise tasks 和 CI。部分暂存 guard 必须先于 formatter，formatter 只处理并重新暂存精确的 staged `.go` 文件，避免把同文件未暂存内容带入 commit。

## Issue #6：Zig 项目基线工具链核验

本节只服务于 `bootstrap-project` 的 Zig vertical slice。版本和 moving tag 的解析结果是 **2026-08-14 快照**；实现中应保留版本刷新入口，不能把本节当作永久最新值。

### 版本快照与 Zig 命令语义

- Zig 官网 Download 页面把 development build `master` 与 tagged release 分开列出；核对日最新稳定 tagged release 是 **0.16.0**，发布日期为 2026-04-13。[Zig Downloads](https://ziglang.org/download/) · [0.16.0 release notes](https://ziglang.org/download/0.16.0/release-notes.html)
- `zig init` 在当前目录创建 `build.zig`、`build.zig.zon`、`src/main.zig`、`src/root.zig`；当前官方输出没有 library/CLI 形态参数，而是同时生成 executable 和 library 示例。0.16.0 源码另提供 `--minimal`，只生成 ZON 和最小 `build.zig`，它同样不是 library/CLI shape selector。[Zig Overview](https://ziglang.org/learn/overview/) · [Zig 0.16.0 CLI source](https://codeberg.org/ziglang/zig/src/tag/0.16.0/src/main.zig) · [official init template](https://codeberg.org/ziglang/zig/src/tag/0.16.0/lib/init/build.zig)
- `zig fmt` 会原地修改源码；`zig fmt --check .` 是不覆盖源码的格式门。`zig build` 执行 `build.zig` 声明的 DAG，默认 main step 是 Install step；被安装的 artifact 通常写到 `zig-out/`，构建缓存写到 `.zig-cache/`。[Zig 0.16.0 Language Reference](https://ziglang.org/documentation/0.16.0/) · [Build System: Installing Build Artifacts](https://ziglang.org/learn/build-system/#Installing-Build-Artifacts)
- `zig test foo.zig` 会编译并运行该 source file 的 test declarations。构建脚本中的测试则分为 Compile 和 Run 两步；如果没有用 `addRunArtifact` 建立运行边，测试只被编译而不会执行。因此 `zig build test` 是否真正运行测试取决于项目的 `build.zig`。[Build System: Testing](https://ziglang.org/learn/build-system/#Testing)

**工程建议：** 新项目可先运行官方 `zig init`，再按已确认的 library 或 CLI 形态窄幅清理另一套示例；既有项目不得重新运行 initializer。生成的 `build.zig` 必须让 `test` step 依赖 `addRunArtifact`，并以真实 smoke test 证明 runner 被执行。

### mise 项目工具、任务与 CI 语法

- 核对日 mise 最新 release 是 **2026.8.5**；`mise.toml` 的 `[tools]` 表用于声明项目工具，例如 `zig = "0.16.0"` 和 `lefthook = "2.1.10"`。`mise use` 会安装工具并创建或修改项目 `mise.toml`；直接编辑配置后运行 `mise install`，工具会被下载、解压或编译到 mise data directory，默认是 `~/.local/share/mise/installs/`。[mise latest release API](https://api.github.com/repos/jdx/mise/releases/latest) · [Dev Tools](https://mise.jdx.dev/dev-tools/) · [`mise install`](https://mise.jdx.dev/cli/install.html)
- TOML task 的当前语法是 `[tasks.<name>]` 加 `run = "..."`，入口为 `mise run <name>`。`depends = [...]` 会先调度依赖，mise 会在可能时并行执行依赖；因此它表达依赖关系，不保证列表逐项串行。[Tasks](https://mise.jdx.dev/tasks/) · [Task Configuration: `depends`](https://mise.jdx.dev/tasks/task-configuration.html#depends) · [`mise run`](https://mise.jdx.dev/cli/run.html)
- `run` 也可接受 command/task-reference 数组；数组元素顺序执行，任一失败即停止，`{ task = "test" }` 可调用另一个 task，而 `{ tasks = ["lint", "test"] }` 才显式并发。这是需要确定顺序的 `ci` 聚合入口。[Task Configuration: `run`](https://mise.jdx.dev/tasks/task-configuration.html#run) · [TOML Tasks: Run command](https://mise.jdx.dev/tasks/toml-tasks.html#run-command)
- 未做 shell activation 时仍可用 `mise exec -- <command>` 或 `mise run <task>` 获得项目工具环境；这适合 Skill 和 CI，且不需要静默修改用户的 shell rc 文件。[Getting Started](https://mise.jdx.dev/getting-started.html)

**工程建议：** Skill 直接结构化写入 `[tools]` 和 `[tasks]`，不调用会隐式修改 global config 的 `mise use --global`。Zig slice 的公共入口应为 `format`、`format-check`、`lint`、`check`、`test`、`build`、`ci`；每个任务必须执行真实命令。`ci` 应只调用不会改写受版本控制文件的任务，不能调用 `format`；使用 `run = [{ task = "format-check" }, ...]` 明确串行、失败即停，不用会自动并行调度的 `depends` 表达质量门顺序。

### Lefthook 的 staged 文件、重暂存与执行顺序

- 核对日 Lefthook 最新 release 是 **2.1.10**。`lefthook install` 会在配置不存在时创建空的 `lefthook.yml`，并把已配置 hooks 安装到 `.git/hooks/`；修改配置后无需重新安装，因为 hook 每次运行都会读取配置。非 npm 安装方式在 clone 后需要显式执行 `lefthook install`；随后可用 `lefthook check-install` 验证，已安装且同步返回 `0`，缺失或需同步返回 `1`。[Lefthook latest release API](https://api.github.com/repos/evilmartians/lefthook/releases/latest) · [`lefthook install`](https://lefthook.dev/usage/commands/install/) · [`lefthook check-install`](https://lefthook.dev/usage/commands/check-install/) · [What is Lefthook?](https://lefthook.dev/)
- `{staged_files}` 会展开为当前准备提交的文件；`{files}` 则来自 hook-level 或 command-level 自定义 `files` shell command。文件列表过长时 Lefthook 会拆成多条命令顺序执行；给模板加引号会影响每个路径的 quoting。[`run`](https://lefthook.dev/configuration/run/) · [hook-level `files`](https://lefthook.dev/configuration/files-global/)
- `stage_fixed` 默认是 `false`，只对 `pre-commit` 生效。设为 `true` 后，Lefthook 在 command/script 完成后自动调用 `git add`：有 command-level `files` 时使用其结果，否则使用 `{staged_files}`，并继续应用 `glob`/`exclude` filters。[`stage_fixed`](https://lefthook.dev/configuration/stage_fixed/)
- Lefthook 默认顺序执行 commands/scripts，`parallel: true` 才并发；需要可审计顺序时可用 `priority`，其中正整数按升序执行，未设置或 `0` 的项最后执行。新的 `jobs` 列表也会按声明顺序追加 unnamed jobs，`piped: true` 可显式表达串行流水线。[`parallel`](https://lefthook.dev/configuration/parallel/) · [`priority`](https://lefthook.dev/configuration/priority/) · [`jobs`](https://lefthook.dev/configuration/jobs/)

**工程推论与建议：** `stage_fixed` 最终调用 `git add`，所以同一文件同时存在 staged 与 unstaged 修改时，它可能把原本未暂存的工作区内容一并加入提交。Skill 必须在 formatter 之前检测这种 partial-staging 情况并中止；不能把 `stage_fixed: true` 本身当作保护。pre-commit 应显式串行化为“partial-stage guard → staged formatter + `stage_fixed` → staged lint → project-level quick check”，不要只依赖 YAML map 的视觉顺序，也不要设置 `parallel: true`。

### GitHub Actions 中的 mise

- mise 的 CI 文档推荐使用项目维护方提供的 `jdx/mise-action`，它负责安装 mise 和配置声明的工具。该页面的示例仍显示 `@v3`，但 action 官方仓库当前 README 已使用 `@v4`；v4 release notes 说明 v3 使用的 Node.js 20 runtime 已被 GitHub 弃用，应迁移到 Node.js 24 runtime 的 v4。[mise Continuous Integration](https://mise.jdx.dev/continuous-integration.html) · [mise-action README](https://github.com/jdx/mise-action/blob/main/README.md) · [mise-action v4.0.0](https://github.com/jdx/mise-action/releases/tag/v4.0.0)
- 核对日 `mise-action` 最新 release 是 **v4.2.5**；official moving tag `v4` 与 `v4.2.5` 都解析到完整 commit SHA **`3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518`**。[latest release API](https://api.github.com/repos/jdx/mise-action/releases/latest) · [`v4` Git ref API](https://api.github.com/repos/jdx/mise-action/git/ref/tags/v4) · [resolved commit](https://github.com/jdx/mise-action/commit/3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518)
- action 的当前默认值是安装 latest mise、运行 `mise install`、启用 mise cache，并把工具环境提供给后续 steps；因此即使 workflow 本身不改源码，setup step 也会下载 action、mise 和工具，并写 runner tool/cache 目录。[mise-action `action.yml`](https://github.com/jdx/mise-action/blob/v4.2.5/action.yml) · [mise-action README](https://github.com/jdx/mise-action/blob/v4.2.5/README.md)
- GitHub 安全文档称 full-length commit SHA 是引用 action 的唯一 immutable release 方式；tag 可移动。GitHub 同时提醒，固定 SHA 不会自动获得更新。[GitHub Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions)

**工程建议：** 生成 `uses: jdx/mise-action@3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518 # v4.2.5`，并显式设置 `version: 2026.8.5`，随后只运行与本地相同的 `mise run ci`。SHA 和注释必须成对保留，便于 Renovate 的 `github-actions` manager 跟踪 tag。

### Renovate 的配置位置与 managers

- `.github/renovate.json` 是 Renovate 官方支持的 repository config 位置；典型起点是 `{"extends":["config:recommended"]}`。提交配置文件不会替用户安装或授权 GitHub App，自托管实例也必须由管理员把仓库纳入运行范围。[Installing and Onboarding: Configuration location](https://docs.renovatebot.com/getting-started/installing-onboarding/#configuration-location) · [Shareable Config Presets](https://docs.renovatebot.com/config-presets/)
- `mise` manager 默认识别 `mise.toml` 等标准路径，读取顶层 `[tools]` 和 `tasks.*.tools`。其当前 registry snapshot 明确把 `zig` 标为受支持的 short name；因此 Zig compiler pin 通过 `mise` manager 更新。[Renovate `mise` manager](https://docs.renovatebot.com/modules/manager/mise/)
- 当前官方 managers 清单没有 Zig 或 `build.zig.zon` 原生 manager；所以不能把“Renovate 能更新 `mise.toml` 中的 Zig”扩大成“Renovate 能管理 ZON package dependencies”。后者若进入范围，需要单独设计和验证 custom manager。[Renovate Managers](https://docs.renovatebot.com/modules/manager/)
- `github-actions` manager 默认扫描 `.github/workflows/**/*.yml|yaml` 等 workflow/action 文件。对 `uses:` 的 SHA pin，只要旁边保留版本 tag 注释，它会按该 tag 更新 commit SHA；没有版本注释的 bare SHA 默认禁用更新，因为 Renovate 无法判断其所属 tag/branch。[Renovate `github-actions` manager](https://docs.renovatebot.com/modules/manager/github-actions/)
- mise lockfile maintenance 可能运行 `mise lock --bump`，官方把它放在 unsafe execution 边界：self-hosted 管理员需显式允许 `mise`，且现有 `mise.lock` 是前提。[Renovate `mise` manager: Lock file support](https://docs.renovatebot.com/modules/manager/mise/#lock-file-support)

**工程建议：** 初始 `.github/renovate.json` 使用 `config:recommended`、semantic commits 和 `dependencies` label；不启用 automerge、auto-approve、schedule 或 lockfile maintenance。GitHub Action 仍由 workflow 中的 SHA + tag comment 表达，不需要额外 manager 配置。Skill 只写配置文件并报告“Renovate 尚未授权”，不得声称 bot 已启用。

### 副作用总表

| 操作                                             | 可预期副作用                                                                                  |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `zig init`                                       | 创建或写入 build manifest 与 `src/` 示例                                                      |
| `zig fmt .`                                      | 改写 Zig 源码                                                                                 |
| `zig fmt --check .`                              | 不改源码；读取 source tree                                                                    |
| `zig build` / 正确连接的 `zig build test`        | 写 `.zig-cache/`；build 通常写 `zig-out/`；test/build steps 可执行项目代码                    |
| `mise install`                                   | 下载、解压或编译工具到 mise data/cache；不负责修改 shell rc                                   |
| `mise run <task>`                                | 运行 task 声明的任意命令；可能自动准备工具，副作用由 task 和 tool installer 决定              |
| `lefthook install`                               | 配置缺失时创建空 config；写 `.git/hooks/`                                                     |
| `stage_fixed: true`                              | 对筛选后的文件调用 `git add`，改变 index                                                      |
| `jdx/mise-action`                                | 下载 action、mise 与工具，写 runner cache/tool directories，并把环境提供给后续 workflow steps |
| 提交 `.github/renovate.json`                     | 只增加仓库配置；不会自动安装或授权 Renovate，是否运行取决于已安装 App 或 self-hosted 调度     |
| Renovate mise lockfile maintenance（若显式启用） | 可执行 `mise lock --bump` 并更新 `mise.lock`；属于受管理员控制的 unsafe execution             |

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

- Issue #6 已核验 Zig 所需的 mise、Lefthook、GitHub Actions 和 Renovate 边界；其他技术栈的 package manager（npm/pnpm/yarn/bun）、Python manager/backend、framework initializer 组合仍需在相应 vertical slice 实现前另行调查。
- 没有在五种最新工具链上逐一执行所有命令并记录精确生成文件快照；initializer 模板和 CLI 参数仍须由实现测试锁定，并在版本升级时刷新 fixture。
- 没有证明任一测试命令对运行环境无副作用。测试、build script、lifecycle script、generator 与 compiler plugin 都能运行项目代码；Skill 只能保护自身生成的命令和版本控制文件边界。
- TypeScript 7.0 的 compiler API 生态仍处过渡期；实现前必须重新检查 `typescript-eslint`、framework 和 bundler 的官方兼容范围。
