# Zig 项目初始化适配器

此适配器仅适用于 macOS 或 Linux 上，在不存在或为空的目标目录中新建单 package Zig library 或 CLI。

## 确定输入

写入前记录绝对目标路径、小写项目标识符、形态和精确版本。版本优先级为用户明确选择，其次是已有约束，最后是执行当日从权威来源验证的当前稳定版本。

随包基线于 2026-08-14 验证：Zig `0.16.0`、Lefthook `2.1.10`、mise `2026.8.5`、`actions/checkout` `v7.0.1` 和 `jdx/mise-action` `v4.2.5`。这只是带日期的证据，而不是永久默认值。选择当前版本时，重新检查官方 Zig、Lefthook、mise 与 action 的发行来源。

项目名称必须匹配 `[a-z][a-z0-9_]*`。如果所需显示名称不匹配，应询问 package identifier，不要静默改写。

## 运行适配器

在目标目录之外创建新的报告路径，然后运行：

```sh
python3 <skill-directory>/scripts/bootstrap_zig.py \
  --target <absolute-target> \
  --name <project_identifier> \
  --shape <library|cli> \
  --zig-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

不要预先在目标目录中创建文件。适配器会在运行 Git 或 mise 前拒绝非空目标。

适配器按以下边界执行：

1. `git init`，不创建 commit；
2. 渲染公共基线并创建 `mise.lock`；
3. 在目标范围内设置 `MISE_TRUSTED_CONFIG_PATHS` 后执行 `mise install`；
4. 在以项目命名的临时子目录中执行 `mise exec -- zig init`，验证其恰好四个文件的输出，并保留 fingerprint；
5. 渲染选定的 library 或 CLI build 与 smoke-test 源码；
6. 将版本锁定的 hook installer 运行到目标本地 `.git/hooks`；
7. 执行 `mise run ci`。

项目名称初始化目录很重要，因为 Zig 会根据 package name 验证 package fingerprint。不得在无关目录中运行 initializer 后仅替换 `.name`。

## 生成的基线

两种形态都会获得：

- `mise.toml` 与 `mise.lock` 中的精确 Zig、Lefthook pins；
- 真正的 `format`、`format-check`、`lint`、`check`、`test`、`build` 和串行 `ci` tasks；
- 连接到 `addRunArtifact` 的 test step，使测试实际执行而不只是编译；
- 有序的 Lefthook jobs：部分暂存防护、暂存的 `zig fmt` 及显式重新暂存、暂存的逐文件 `zig ast-check`、`mise run check`；
- README、ignore rules、EditorConfig、使用不可变 action SHA 的 Ubuntu GitHub Actions workflow，以及 `.github/renovate.json`；
- 不创建 license、contribution guide、commit、push、外部 App 授权、automerge 或 lockfile maintenance。

installer 会验证 Lefthook 生成的 hook，加入 `--no-stage-fixed`，并将 `MISE_TRUSTED_CONFIG_PATHS` 限定为该 hook 进程的 repository root，不持久化全局信任。formatter helper 从 Git index 读取 NUL 分隔路径，为 formatter arguments 加上 `./` 前缀，并且只重新暂存这些精确文件。因此部分暂存防护在任何 formatter 前运行，并拒绝 index 与 worktree 列都发生变化的 tracked file。

## 解读报告

`completed` 表示完整适配器和 `mise run ci` 成功。 `partial` 表示目标可能包含有用输出，但 initializer、install、hook 或 validation command 失败。 `blocked` 表示 validation 在受支持的 initialization 能够开始前已停止。

出现 `partial` 时，报告精确的 `failed_command`，保留目标供检查，并提供针对该命令的重试或恢复步骤。不要声称完成，也不要自动删除部分目标。
