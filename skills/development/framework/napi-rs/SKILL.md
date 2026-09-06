---
name: napi-rs
description: 使用 napi-rs 构建、修改、调试、测试、打包或审查 Rust Node-API addon。适用于接入或迁移、#[napi] 导出、Rust/JavaScript 类型转换、类、函数、错误、buffer、生命周期、异步与线程、CLI、打包、交叉编译、WebAssembly、兼容性、测试、发布和故障排查。涉及版本化 API、CLI 参数、目标支持或发布行为时，先查阅当前 napi-rs 官方文档。
---

# napi-rs 通用工作流

按当前项目的语言、包管理器和构建约定完成 Rust Node-API addon 工作。不要假定特定仓库、crate 名称、领域模型、测试数据或发布平台。请求与 Rust、Node-API 或 napi-rs 无关时，直接完成原任务，不输出本 Skill 的流程或术语。

## 先确定边界

1. 检查既有 Rust crates、Node packages、构建脚本、支持矩阵和用户授权。不要只因使用本 Skill 就脚手架化、迁移、发布或改变公开 API。
2. 先定义 JavaScript 契约：导出名称、参数与返回值、同步或异步语义、错误形状、生成的 `.d.ts`、模块加载和兼容性承诺。
   同时从 Cargo manifest／lockfile 与 Node package／lockfile 确定 `napi`、`napi-derive`、`@napi-rs/cli` 和 Node 版本；官网当前示例与项目版本不匹配时，查对应发布记录、版本源码或已安装包，不自动升级来迁就示例。
3. 项目已有独立 core crate 时，让 Node-API 代码保持为薄适配层。不要把业务规则、I/O 策略或领域模型复制进绑定层；独立 addon 不需要为此额外拆 crate。

## 使用当前官方文档

1. 对陌生或版本敏感任务，先阅读 [官方文档清单](references/official-documentation-inventory.md)，再打开所用能力的官方页面。
2. 涉及 CLI、Cargo features、目标平台、WASI、发布或迁移时，始终以当前官方页面为准。不要从本 Skill 推断精确参数、版本或支持矩阵。
3. 只有在刷新清单或声称本地材料仍完整覆盖官方站点时，才运行 `node scripts/verify-official-docs-coverage.mjs --check`；发布前或文档刷新后再加 `--verify-links`。

| 工作                                                          | 优先官方主题               |
| ------------------------------------------------------------- | -------------------------- |
| 接入现有项目、创建 package、使用 `napi` CLI                   | Introduction、CLI          |
| `#[napi]`、函数、类、enum、类型声明、错误                     | Exports 与 JavaScript API  |
| 值转换、`Env`、`this`、references、buffers、Promise、生命周期 | Values、转换与生命周期管理 |
| `async fn`、`AsyncTask`、线程回调、Tokio                      | 异步与并发                 |
| Cargo features、预构建产物、交叉编译、WASI                    | 构建、目标与 WebAssembly   |
| 运行时加载、bundler、测试、崩溃或平台失败                     | 质量、集成与故障排查       |
| 版本、artifacts、npm publish 或 v2/v3 migration               | 发布、迁移与历史背景       |

只读取实际触及能力对应的页面。例如，导出异步 `TypedArray` 时，还应读取异步、typed array、生命周期、错误处理和导出／类型转换页面。

涉及大整数转换、共享 Buffer、取消／背压，或最终 package 的验收时，读取 [边界决策与回归](references/boundary-decisions.md) 中对应小节。

## 保持边界安全

- 在 JavaScript 边界验证输入、路径、选项组合和资源上限，并保持导出名、`.d.ts`、loader 与 `package.json` 一致。
- 将预期错误映射为稳定、可操作、机器可读的 JavaScript errors；默认不暴露凭据、绝对路径或原始内部错误。
- scoped Node-API handles 与借用的 JavaScript values 仅在其 `Env` 和生命周期内使用；跨调用保留值时选择版本支持的 reference wrapper，并在所属环境释放。保持存活不等于隔离可变内存；跨线程前另行证明所有权与同步，不能把 `Send` 当作共享字节安全证明。
- 不在 JavaScript main thread 上进行昂贵的 CPU、文件系统、网络或外部进程工作。按当前官方指引选择 `async fn`、`AsyncTask` 或 `ThreadsafeFunction`，并只将拥有所有权的 Rust 数据交给后台工作。
- 除非公开契约另有说明，不要在绑定层改变 core layer 提供的确定性顺序、精度或错误分类。

## 实施与验证

按改动选择验证，完成仓库必需检查。纯文档改动运行文档检查；代码、绑定或打包变化执行下列适用检查。通过后，仅因新修改、失败或未解决疑点扩大或重复验证。

1. Rust 代码变化且项目已配置对应命令时，运行格式化、Clippy 和受影响的 Rust tests；不要虚构不存在的 workspace 结构。
2. 改动影响 JavaScript 可观察行为、绑定或打包时，用项目配置的 napi CLI 或当前官方文档命令构建 artifacts。通过 Node integration tests 从最终 package 导入 addon，覆盖受影响的成功路径、无效输入或预期错误路径，以及每个新增异步行为。
3. 只有在干净环境中同时拥有生成产物和真实导入测试时，才声称支持某个 Node.js、OS、CPU、libc、runtime 或 WASI 组合。仅有 Node-API ABI 兼容性不足以证明支持。
4. 将跨平台、loader、bundler 或性能结论与实际测试矩阵分开；未运行组合保持未验证。
5. 将 `napi pre-publish`、`napi prepublish`、npm publish、GitHub releases 和 artifact uploads 视为外部副作用。未经用户明确授权不得执行。

## 本地资源

- [官方文档清单](references/official-documentation-inventory.md)：当前官方 Docs／Blog 页面的能力路由与范围说明。
- [覆盖验证器](scripts/verify-official-docs-coverage.mjs)：将本地清单与官方 `llms.txt`／sitemap 比较，也可验证链接可达性。
