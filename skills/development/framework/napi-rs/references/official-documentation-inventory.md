# napi-rs 官方文档完整覆盖清单

> 快照：2026-07-29（Asia/Shanghai）。此清单是供任务路由和覆盖审计使用的页面目录，不是 API 语法的离线副本。实现时仍须打开对应官方页面，确认当前版本细节。

## 权威入口与采集方法

- 官方站点的 [robots.txt](https://napi.rs/robots.txt) 指向 [sitemap.xml](https://napi.rs/sitemap.xml)。本快照交叉检查 sitemap、站点侧边栏和逐页 HTTP `200` 响应：Docs 有 **50** 个英文规范页面；简体中文与 pt-BR 分别拥有相同的 **50** 个本地化页面，Docs URL 共 **150** 个。
- 官方机器可读入口为 [llms.txt](https://napi.rs/llms.txt)。它按照站点导航列出 Docs、Blog 和 Changelog，适合在刷新文档时重新发现页面。
- 结构来源于 napi-rs 维护的 [website repository](https://github.com/napi-rs/website)：快照中的 [Docs navigation metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json) 定义了 6 个 Docs sections，而 [navigation generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs) 按英文结构为三种语言生成 sidebars。完整源码树：[content/docs](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs) 和 [content/blog](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog)。

### 路由规则与数量

- 下文列出 **50 个英文规范 Docs URL** 与 **3 个英文规范 Blog URL**；每个 URL 都是独立的能力/主题条目。
- 下列每个 Docs path 都带有英文 `https://napi.rs/docs/` 前缀，并在 `https://napi.rs/cn/docs/` 与 `https://napi.rs/pt-BR/docs/` 下有对应本地化页面。本地化页面不是额外能力，因此不重复列出这 100 个镜像 URL。此规则由 [official route-map generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-route-map.mjs) 和 [Docs navigation generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs) 共同定义。
- `https://napi.rs/docs` 本身不是主题页面；应使用实际 leaf routes。页面的 `.md` 形式是同一页面的机器可读表示，而不是额外能力页面；参见 [sitemap generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/generate-sitemap.mjs)。

## 分类、纳入策略与完整页面图

纳入策略含义：**core** = 应浓缩进 Skill 的持久安全边界/工作流；**topic reference** = 按任务加载的本地参考索引，不替代官方网站；**online lookup** = 强烈依赖版本、CLI、目标或发布；执行前打开官方页面。

### 1. 入门与项目采用（3 页；core + topic reference）

保留“薄 Node adapter、先定义 JS contract、未经授权不 scaffold/publish”的核心流程。每项任务都在线确认 template steps 和 dependency versions。

- [Getting started](https://napi.rs/docs/introduction/getting-started) — 从 template 创建、构建和测试 napi-rs v3 package。
- [Build your first package](https://napi.rs/docs/introduction/simple-package) — 完成第一个 package 的构建、测试和 pre-publish 准备。
- [Manual setup](https://napi.rs/docs/introduction/manual-setup) — 在已有 Rust crate、JavaScript package 或 workspace 中手动采用 napi-rs。

### 2. JavaScript 导出与公共 API（11 页；topic reference）

这些页面决定 Rust/JS 公共 contract、生成的 TypeScript 与错误语义。Skill 核心仅保留“先写 contract、稳定命名、错误可分类”；attribute combinations 和 conversion rules 必须按页面在线查询。

- [Exports](https://napi.rs/docs/concepts/exports) — 控制 Rust functions、classes 和 constants 如何导出到 JavaScript。
- [Module Initialization](https://napi.rs/docs/concepts/module-init) — Node 加载 native module 时运行自定义初始化。
- [Naming conventions](https://napi.rs/docs/concepts/naming-conventions) — 定义 Rust 与 JavaScript 之间的名称转换规则。
- [`#[napi]` attributes](https://napi.rs/docs/concepts/napi-attributes) — 参考全部公共 `napi-derive` attributes 及其 runtime 和 TypeScript 影响。
- [Class](https://napi.rs/docs/concepts/class) — 将 Rust `struct` 定义并导出为 JavaScript class。
- [Enum](https://napi.rs/docs/concepts/enum) — 将 Rust enums 映射为 JavaScript string unions 或 numeric enums。
- [Object](https://napi.rs/docs/concepts/object) — 在 Rust 与 Node 之间传递 plain JavaScript objects。
- [Function](https://napi.rs/docs/concepts/function) — 定义、接收和调用 JavaScript function values。
- [Error handling](https://napi.rs/docs/concepts/error-handling) — 处理同步/异步 API 的 thrown、rejected、retained 和可分类 errors。
- [Types Overwrite](https://napi.rs/docs/concepts/types-overwrite) — 覆盖生成的 TypeScript declarations。
- [Type conversions](https://napi.rs/docs/concepts/type-conversions) — 说明 conversion matrix、方向、所有权和必需 features。

### 3. 值、内存、生命周期与底层 Node-API（11 页；topic reference；涉及 handles 时 online lookup）

Skill 核心应强制“不得将 Node-API handles 或借用的 JS values 存入 Rust state，也不得跨 threads 发送”。具体 traits、lifetimes、`Env` APIs、zero-copy 行为和 feature requirements 仅以当前官方页面为准。

- [Values](https://napi.rs/docs/concepts/values) — Rust 与 JavaScript values 的高层转换入口。
- [TypedArray](https://napi.rs/docs/concepts/typed-array) — 操作 JavaScript TypedArray primitives 与 Rust data。
- [Understanding Lifetime](https://napi.rs/docs/concepts/understanding-lifetime) — 解释 JavaScript values 的 lifetimes 与 Rust borrow boundaries。
- [`Reference` / `WeakReference`](https://napi.rs/docs/concepts/reference) — 创建并使用强/弱 object references。
- [External](https://napi.rs/docs/concepts/external) — 在 JavaScript objects 上通过 `External` 携带 Rust native values。
- [Env](https://napi.rs/docs/concepts/env) — 访问底层 Node-API environment、value creation、cleanup 和 memory interfaces。
- [Inject Env](https://napi.rs/docs/concepts/inject-env) — 将 Node-API `Env` 注入导出 functions 和 methods。
- [Inject This](https://napi.rs/docs/concepts/inject-this) — 将 JavaScript `this` receiver 注入绑定 API。
- [Cargo features](https://napi.rs/docs/concepts/cargo-features) — 选择 Node-API level、async、conversion、diagnostic 和 compatibility features。
- [Promise](https://napi.rs/docs/concepts/promise) — 在 Rust 中表示并 await JavaScript Promise。
- [Iterators and async iterators](https://napi.rs/docs/concepts/iterators) — 实现 Generator 与 AsyncGenerator 的 JavaScript iteration protocols。

### 4. 异步、线程与并发（4 页；core + topic reference）

核心应固定“不得阻塞 JavaScript main thread、只向 workers 发送拥有所有权的 Rust data、非 JS-thread callbacks 使用受支持机制”。runtime、cancellation 和 shutdown 细节需要阅读本组完整页面。

- [async fn](https://napi.rs/docs/concepts/async-fn) — 在 Tokio runtime 上运行导出的 Rust `async fn`。
- [AsyncTask](https://napi.rs/docs/concepts/async-task) — 在 libuv thread pool 上运行工作，并处理 `AbortSignal` cancellation。
- [ThreadsafeFunction](https://napi.rs/docs/concepts/threadsafe-function) — 从其他 threads 安全调用 JavaScript callbacks。
- [Async and concurrency](https://napi.rs/docs/more/async-concurrency) — 为 cancellation、JS access、workers 和 runtime shutdown 选择 API 与安全边界。

### 5. CLI、构建产物与发布（13 页；topic reference + online lookup）

CLI options、生成 templates、platform package layout、npm permissions 和 GitHub releases 会随版本改变。核心仅保留“测试声称支持的 runtimes、publishing commands 需要明确授权、publish 不具事务性”。执行前在线打开触及的页面。

- [New](https://napi.rs/docs/cli/new) — 从维护的 Yarn/pnpm templates 创建 project。
- [Rename](https://napi.rs/docs/cli/rename) — 重命名 project 与相关生成 assets。
- [Build](https://napi.rs/docs/cli/build) — 使用 `napi build`、cross-compile flags、实际 build commands 与 environment。
- [NAPI Config](https://napi.rs/docs/cli/napi-config) — 配置 builds、生成 bindings、targets 和 WASI output。
- [Programmatic API](https://napi.rs/docs/cli/programmatic-api) — 通过 `@napi-rs/cli` 的 programmatic API 自定义 builds。
- [Create npm directories](https://napi.rs/docs/cli/create-npm-dirs) — 创建 platform npm package directories。
- [Artifacts](https://napi.rs/docs/cli/artifacts) — 将 CI build artifacts 收集到 platform packages。
- [Universalize](https://napi.rs/docs/cli/universalize) — 合并为 universal binary。
- [Version packages](https://napi.rs/docs/cli/version) — 更新创建出的 platform packages 的版本。
- [Pre Publish](https://napi.rs/docs/cli/pre-publish) — 对 platform packages 执行版本、发布和附加；具有 network 和 registry side effects。
- [Release native packages](https://napi.rs/docs/deep-dive/release) — 说明多平台 package 构建、验证、发布和 partial-failure recovery。
- [Native module](https://napi.rs/docs/deep-dive/native-module) — 说明 native module 是什么以及 Node 如何加载/运行它。
- [WebAssembly and WASI](https://napi.rs/docs/concepts/webassembly) — 构建、打包、测试并运行 Node/browser WASI fallbacks。

### 6. 目标平台与交叉编译（3 页；online lookup）

target triples、glibc、SDKs、linkers、Node-API ABI 和 continuous test matrices 是时效性事实。不得固化进 Skill。

- [Cross build](https://napi.rs/docs/cross-build) — host/target decision matrix、target recipes、glibc、C/C++ dependencies 和 Docker image migration。
- [Support and compatibility](https://napi.rs/docs/more/support-compatibility) — 区分 Node-API ABI、已测试 runtimes 与 napi-rs target support。
- [Cross-build FAQ](https://napi.rs/docs/more/faq) — 常见 cross-compile 与 native loading 问题。

### 7. 测试、集成与排障（3 页；core + topic reference）

核心应要求每个声称支持的平台都具备 Rust tests、Node import integration tests 和真实 runtime verification。具体 bundlers、frameworks、debuggers 与 error symptoms 按页面查询。

- [Testing and debugging](https://napi.rs/docs/more/testing-debugging) — 测试 Rust/JavaScript boundary 的 addons，并在 Node 中调试 native code。
- [Integrations and bundlers](https://napi.rs/docs/more/integrations) — 在 CJS、ESM、bundlers、frameworks、Electron 和 serverless 中加载 addons。
- [Troubleshooting](https://napi.rs/docs/more/troubleshooting) — 按失败层次从外向内诊断 build、loader、platform、TypeScript、async 和 WASI。

### 8. 迁移与背景（3 个 Docs 页面 + 3 个 Blog 页面；online lookup）

此节用于版本升级、legacy project compatibility，以及理解较旧 unsafe APIs 的起源。它不替代当前 Concepts 与 reference pages。

- [V2 to V3 Migration Guide](https://napi.rs/docs/more/v2-v3-migration-guide) — 从 napi-rs v2 到 v3 的 configuration、CLI、type 与 compatibility migration。
- [History](https://napi.rs/docs/deep-dive/history) — Node native addon 演进的背景。
- [Functions and Callbacks in NAPI-RS](https://napi.rs/blog/function-and-callbacks) — function 和 callback bindings 的背景与模式。
- [Announcing NAPI-RS v3](https://napi.rs/blog/announce-v3) — 记录 v3 的 lifetime、ThreadsafeFunction 与 migration 背景。
- [Announcing NAPI-RS v2](https://napi.rs/blog/announce-v2) — 记录 v2 变更的历史背景。

## 覆盖完整性与已知限制

### 已验证覆盖

- 本文件枚举官方 Docs sidebar 中全部 **50/50** 个英文规范 Docs 页面：Introduction 3、Concepts & reference 26、CLI 10、Deep dive 3、Cross build 1、Guides & help 7。可根据 [Docs metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json) 重新检查 sections 与顺序。
- 还枚举官方 Blog navigation 中全部 **3/3** 个页面；这正是 [Blog metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog/_meta.en.json) 中完整的公开集合。
- 因此目录覆盖当前公开可执行的能力文档：**53/53** 条规范 Docs/Blog routes。这 100 个 Docs localization mirrors 受相同路由规则覆盖。实时发现入口仍是 [llms.txt](https://napi.rs/llms.txt)。

### 边界与刷新规则

- Changelog 是带版本的历史发行日志，不是稳定能力参考。需要 crate/CLI 版本变更时，应从官方 [Changelog](https://napi.rs/changelog/napi) 在线进入；不要把它浓缩到 Skill 的行为规则中。
- 此清单不复制完整 Rust API function signatures，也不保证某 feature 在你的 Node、CPU、libc、WASI runtime 或 CLI 版本上可用。因此任务中应在线查阅 Cargo features、Support and compatibility、Cross build 和相关 CLI 页面。
- 官方站点添加、删除、重命名页面或改变 navigation 后，53 的计数即失效。刷新时，从 [llms.txt](https://napi.rs/llms.txt)、[sitemap.xml](https://napi.rs/sitemap.xml) 和官方 [website source](https://github.com/napi-rs/website) 重新枚举，逐个保留规范 HTTPS URLs；仅在链接可访问后再次声称完整覆盖。
