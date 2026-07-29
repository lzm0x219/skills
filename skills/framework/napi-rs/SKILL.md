---
name: napi-rs
description: "使用 napi-rs 构建、修改、调试、测试、打包或评审 Rust Node-API addon。适用于接入或迁移、#[napi] 导出、Rust/JavaScript 类型转换、class、函数、错误、buffer、生命周期、异步与线程、CLI、打包、交叉编译、WebAssembly、兼容性、测试、发布与故障排查。涉及版本 API、CLI 参数、目标支持或发布行为时，先查当前 napi-rs 官方文档。"
---

# napi-rs 通用工作流

使用当前项目的语言、包管理器和构建约定完成 Rust Node-API addon 工作；不要假定某个仓库、crate 名称、领域模型、测试数据或发布平台。请求与 Rust、Node-API 或 napi-rs 无关时，直接完成原任务，不要输出本 Skill 的流程或术语。

## 先确定边界

1. 检查现有 Rust crate、Node 包、构建脚本、支持矩阵和用户授权。不要因为使用本 Skill 而擅自脚手架、迁移、发布或修改公共 API。
2. 先定义 JavaScript 合约：导出名称、参数和返回值、同步或异步语义、错误形状、生成的 `.d.ts`、模块加载方式和兼容承诺。
3. 如果项目已有独立核心 crate，将 Node-API 代码保持为薄适配层；不要把业务规则、I/O 策略或领域模型复制进绑定层。独立 addon 不必为了套用该模式额外拆 crate。

## 使用当前官方文档

1. 对不熟悉或版本敏感的任务，先读 [官方文档清单](references/official-documentation-inventory.md)，再打开触及能力的官方页面。
2. 涉及 CLI、Cargo feature、目标平台、WASI、发布或迁移时，始终以当前官方页面为准；不要从本 Skill 推断精确参数、版本或支持矩阵。
3. 仅在刷新清单或声称本地资料仍全覆盖时，运行 `node scripts/verify-official-docs-coverage.mjs --check`；发布前或文档刷新时再加 `--verify-links`。

| 工作内容 | 优先查阅的官方主题 |
| --- | --- |
| 接入已有项目、创建包、使用 `napi` CLI | Introduction、CLI |
| `#[napi]`、函数、class、enum、类型声明、错误 | Exports and JavaScript API |
| 值转换、`Env`、`this`、引用、buffer、Promise、生命周期 | Values, conversion, and lifetime management |
| `async fn`、`AsyncTask`、线程回调、Tokio | Async and concurrency |
| Cargo feature、预编译产物、交叉编译、WASI | Build, targets, and WebAssembly |
| 运行时加载、bundler、测试、崩溃或平台故障 | Quality, integrations, and troubleshooting |
| 版本、制品、npm 发布或 v2/v3 迁移 | Release, migration, and historical context |

按实际触及的能力组合阅读页面。例如，异步导出 `TypedArray` 时，同时阅读 async、typed array、lifetime、error handling 与 export/type conversion 页面。

## 保持边界安全

- 在 JavaScript 边界验证输入、路径、选项组合和资源上限；保持导出名、`.d.ts`、loader 与 `package.json` 一致。
- 将可预期错误映射为稳定、可操作且机器可读的 JavaScript 错误；默认不要暴露凭据、绝对路径或原始内部错误。
- 仅在其 `Env` 与生命周期内使用 Node-API 句柄和借用的 JavaScript 值。不要将它们保存到长期 Rust 状态，也不要跨 worker 或线程发送。
- 不要在 JavaScript 主线程执行耗时的 CPU、文件系统、网络或外部进程工作。按当前官方指导选择 `async fn`、`AsyncTask` 或 `ThreadsafeFunction`，并只把拥有所有权的 Rust 数据交给后台工作。
- 除非公共合约另有规定，不要在绑定层改变核心层提供的确定性顺序、精度或错误分类。

## 实现与验证

1. 在项目配置的 Rust 命令存在时，运行格式化、Clippy 和 Rust 测试；不要凭空要求某种 workspace 结构。
2. 用项目配置的 napi CLI 或当前官方文档中的命令构建产物。以 Node 集成测试从最终包导入 addon，覆盖至少一个成功路径、一个无效输入或预期错误路径，以及所有新异步行为。
3. 只有同时具备生成的制品和干净环境中的实际导入测试，才声称支持某个 Node.js、OS、CPU、libc、运行时或 WASI 组合。Node-API ABI 兼容本身不足以证明可用。
4. 将跨平台、loader、bundler 或性能结论与实际测试矩阵区分开；未跑的组合保持为未验证。
5. 将 `napi pre-publish`、`napi prepublish`、npm publish、GitHub release 和制品上传视为外部副作用。没有用户的明确授权，不运行它们。

## 本地资源

- [官方文档清单](references/official-documentation-inventory.md)：当前官方 Docs/Blog 的能力路由和范围说明。
- [覆盖验证器](scripts/verify-official-docs-coverage.mjs)：比对本地清单与官方 `llms.txt`/sitemap，并可验证链接可达性。
