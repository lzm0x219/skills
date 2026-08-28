# Rust 项目初始化适配器

此 Rust 适配器适用于一个使用 edition 2024 的 Cargo package，可作为 library 或 CLI。新建模式仅接受不存在或为空的目标目录；已有模式仅接受带有仓库本地 `.git` 元数据的 Git 仓库精确根目录。

## 确定版本与形态

采用标准版本优先级：用户明确选择，其次是已有 Cargo 或 Rust toolchain 的精确约束，最后是执行当日从官方 Rust 来源验证的当前稳定版本。随包基线于 2026-08-14 验证：Rust `1.97.1`、Lefthook `2.1.10`、mise `2026.8.5`；这些值仅为带日期的证据。

新建模式要求小写 Cargo package 名、精确 Rust 和 Lefthook 版本，以及 `library` 或 `cli`。已有模式从 `Cargo.toml` 和 `src/lib.rs`/`src/main.rs` 推导名称、形态和 Rust 版本。已有 `rust-toolchain.toml` 或 `rust-toolchain` 仅当其精确 channel 与 Cargo 一致时才保留。

## 运行适配器

在目标目录之外使用新的报告路径：

```sh
python3 <skill-directory>/scripts/bootstrap_rust.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <package-name> \
  --rust-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

已有模式省略 `--name`，通常也省略 `--rust-version`；显式给出的版本必须与 Cargo 一致。 `--shape` 可选，但提供时必须一致。

新建模式初始化 Git 但不创建 commit，锁定本地 hooks path，安装 mise toolchain，运行官方 `cargo init --edition 2024 --vcs none`，验证其输出边界，再仅用选定的最小 templates 替换这些已知生成文件。

已有模式绝不运行 `cargo init`。它保留 `Cargo.toml`、存在时的 `Cargo.lock`、Rust 源码、README、toolchain files 和布局。仅当基线目标不存在或已逐字节一致时，才创建基线目标。asdf、Husky、pre-commit、冲突 toolchains、linked worktrees 和内容不同的基线文件均为阻塞冲突。

## 生成的质量基线

- `format`：`cargo fmt --all`；
- `format-check`：`cargo fmt --all --check`；
- `lint`：对所有 targets 与 features 运行 Clippy，并拒绝 warnings；
- `check`、`test`、`build`：针对所有 targets 和 features 使用 `--locked`；
- 串行 `ci`：format-check、lint、check、test，最后 build；
- pre-commit：`piped: true` 按失败即停顺序执行部分暂存防护、暂存 rustfmt 及显式重新暂存、项目 Clippy、再到快速 Cargo check；完整 test 和 build 不放入 hook。安装器向生成 hook 加入 `--no-stage-fixed` 和进程局部的 `MISE_TRUSTED_CONFIG_PATHS`，不持久化全局信任；formatter helper 从 Git index 读取 NUL 分隔路径；
- Ubuntu CI 通过相同的 `mise run ci` 入口、不可变 action SHA，以及对 mise、Cargo 和 Actions 的 Renovate 覆盖。

小型 libraries 保持扁平。新的 CLI project 将 `main.rs` 保持为薄输出边界，并把经测试的逻辑置于 `lib.rs`。单元测试放在 `#[cfg(test)]` 下，并使用描述行为的名称。

## 失败语义

`blocked` 表示目标、版本、VCS、tool-manager、Cargo、形态或目标路径冲突阻止了应用。 `partial` 表示已知写入或外部命令失败；保留报告、精确失败命令和部分变更。 `completed` 要求已安装 hook、已生成 lockfile、成功的完整质量门，以及新建模式下为空的 Git history。
