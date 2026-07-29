# Skills

[![Validation](https://badges.ws/github/workflow/lzm0x219/skills/validate.yml?style=flat-square&label=validation&labelColor=111827&icon=githubactions&iconColor=white)](https://github.com/lzm0x219/skills/actions/workflows/validate.yml)
[![Target: Codex](https://badges.ws/badge/target-Codex-10A37F?style=flat-square&labelColor=111827&icon=openai&iconColor=white)](#兼容性和限制)
[![Format: Agent Skills](https://badges.ws/badge/format-Agent%20Skills-7C3AED?style=flat-square&labelColor=111827&icon=markdown&iconColor=white)](https://agentskills.io/specification)
[![License: Apache-2.0](https://badges.ws/github/l/lzm0x219/skills?style=flat-square&labelColor=111827&color=0EA5E9&icon=apache&iconColor=white)](LICENSE)

这里的每一个 Skill，都源自我实际遇到的问题，也会随着新的需求不断增加。

## 选择合适的 Skill

不确定要不要用时，先看下面的边界。显式调用最稳妥；是否隐式匹配由 Codex 和当前模型决定，因此这里不承诺“装上就一定自动触发”。

| Skill | 适合 | 不适合 | 显式调用 |
| --- | --- | --- | --- |
| [`dsa-design`](skills/engineering/dsa-design/SKILL.md) | 数据结构或算法选择会实质影响正确性、性能、资源上限、接口或维护成本 | 纯文案改动，以及没有实质 DSA 取舍的常规 CRUD | `$dsa-design` |
| [`napi-rs`](skills/framework/napi-rs/SKILL.md) | 使用 napi-rs 接入、设计、实现、调试、测试、构建或发布 Rust Node-API addon | 与 Rust、Node-API 或 napi-rs 无关的任务 | `$napi-rs` |

`napi-rs` 遇到精确 API、命令行参数、目标支持或发布流程时，会先回到当前官方文档，而不是把写进 Skill 时的知识当成永久事实。

## 安装并开始使用

推荐使用 [Vercel Labs Skills CLI](https://github.com/vercel-labs/skills) 来发现和安装仓库中的 Skill。先查看可用清单，不修改当前项目：

```sh
npx skills add lzm0x219/skills --list
```

默认安装到当前项目，并只为 Codex 安装选定的 Skill：

```sh
npx skills add lzm0x219/skills --skill napi-rs --agent codex
```

需要在所有项目中使用时，改为全局安装：

```sh
npx skills add lzm0x219/skills \
  --skill napi-rs --agent codex --global
```

把 `napi-rs` 替换为 `dsa-design` 即可安装另一个 Skill。安装后可以分别检查项目级和全局状态：

```sh
npx skills list --agent codex
npx skills list --global --agent codex
```

`npx` 可能在首次运行时下载第三方 `skills` CLI。安装前应先使用 `--list`，并审查目标 Skill 的 `SKILL.md`、脚本和附属资源。交互式确认默认保留；只有在已经固定来源并审查过内容的自动化中，才添加 `--yes`。

如果当前 Codex 会话没有发现新安装的 Skill，请重新打开任务。然后用 `$skill-name` 显式调用：

```text
$napi-rs 评审这个 addon 的异步、生命周期和发布边界，先不要修改代码。
```

## 了解仓库结构

仓库采用 [Agent Skills 规范](https://agentskills.io/specification) 所定义的基础目录模型，并增加 Codex 元数据和本仓库自己的行为验证约定。

```text
.
├── skills/
│   ├── engineering/dsa-design/
│   └── framework/napi-rs/
├── evals/
│   ├── fixtures/
│   └── *.behavior.json
├── tests/
├── scripts/
└── .github/workflows/validate.yml
```

各类文件承担不同职责：

| 路径 | 职责 |
| --- | --- |
| `skills/**/SKILL.md` | 必需入口；frontmatter 用于发现，正文仅在 Skill 被使用时加载 |
| `skills/**/agents/openai.yaml` | Codex 界面元数据、默认提示和隐式调用策略 |
| `skills/**/references/` | 按任务需要读取的参考资料，避免把所有内容塞进 `SKILL.md` |
| `skills/**/scripts/` | 可执行的确定性检查或辅助工具 |
| `evals/*.behavior.json` | Skill 的机器可读行为契约、源码断言和必需场景 |
| `evals/fixtures/` | CI 使用的固定回答；用于验证断言执行器，不代表当前模型表现 |
| `tests/`、`scripts/` | 验证仓库结构、评测隔离和契约执行逻辑 |

`agents/openai.yaml` 和 `evals/` 是本仓库约定，不是 Agent Skills 开放规范的必需文件。

## 判断验证结果能证明什么

仓库把验证分成四层。每一层回答不同问题：

| 检查 | 能证明 | 不能证明 |
| --- | --- | --- |
| 仓库静态验证 | frontmatter、路径、链接、Codex 元数据、行为契约和源码断言符合仓库规则 | Skill 在真实模型中一定给出正确答案 |
| 固定回答回归 | 行为评测执行器和正则断言能稳定识别已知输出 | 当前模型已经通过这些场景 |
| 真实 Codex 评测 | 当前 CLI、模型和 Skill 对指定场景的最终可见输出满足断言 | 模型内部一定加载或没有加载某个 Skill |
| napi-rs 文档覆盖检查 | 本地清单与检查时的官方索引一致，且链接可访问 | 未来版本或未运行平台仍然有效 |

GitHub Actions 运行静态验证、执行器单元测试和固定回答回归。默认 CI 不调用模型，也不访问 napi-rs 官方网站。

## 运行本地检查

提交前先运行离线检查。这些命令只使用仓库文件和 Python 标准库：

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
```

真实行为评测需要已认证的 Codex CLI，并会把评测提示和 Skill 内容发送给配置的 Codex 服务：

```sh
python3 scripts/run_behavior_evals.py --skill dsa-design
python3 scripts/run_behavior_evals.py --skill napi-rs
```

刷新或发布 `napi-rs` 官方文档清单前，再运行联网检查：

```sh
node skills/framework/napi-rs/scripts/verify-official-docs-coverage.mjs \
  --check --verify-links
```

评测场景、隔离方式和限制见[行为评测说明](docs/behavior-evals.md)。

## 添加或修改 Skill

每个 Skill 都需要一条可执行的质量路径。新增或修改时：

1. 在 `skills/<category>/<skill-name>/` 中维护 `SKILL.md`
2. 在 `agents/openai.yaml` 中提供 Codex 界面元数据和调用策略
3. 在 `evals/<skill-name>.behavior.json` 中定义源码断言和必需场景
4. 为每个场景添加 `evals/fixtures/<skill-name>/<case-id>.txt`
5. 更新 Skill 清单，并运行全部离线检查

`description` 应同时说明 Skill 做什么、何时使用。较长资料放进 `references/`，确定性工具放进 `scripts/`，不要让 `SKILL.md` 承担与当前任务无关的全部背景。

当前验证器会锁定已收录 Skill 的必需场景。新增 Skill 时，还需要在 `scripts/validate_skills.py` 中登记对应的场景类别和调用方式。

## 兼容性和限制

仓库当前以 Codex 的目录、界面元数据和评测执行器为验证目标。其他 Agent 可能读取同样的 `SKILL.md`，但其发现路径、元数据、脚本权限和隐式调用行为需要单独验证。

Skill 是任务指导和工具集合，不是运行时安全边界。执行脚本、联网、发布或修改外部系统前，仍应检查代码、凭据范围和用户授权。

## 许可证

本仓库依据 [Apache License 2.0](LICENSE) 授权。
