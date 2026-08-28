# Go 项目初始化适配器

此 Go 适配器适用于一个作为库或 CLI/应用的 Go module。新建模式仅接受不存在或为空的目标目录；已有模式仅接受带有仓库本地 `.git` 元数据的 Git 仓库精确根目录。

## 确定版本、模块与形态

采用标准版本优先级：用户明确选择，其次是已有仓库的精确约束，最后是执行当日从负责的官方来源验证的当前稳定版本。随包基线于 2026-08-14 验证：Go `1.26.6`、Lefthook `2.1.10`、mise `2026.8.5`；这些值仅为带日期的证据。

新建模式需要精确 Go 版本、精确 Lefthook 版本、有效 module path、小写项目名和 `library` 或 `cli`。已有模式保留 `go.mod` 中的 module path；其精确 Go 版本可来自用户明确选择、已有 mise pin、精确 `toolchain` directive 或 patch-level `go` directive。所有来源必须与 `go` directive 兼容。

## 运行适配器

在目标目录之外使用新的报告路径：

```sh
python3 <skill-directory>/scripts/bootstrap_go.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <project-name> \
  --module-path <module-path> \
  --go-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

已有模式省略 `--name` 和 `--module-path`；`--shape` 可选，但提供时必须一致。仅当已有仓库约束已识别并精确确定 Go 版本时，才可省略 `--go-version`。

新建模式初始化 Git 但不创建 commit，安装精确 mise 工具，调用官方 `go mod init`，验证它唯一新增的文件是 `go.mod`，写入选定的最小源码和测试骨架，运行 `go mod tidy`，安装 Lefthook，然后运行 `mise run ci`。

已有模式绝不运行 `go mod init`，绝不重写 `go.mod`、`go.sum`、源码、测试、README 或包布局，并将 `go mod tidy -diff` 作为只读模块检查。它只接受一个 module 和一个包边界。已识别的 CLI 由一个薄的 `cmd/<name>` 入口与可测试库包组成，这也防止单一 `main` 的 `go build` 将可执行文件写入仓库。Go workspace、嵌套 module、asdf、Husky、pre-commit、自定义 hooks 和未知基线目标均为阻塞冲突。

## 生成的质量基线

- `install`：`go mod download`；
- `format`：对所有非 vendored Go 源码递归执行 `gofmt -w`；
- `format-check`：对所有非 vendored Go 源码运行 `gofmt -d`，不修改文件；
- `check`：`go mod tidy -diff`；
- `lint`：`go vet -mod=readonly ./...`；
- `test`：`go test -mod=readonly -count=1 ./...`；
- `build`：针对库或多包薄 CLI 布局执行 `go build -mod=readonly ./...`，避免把可执行文件写入仓库；
- 串行 `ci`：install、模块检查、格式检查、vet、test，最后 build；
- pre-commit：`piped: true` 使部分暂存防护、暂存的 gofmt 与显式重新暂存、模块元数据检查、再到 vet 按失败即停顺序执行。完整 test 与 build 不放入 hook。版本锁定的安装器会验证 Lefthook 生成的 hook，加入官方 `--no-stage-fixed` 运行参数，并将 `MISE_TRUSTED_CONFIG_PATHS` 限定到该 hook 进程而不持久化全局信任；暂存辅助脚本直接从 Git index 读取 NUL 分隔路径；
- Ubuntu CI 通过相同的 `mise run ci` 入口、不可变 action SHA，以及对 mise、Go modules、Go directives 和 Actions 的 Renovate 覆盖。明确禁用 lockfile maintenance；`go.sum` 是校验和元数据，不是 lockfile maintenance 目标。

`GOTOOLCHAIN=local` 阻止隐式下载工具链，`GOWORK=off` 使边界保持在选定的单一 module。Go 命令仍使用仓库外的主机或 runner build、module 和临时缓存。

## 失败语义

`blocked` 表示目标、module、版本、VCS、manager、hook、形态、源码布局或目标路径冲突阻止了应用。 `partial` 表示已知写入或外部命令失败；保留报告、精确失败命令和部分变更。 `completed` 要求已安装 hook、精确 mise lock、整洁的 module、成功的完整质量门，以及新建模式下为空的 Git history。
