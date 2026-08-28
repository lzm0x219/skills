# TypeScript 与 Node.js 项目初始化适配器

此 Node 适配器适用于一个作为库或 CLI/应用的 ESM TypeScript package。新建模式仅接受不存在或为空的目标目录；已有模式仅接受带有仓库本地 `.git` 元数据的 Git 仓库精确根目录。

## 确定版本与形态

采用标准版本优先级：用户明确选择，其次是已有 package 的精确约束，最后是执行当日从负责的官方来源验证的当前稳定版本。随包基线于 2026-08-14 验证：Node.js LTS `24.19.0`、pnpm `11.21.0`、TypeScript `7.0.2`、Oxfmt `0.63.0`、Oxlint `1.78.0`、Vitest `4.1.10`、`@types/node` `24.13.3`、Lefthook `2.1.10` 和 mise `2026.8.5`；这些值仅为带日期的证据。

新建模式要求每个所列工具和依赖都有精确版本、有效的小写 npm package 名，以及 `library` 或 `cli`。已有模式从 `bin`、`exports` 和已识别的 `src` 布局推导形态，并保留兼容的 package scripts 与配置。精确的已有约束优先，且必须与任何显式参数一致。

## 运行适配器

在目标目录之外使用新的报告路径：

```sh
python3 <skill-directory>/scripts/bootstrap_node.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <package-name> \
  --node-version <x.y.z> \
  --pnpm-version <x.y.z> \
  --typescript-version <x.y.z> \
  --node-types-version <x.y.z> \
  --oxfmt-version <x.y.z> \
  --oxlint-version <x.y.z> \
  --vitest-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

已有模式省略 `--name`。仅当已识别 package metadata 中已有同一精确版本时，才可省略版本参数。 `--shape` 可选，但提供时必须一致。

新建模式初始化 Git 但不创建 commit，写入选定的最小 ESM skeleton，安装精确 mise 工具，创建 pnpm lockfile，再从该冻结 lockfile 安装，安装 Lefthook，并运行 `mise run ci`。Node 和 TypeScript 并未提供单一官方的 library/CLI scaffolder，因此适配器拥有并测试完整、已知的 template 边界。

已有模式保留源码、package scripts、README，以及兼容的 TypeScript、Oxc、Vitest 和 pnpm 配置。它只对缺失的精确 runtime 与 development dependency pins 执行结构化 package metadata merge。npm、Yarn、Bun、Volta、Husky、pre-commit、Prettier、ESLint 和 typescript-eslint 都是阻塞性迁移冲突，而不是静默替换对象。

## 生成的质量基线

- `format` 和 `format-check`：本地 Oxfmt；check mode 只读；
- `lint`：本地 Oxlint，启用 Vitest rules 并拒绝 warnings；
- `check`：NodeNext ESM 下严格的 `tsc --noEmit`；
- `test`：一次性 `vitest run`，测试导入的 API；
- `build`：TypeScript 输出 JavaScript、source maps 和 declarations；
- 串行 `ci`：冻结安装、format-check、lint、check、test，最后 build；
- pre-commit：`piped: true` 让部分暂存防护、暂存 Oxfmt 及只对这些文件的显式重新暂存、全项目 Oxlint、再到 type-check 按失败即停顺序执行；完整 tests 和 build 不放入 hook。Lefthook 将每次 `pre-commit` 运行视为暂存，并通常在任务前隐藏未暂存变更。版本锁定的安装器验证生成 hook，加入官方 `--no-stage-fixed` 运行参数，并将 `MISE_TRUSTED_CONFIG_PATHS` 限定到该 hook 进程而不持久化全局信任。formatter helper 随后直接从 Git index 读取 NUL 分隔路径，因此即使仓库尚无初始 commit，防护仍首先运行；
- Ubuntu CI 通过 `mise run ci`、不可变 action SHA，以及对 mise、npm/pnpm 和 Actions 的 Renovate 覆盖。

不会生成 Prettier、ESLint、typescript-eslint 或 `node:test` 的依赖、配置或命令。新的 CLI 保持 `src/cli.ts` 为薄输出边界，并将经测试的逻辑置于 `src/index.ts`。

## 失败语义

`blocked` 表示目标、package 边界、版本、VCS、manager、hook、形态或目标路径冲突阻止了应用。 `partial` 表示已知写入或外部命令失败；保留报告、精确失败命令和部分变更。 `completed` 要求已安装 hook、精确 mise 与 pnpm lockfiles、成功的完整质量门，以及新建模式下为空的 Git history。
