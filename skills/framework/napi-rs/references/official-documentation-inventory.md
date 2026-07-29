# napi-rs 官方文档能力全覆盖清单

> 检索快照：2026-07-29（Asia/Shanghai）。此清单是任务路由和覆盖审计用的页面目录，不是 API 语法的离线副本；实现时仍须打开对应的官方页面确认当前版本细节。

## 权威入口与抓取方法

- 官网的 [robots.txt](https://napi.rs/robots.txt) 指向 [sitemap.xml](https://napi.rs/sitemap.xml)。本次以 sitemap、官网侧栏和逐页 HTTP `200` 交叉核对：Docs 有 **50** 个英文 canonical 页面，简体中文与 pt-BR 各有同一组 **50** 个本地化页面，即 **150** 条 Docs URL。
- 官方的机器可读入口是 [llms.txt](https://napi.rs/llms.txt)；它按站点导航列出 Docs、Blog 和 Changelog，适合在文档刷新时重新发现页面。
- 结构性来源为 napi-rs 维护的 [website 仓库](https://github.com/napi-rs/website)：快照中的 [Docs 导航元数据](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json) 定义 6 个 Docs 分区，且 [导航生成器](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs) 明确以英文结构为三种语言生成侧栏。完整来源目录见 [content/docs](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs) 与 [content/blog](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog)。

### 路由规则与计数

- 下文列出 **50 个英文 canonical Docs URL** 和 **3 个英文 canonical Blog URL**；每一条 URL 都是一个单独的能力/主题入口。
- 每一个下列 Docs path 都有英文 `https://napi.rs/docs/` 前缀，并对应 `https://napi.rs/cn/docs/` 与 `https://napi.rs/pt-BR/docs/` 前缀的本地化页面；本地化页面不算新增能力，故不重复列出 100 条镜像 URL。此规则由 [官网路由生成逻辑](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-route-map.mjs) 和 [Docs 导航生成器](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs) 共同定义。
- `https://napi.rs/docs` 本身不是主题页；以实际叶子路由为准。页面的 `.md` 表示是同一页面的机器可读表示，而非额外能力页，见 [sitemap 生成器](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/generate-sitemap.mjs)。

## 分类、纳入策略与完整页面映射

纳入策略含义：**核心** = 长期不易漂移、应浓缩为 skill 的安全边界/工作流；**主题参考** = 按任务加载的本地参考索引，不能取代官网；**在线查阅** = 强依赖版本、CLI 参数、目标平台或发布副作用，动手前必须打开官网。

### 1. 入门与项目接入（3 页；核心 + 主题参考）

核心保留“薄 Node 适配层、先定义 JS 合约、不要在未授权时脚手架/发布”的流程；模板步骤和依赖版本按任务在线确认。

- [Getting started](https://napi.rs/docs/introduction/getting-started) — 使用模板创建、构建并测试 napi-rs v3 包。
- [Build your first package](https://napi.rs/docs/introduction/simple-package) — 完成首个包的构建、测试和发布前准备。
- [Manual setup](https://napi.rs/docs/introduction/manual-setup) — 在既有 Rust crate、JavaScript 包或 workspace 中手工接入 napi-rs。

### 2. JavaScript 导出与公共 API（11 页；主题参考）

这些页决定 Rust/JS 公共契约、生成的 TypeScript 和错误语义；skill 核心只保留“先写契约、稳定命名、错误可分类”的约束，属性组合和转换规则必须按页在线查阅。

- [Exports](https://napi.rs/docs/concepts/exports) — 控制 Rust 函数、类和常量导出到 JavaScript 的方式。
- [Module Initialization](https://napi.rs/docs/concepts/module-init) — 在 Node 加载原生模块时执行自定义初始化。
- [Naming conventions](https://napi.rs/docs/concepts/naming-conventions) — 规定 Rust 与 JavaScript 的名称转换规则。
- [`#[napi]` attributes](https://napi.rs/docs/concepts/napi-attributes) — 参考所有公开的 `napi-derive` 属性及其运行时和 TypeScript 影响。
- [Class](https://napi.rs/docs/concepts/class) — 将 Rust `struct` 定义和导出为 JavaScript class。
- [Enum](https://napi.rs/docs/concepts/enum) — 映射 Rust enum 与 JavaScript 字符串联合或数值 enum。
- [Object](https://napi.rs/docs/concepts/object) — 在 Rust 与 Node 间传递普通 JavaScript object。
- [Function](https://napi.rs/docs/concepts/function) — 定义、接收和调用 JavaScript function 值。
- [Error handling](https://napi.rs/docs/concepts/error-handling) — 处理同步/异步 API 的抛出、拒绝、保留和分类错误。
- [Types Overwrite](https://napi.rs/docs/concepts/types-overwrite) — 覆盖自动生成的 TypeScript 声明。
- [Type conversions](https://napi.rs/docs/concepts/type-conversions) — 说明转换矩阵、方向、所有权和所需 feature。

### 3. 值、内存、生命周期与低层 Node-API（11 页；主题参考，涉及句柄时在线查阅）

skill 核心应强制“不要把 Node-API 句柄或借用的 JS 值存入 Rust 状态或跨线程发送”；具体 trait、生命周期、`Env` API、零拷贝与 feature 要求只以官方当前页为准。

- [Values](https://napi.rs/docs/concepts/values) — 提供 Rust 与 JavaScript 值之间的高层转换入口。
- [TypedArray](https://napi.rs/docs/concepts/typed-array) — 处理 JavaScript TypedArray 原语与 Rust 数据。
- [Understanding Lifetime](https://napi.rs/docs/concepts/understanding-lifetime) — 解释 JavaScript 值与 Rust 借用边界的生命周期。
- [`Reference` / `WeakReference`](https://napi.rs/docs/concepts/reference) — 创建和使用对象强/弱引用。
- [External](https://napi.rs/docs/concepts/external) — 用 JavaScript object 承载 Rust native value 的 `External`。
- [Env](https://napi.rs/docs/concepts/env) — 访问低层 Node-API 环境、值创建、清理与内存接口。
- [Inject Env](https://napi.rs/docs/concepts/inject-env) — 向导出函数和方法注入 Node-API `Env`。
- [Inject This](https://napi.rs/docs/concepts/inject-this) — 向绑定 API 注入 JavaScript `this` receiver。
- [Cargo features](https://napi.rs/docs/concepts/cargo-features) — 选择 Node-API level、async、转换、诊断和兼容 feature。
- [Promise](https://napi.rs/docs/concepts/promise) — 在 Rust 侧表示和等待 JavaScript Promise。
- [Iterators and async iterators](https://napi.rs/docs/concepts/iterators) — 实现 Generator 与 AsyncGenerator 的 JavaScript 迭代协议。

### 4. 异步、线程与并发（4 页；核心 + 主题参考）

核心应固定“不能阻塞 JavaScript 主线程、只把 owned Rust 数据送往 worker、从非 JS 线程回调必须使用受支持的机制”；runtime、取消和 shutdown 细节需读本组完整页面。

- [async fn](https://napi.rs/docs/concepts/async-fn) — 用 Tokio runtime 执行导出的 Rust `async fn`。
- [AsyncTask](https://napi.rs/docs/concepts/async-task) — 在 libuv 线程池执行任务，并处理 `AbortSignal` 取消。
- [ThreadsafeFunction](https://napi.rs/docs/concepts/threadsafe-function) — 从其他线程安全调用 JavaScript callback。
- [Async and concurrency](https://napi.rs/docs/more/async-concurrency) — 选择 API、取消、JS 访问、worker 和 runtime shutdown 的安全边界。

### 5. CLI、构建产物与发布（13 页；主题参考 + 在线查阅）

CLI 选项、生成模板、平台包布局、npm 权限和 GitHub release 都可能随版本变化；核心仅保留“测试声称支持的运行时、发布命令需显式授权、发布不是事务”的安全规则。执行前必须在线打开触及的页面。

- [New](https://napi.rs/docs/cli/new) — 从维护的 Yarn/pnpm 模板创建项目。
- [Rename](https://napi.rs/docs/cli/rename) — 重命名项目和相关生成资产。
- [Build](https://napi.rs/docs/cli/build) — 使用 `napi build`、跨编译 flags、实际构建命令和环境。
- [NAPI Config](https://napi.rs/docs/cli/napi-config) — 配置构建、生成绑定、targets 和 WASI 输出。
- [Programmatic API](https://napi.rs/docs/cli/programmatic-api) — 通过 `@napi-rs/cli` 的编程 API 定制构建。
- [Create npm directories](https://napi.rs/docs/cli/create-npm-dirs) — 创建平台 npm 包目录。
- [Artifacts](https://napi.rs/docs/cli/artifacts) — 将 CI 构建产物收集到平台包。
- [Universalize](https://napi.rs/docs/cli/universalize) — 合并为 universal binary。
- [Version packages](https://napi.rs/docs/cli/version) — 更新已创建平台包的版本。
- [Pre Publish](https://napi.rs/docs/cli/pre-publish) — 版本化、发布并附加平台包；这是具网络和 registry 副作用的操作。
- [Release native packages](https://napi.rs/docs/deep-dive/release) — 解释多平台包的构建、验证、发布和部分失败恢复。
- [Native module](https://napi.rs/docs/deep-dive/native-module) — 解释 native module 的含义以及 Node 的加载/执行方式。
- [WebAssembly and WASI](https://napi.rs/docs/concepts/webassembly) — 构建、打包、测试并运行 Node/浏览器的 WASI fallback。

### 6. 目标平台与交叉编译（3 页；在线查阅）

目标三元组、glibc、SDK、链接器、Node-API ABI 和持续测试矩阵均是时效性事实；不能把它们冻结在 skill 里。

- [Cross build](https://napi.rs/docs/cross-build) — 提供 host/target 决策矩阵、target 配方、glibc、C/C++ 依赖和 Docker 镜像迁移。
- [Support and compatibility](https://napi.rs/docs/more/support-compatibility) — 区分 Node-API ABI、受测运行时和 napi-rs target 支持。
- [Cross-build FAQ](https://napi.rs/docs/more/faq) — 汇总常见交叉编译和 native loading 问题。

### 7. 测试、集成与故障诊断（3 页；核心 + 主题参考）

核心应要求 Rust 测试、Node 导入集成测试和每个声称支持平台的实际运行验证；具体 bundler、框架、调试器与错误症状按页查阅。

- [Testing and debugging](https://napi.rs/docs/more/testing-debugging) — 测试 Rust/JavaScript 边界的 addon，并在 Node 中调试 native code。
- [Integrations and bundlers](https://napi.rs/docs/more/integrations) — 在 CJS、ESM、bundler、framework、Electron 和 serverless 中加载 addon。
- [Troubleshooting](https://napi.rs/docs/more/troubleshooting) — 从失败层向外诊断 build、loader、platform、TypeScript、async 与 WASI。

### 8. 迁移与背景（3 个 Docs 页面 + 3 个 Blog 页面；在线查阅）

这部分用于版本升级、旧项目兼容和理解不安全旧 API 的来源；不能替代当前 `Concepts & reference` 页面。

- [V2 to V3 Migration Guide](https://napi.rs/docs/more/v2-v3-migration-guide) — 说明 napi-rs v2 到 v3 的配置、CLI、类型和兼容迁移。
- [History](https://napi.rs/docs/deep-dive/history) — 介绍 Node 原生 addon 的发展背景。
- [Functions and Callbacks in NAPI-RS](https://napi.rs/blog/function-and-callbacks) — 解释函数与 callback 绑定的背景和模式。
- [Announcing NAPI-RS v3](https://napi.rs/blog/announce-v3) — 记录 v3 的生命周期、ThreadsafeFunction 和迁移背景。
- [Announcing NAPI-RS v2](https://napi.rs/blog/announce-v2) — 记录 v2 的历史变更背景。

## 覆盖完整性与已知限制

### 已证实的覆盖

- 本文件逐条列出了官方 Docs 侧栏的 **50/50** 个英文 canonical 页面：Introduction 3、Concepts & reference 26、CLI 10、Deep dive 3、Cross build 1、Guides & help 7；分区及顺序可由 [Docs 元数据](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json) 复核。
- 本文件也逐条列出了官方 Blog 导航的 **3/3** 篇页面；这是 [Blog 元数据](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog/_meta.en.json) 当前公开的完整条目。
- 因而目录覆盖的是当前官网公开的可执行能力文档：**53/53** 个 canonical Docs/Blog 路由；Docs 的 100 个本地化镜像按相同路由规则覆盖。页面发现的实时入口仍是 [llms.txt](https://napi.rs/llms.txt)。

### 边界与刷新规则

- Changelog 是按版本罗列的历史发布记录，而非稳定的能力参考；需要确认某个 crate/CLI 版本变化时，从官方 [Changelog](https://napi.rs/changelog/napi) 在线进入，不将其压缩进 skill 的行为规则。
- 此清单不复制 Rust API 的全部函数签名，也不保证某项功能在你的 Node、CPU、libc、WASI runtime 或 CLI 版本可用；这正是应在任务时在线查阅“Cargo features”“Support and compatibility”“Cross build”以及相关 CLI 页的原因。
- 官网增加、删除、重命名页面或修改导航后，53 的计数会失效。刷新时以 [llms.txt](https://napi.rs/llms.txt)、[sitemap.xml](https://napi.rs/sitemap.xml) 和官方 [website 源码](https://github.com/napi-rs/website) 重新枚举，逐一保留 canonical HTTPS URL，并在链接可达后才重新声称“全覆盖”。
