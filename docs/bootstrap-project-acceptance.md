# Bootstrap Project 跨技术栈验收记录

本文记录 `bootstrap-project` v1 在 2026-08-14 的确定性回归、真实工具链 smoke、平台边界和已知副作用。它是有日期的证据快照，不把模板存在或单次成功扩大为永久兼容保证。

## 五栈验收矩阵

| 技术栈                             | 新 library | 新 CLI | 既有项目                                          | 真实 smoke 证据                                                                                            |
| ---------------------------------- | ---------- | ------ | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Zig `0.16.0`                       | 通过       | 通过   | Ziwei 风格 fixture 通过且二次运行无受版本控制变更 | [PR #14](https://github.com/lzm0x219/skills/pull/14)、[PR #15](https://github.com/lzm0x219/skills/pull/15) |
| Rust `1.97.1`                      | 通过       | 通过   | library 保留 Cargo 与源码                         | [PR #16](https://github.com/lzm0x219/skills/pull/16)                                                       |
| Node.js `24.19.0` / pnpm `11.21.0` | 通过       | 通过   | ESM library 二次运行无受版本控制变更              | [PR #17](https://github.com/lzm0x219/skills/pull/17)                                                       |
| Python `3.14.7` / uv `0.12.4`      | 通过       | 通过   | packaged library 二次运行无受版本控制变更         | [PR #18](https://github.com/lzm0x219/skills/pull/18)                                                       |
| Go `1.26.6`                        | 通过       | 通过   | module 二次运行无受版本控制变更                   | [PR #19](https://github.com/lzm0x219/skills/pull/19)                                                       |

表中的“通过”包含适配器完成、`mise run ci` 成功、library/CLI smoke test 执行，以及 Git 历史仍为空。Node.js 使用 Oxfmt、Oxlint、TypeScript 和 Vitest；Python 使用 Ruff、mypy、pytest 和 build；Go 使用 gofmt、vet、test 和 build。Lefthook 固定为 `2.1.10`，本机 mise 为 `2026.8.5`。

真实 smoke 在临时项目中执行，不是只解析模板。Zig 与 Rust 的最终集成还验证了生成 hook 带 `--no-stage-fixed`：同一文件存在 staged 与 unstaged 修改时，guard 在 formatter 前失败；完整暂存后 hook 可通过。每个栈的离线单元测试使用假的外部命令边界验证精确 argv、失败状态和文件清单，不把 fake 运行称为真实工具链成功。

## 公共契约

五栈都提供有真实命令的 `format`、`format-check`、`lint`、`check`、`test`、`build` 和 `ci`。`ci` 不调用会改写源码的 `format`；它可以下载依赖，并可写忽略的 cache 或 build artifact。pre-commit 使用 `piped: true`，顺序为 partial-stage guard、只处理 index 路径的 formatter 与精确 restage、lint/check；完整 test 和 build 不进入 hook。

每个 Ubuntu workflow 都以完整 commit SHA 固定 Actions，只调用一次 `mise run ci`，不生成 OS 或版本矩阵。每个 `.github/renovate.json` 扩展 `config:recommended`，启用 semantic commits，添加 `dependencies` 标签，并显式关闭 lockfile maintenance；没有 auto-approve、automerge 或 schedule。

## 副作用边界

| 技术栈  | `mise run ci` 可产生但不应被跟踪的副作用                                                                 |
| ------- | -------------------------------------------------------------------------------------------------------- |
| Zig     | `.zig-cache/`、`zig-out/`                                                                                |
| Rust    | Cargo registry/git cache 与项目 `target/`                                                                |
| Node.js | pnpm store、`node_modules/`、工具 cache 与 `dist/`                                                       |
| Python  | uv cache、`.venv/`、Ruff/mypy/pytest cache 与 `dist/`                                                    |
| Go      | `GOCACHE`、`GOMODCACHE`、临时构建目录；支持的 library 或多 package thin-CLI 构建不在仓库根生成可执行文件 |

`mise install` 会访问网络并写 mise 的用户级 data/cache 目录，但适配器不修改全局 mise 配置或 shell rc。Lefthook 安装只写目标仓库的 `.git/hooks/`；生成 hook 只在该进程内把仓库根加入 `MISE_TRUSTED_CONFIG_PATHS`，不执行持久化 `mise trust`。Renovate 文件只配置仓库，不安装或授权 GitHub App。

## 失败与恢复

- 在写入前发现目标、栈、monorepo 边界、版本、替代工具或未知配置冲突时返回 `blocked`，不运行外部安装命令。
- 网络、工具安装、依赖锁定、hook 安装或质量门在写入开始后失败时返回 `partial`，报告精确 `failed_command`、已产生的变更和恢复步骤。
- `completed` 只用于 hook 已验证且 `mise run ci` 成功的运行。检查失败不会被降级为提示或描述成成功。

| 注入点         | 确定性证据                                                    | 预期状态                            |
| -------------- | ------------------------------------------------------------- | ----------------------------------- |
| 网络或工具安装 | Zig fake mise 在 `mise install` 失败                          | `partial`，保留精确 argv 与恢复步骤 |
| 锁文件生成     | Node.js `pnpm install --lockfile-only`、Python `uv lock` 失败 | `partial`                           |
| 项目依赖安装   | Node.js frozen install、Python locked sync 失败               | `partial`                           |
| hook 安装      | Node.js、Python 与既有 Zig installer 失败                     | `partial`                           |
| 质量门         | 五栈的 `mise run ci` 失败断言                                 | `partial`，`mise_run_ci=failed`     |
| 写入前冲突     | 版本、替代 manager、未知配置、workspace 或模块边界            | `blocked`，外部命令未运行           |

各语言单元测试还覆盖保留文件与幂等断言；`tests/test_bootstrap_project_integration.py` 统一解析五套任务、hook、workflow、Renovate 与行为矩阵。

## 平台与证据范围

- **macOS**：真实 smoke 在 Darwin arm64 上完成；这是当前最强运行时证据。
- **Linux**：PR #14 至 #19 的仓库级 Ubuntu CI 均为 2 项检查通过，证明离线 validator、单元测试和 fixtures 在 Ubuntu runner 上工作。生成项目的五套真实工具链命令尚未在独立 Linux 主机逐一 smoke，因此不能声称与 macOS 等强度的运行时覆盖。
- **Windows**：v1 不支持，也没有 WSL、PowerShell 或原生 Windows 行为保证。

固定答案 behavior eval 只验证 runner 与回答断言。需要认证服务的 live Codex eval 是交互判断的补充证据，不是确定性回归或文件副作用证明。

## 可重复验证

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_skills.py
python3 scripts/run_behavior_evals.py \
  --skill bootstrap-project --answers evals/fixtures/bootstrap-project
oxfmt --check .
```

真实工具链复验必须在临时目录运行对应适配器，再运行生成项目的 `mise run ci` 和 `.git/hooks/pre-commit`；不得在本仓库直接安装目标项目依赖来替代隔离 smoke。
