# 技术栈证据

仅当用户未明确指定技术栈，或必须检查已有目标是否存在冲突证据时，才阅读本参考。

## 证据优先级

优先采用已提交的 manifests 与 toolchain constraints，而非源码扩展名、文档散文、生成缓存、已安装 hooks 或目录名。manifest 是某个技术栈的证据；它本身不能证明是 library 还是 CLI/application。

| 技术栈             | 主要证据                                       | 形态证据                                                                              |
| ------------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| Zig                | `build.zig.zon`、`build.zig`                   | 导出的 modules 表明 library；已安装的 executable artifact 表明 CLI/application        |
| Rust               | `Cargo.toml`、可选的 `rust-toolchain.toml`     | `[lib]` 或 `src/lib.rs` 表明 library；`[[bin]]` 或 `src/main.rs` 表明 CLI/application |
| TypeScript/Node.js | `package.json`、`tsconfig.json`、pnpm lockfile | `exports` 表明 library；`bin` 表明 CLI/application                                    |
| Python             | `pyproject.toml`、uv lockfile                  | import package metadata 表明 library；project scripts 表明 CLI/application            |
| Go                 | `go.mod`                                       | 可 import packages 表明 library；`package main` 表明 CLI/application                  |

## 歧义规则

- 除非用户指定目标 subproject，否则将来自不同技术栈的两个主要 manifests 视为歧义。
- 将多个 workspace members、packages 或 modules 视为需要精确目标的 monorepo 边界。
- README 声明仅为辅助证据。
- 识别技术栈时，忽略 build outputs、caches、virtual environments、vendored dependencies 和生成的 hook shims。
- 即使存在更新稳定版本也保留已声明版本；报告主要 manifests 与 environment-manager pins 的不一致。
