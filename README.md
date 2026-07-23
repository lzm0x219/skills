# Skills

这个仓库维护可复制安装的 Codex Skills。目前包含：

| Skill | 用途 | 触发边界 |
| --- | --- | --- |
| [`dsa-design`](skills/dsa-design/SKILL.md) | 根据真实的数据规模、操作模式和约束比较数据结构与算法，并给出推荐 | 适用于明确调用，或实现中存在会实质影响正确性、性能、资源上限、接口、依赖、持久化或维护成本的 DSA 决策；纯文案改动和没有实质 DSA 取舍的常规 CRUD 不应触发 |

## 仓库结构

```text
.
├── skills/
│   └── dsa-design/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── references/
├── evals/
│   ├── fixtures/dsa-design/
│   └── dsa-design.behavior.json
├── scripts/
│   ├── run_behavior_evals.rb
│   └── validate_skills.rb
└── .github/workflows/
    └── validate.yml
```

每个 Skill 目录以 `SKILL.md` 为入口；`agents/openai.yaml` 提供界面元数据与调用策略；`references/` 仅在相关决策需要时加载。

## 安装

从本仓库检出中复制 Skill。以下命令会在目标已存在时停止，避免静默覆盖：

```sh
set -eu
skill_destination="${CODEX_HOME:-$HOME/.codex}/skills"
skill_target="$skill_destination/dsa-design"
if test -e "$skill_target"; then
  printf 'Target already exists: %s\n' "$skill_target" >&2
  exit 1
fi
mkdir -p "$skill_destination"
cp -R skills/dsa-design "$skill_target"
```

也可以只复制 `skills/dsa-design` 到支持同类 Skill 目录结构的项目级位置。复制前应检查目标环境的本地约定。

## 验证

运行无网络、无第三方依赖的仓库检查：

```sh
ruby scripts/validate_skills.rb
```

脚本使用 Ruby 标准库验证：

- `skills/*/SKILL.md` 的 YAML frontmatter、目录与 `name` 一致性及非空 `description`；
- 根 README 与 Skill 内 Markdown 本地链接是否仍位于仓库内且目标存在；
- `agents/openai.yaml` 的必需界面字段、默认提示中的 `$skill-name` 引用，以及调用策略的布尔类型；
- `evals/dsa-design.behavior.json` 的基本结构、可执行断言与四个必需行为场景；
- 行为回归执行器能够读取并列出全部场景。

GitHub Actions 也会运行静态检查，并用固定输出验证行为断言执行器。默认 CI 不调用模型，因此不需要凭据，也不会产生模型调用费用。

## 行为评测

[`evals/dsa-design.behavior.json`](evals/dsa-design.behavior.json) 是机器可读的行为契约，覆盖：

- 纯文案改动不触发；
- 没有实质 DSA 取舍的简单 CRUD 不强制触发；
- 重大 Top-K 决策触发比较并在未获授权时等待选择；
- 用户已委托选择时不因选择方案而暂停。

使用已认证的 Codex CLI 执行全部行为回归：

```sh
ruby scripts/run_behavior_evals.rb
```

真实模型运行会把评测提示和 Skill 内容发送给配置的 Codex 服务。可先使用仓库内固定输出离线验证执行器，或列出、筛选场景：

```sh
ruby scripts/run_behavior_evals.rb --answers evals/fixtures/dsa-design
ruby scripts/run_behavior_evals.rb --list
ruby scripts/run_behavior_evals.rb --case simple-crud-no-forced-dsa
```

执行器把工作树中的 Skill 复制到临时项目，并使用唯一评测名称加载，以免同名已安装副本污染结果；随后以只读沙箱和临时会话调用 Skill，并根据契约中的正则断言判定结果。无 `--answers` 的命令会产生真实模型调用；固定输出只验证执行器与断言，不代表当前模型通过回归。

## 许可证

本仓库依据 [Apache License 2.0](LICENSE) 授权。
