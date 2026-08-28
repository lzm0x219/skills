# 已有 Zig 基线适配器

此适配器仅适用于已存在的单 package Zig library，且目标是 Git repository 的精确根目录。在每一项 preflight check 通过前，inventory 保持只读。

## 已识别输入

当前适配器要求常规的 `build.zig.zon`、`build.zig`、`src/root.zig`、`mise.toml` 和 `lefthook.yml` 文件。它保留项目名称、source tree、build graph、README，以及已有的精确 Zig 与 Lefthook pins。

`mise.toml` 中的 Zig 版本必须等于 `build.zig.zon` 中的 `.minimum_zig_version` 和 `mise.lock` 中的任何 Zig 条目。已有 Lefthook lock entries 必须与其 mise pin 匹配。不一致属于 conflict，而非版本选择机会。

build script 必须已经将其 `test` step 连接到 `addRunArtifact`。适配器不会改写已有 build graph。其只编译的 `check` task 使用 `zig test --test-no-exec -fno-emit-bin src/root.zig`；需要 dependency injection、不同 root 或 generated inputs 的项目不属于此范围。

## 冲突边界

出现下列任一项时，在写入前停止：

- asdf `.tool-versions`、Volta configuration、Husky、pre-commit 或未识别的已有 pre-commit hook；
- 非目标本地 `.git/hooks` 的自定义 `core.hooksPath`；
- 未知或冲突的必需 mise tasks；
- 除精确已识别的 parallel formatter-plus-test legacy shape 或生成的 ordered shape 外的 Lefthook content；
- symlink、非普通文件，或内容不同的已有 CI、Renovate、partial-stage guard 目标；
- 目标不是精确 Git root，或 linked worktree 的 metadata 位于目标之外。

一起报告所有检测到的冲突。不得对存在未解决冲突的目标进行部分迁移。

## 运行适配器

在仓库外给报告指定新的路径：

```sh
python3 <skill-directory>/scripts/baseline_existing_zig.py \
  --target <absolute-repository-root> \
  --report <absolute-report-path>
```

随后适配器：

1. 仅通过已识别的 mise settings structure 添加 `lockfile = true`；
2. 保留兼容 tasks，并补充缺失的 `format`、`format-check`、`lint`、`check`、`test`、`build` 和串行 `ci` task tables；
3. 仅将精确已识别的 legacy Lefthook file 替换为有序的部分暂存防护、暂存 formatter 及重新暂存、暂存 lint、再到快速 compile check；
4. 仅创建缺失且已知的 CI、Renovate、partial-stage guard 与 lockfile 路径；
5. 执行 `mise install`，将 Lefthook 安装到目标本地 hooks directory，然后执行 `mise run ci`；
6. 比较变更前后的 manifests，拒绝意外变更，并验证保留的 project-file hashes。

操作具备幂等性：对完成基线再次运行不会产生 tracked-content changes。

## 解读失败

`blocked` 表示 preflight 在写入前发现版本、工具、结构、目标路径或 repository-boundary conflict。 `partial` 表示已知变更开始后安装、hook setup、validation 或 postcondition 失败。保留部分证据；存在时指出精确失败命令，并提供针对性的恢复步骤。
