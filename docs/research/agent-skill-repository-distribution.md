# Agent Skills 社区的仓库组织与分发研究

核对日期：2026-08-28。本文优先使用 Agent Skills 规范、Vercel Skills CLI 与 Anthropic 官方源码；“官方事实”只陈述来源直接支持的行为，“推论”则明确标注为架构判断，不能当作规范。

## 先确定边界：Skill、源码仓库与目录不是同一层

- **官方事实：** Agent Skills 规范把可移植单元定义为一个 `skill-name/` 目录，至少包含 `SKILL.md`；`scripts/`、`references/` 与 `assets/` 是可选的同包资源。规范并未规定一个 Skill 必须对应一个 GitHub 仓库，也没有规定 registry 的协议。[规范](https://agentskills.io/specification)（访问：2026-08-28）
- **官方事实：** `SKILL.md` 的 `name` 与父目录名必须一致；名称为 1–64 个小写字母、数字或连字符，且不能以连字符开头/结尾或连续使用连字符。该规则约束的是**Skill 标识**，不是 GitHub repository 名称。[规范源码](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)（访问：2026-08-28）
- **官方事实：** 官方客户端实现指南将 `.agents/skills/` 描述为跨客户端本地共享约定，并列出克隆配置仓库、接受 Skill URL/包、上传目录等取得方式；它仍未指定远端必须采用单体或单 Skill 仓库。[客户端实现指南](https://agentskills.io/client-implementation/adding-skills-support)（访问：2026-08-28）

**推论：** “一项 Skill”的稳定边界应是 `SKILL.md` 所在目录及其资源，而仓库、插件包和目录站都只是不同的维护与交付边界。因此，不能因为要独立仓库而更改 Skill 的规范名称。

## 已验证的社区分发模式

### 1. 单体 Skills 合集（monorepo）

- **官方事实：** Anthropic 的 [`anthropics/skills`](https://github.com/anthropics/skills) 在一个源码仓库的 `skills/` 下并列多个独立 Skill 目录；README 明确把 Skill 描述为各自包含 instructions、scripts 和 resources 的文件夹。[README](https://github.com/anthropics/skills/blob/main/README.md) · [`skills/` 目录](https://github.com/anthropics/skills/tree/main/skills)（访问：2026-08-28）
- **官方事实：** Vercel 的 [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) 同样用一个仓库公开多项 Skills，CLI 使用 `npx skills add vercel-labs/agent-skills` 安装，也允许用 `--skill` 选择其中一项。[仓库 README](https://github.com/vercel-labs/agent-skills/blob/main/README.md) · [CLI 选项](https://github.com/vercel-labs/skills/blob/main/README.md#options)（访问：2026-08-28）
- **官方事实：** Vercel Skills CLI 会在根目录及 `skills/`、`skills/.curated/`、`skills/.experimental/`、`skills/.system/` 中发现 Skill；容器目录默认向下扫描最多三层，覆盖 `skills/<category>/<skill>/SKILL.md` 等合集布局。[CLI 文档：Skill Discovery](https://github.com/vercel-labs/skills/blob/main/README.md#skill-discovery) · [实现](https://github.com/vercel-labs/skills/blob/main/src/skills.ts)（访问：2026-08-28）

**推论：** 当多个 Skill 共享验证器、发布规则、版本约束或维护团队，并且通常一起演进时，单体合集是最低的维护成本；官方公开样本也更接近这一基线。但它不应把无关的重依赖、独立许可或私有 IP 强行捆绑进同一 release。

### 2. 一个 Skill 一个源码仓库

- **官方事实：** Vercel Skills CLI 接受 GitHub `owner/repo`、完整 Git URL、仓库内某个 Skill 的 tree URL、本地路径，以及直接指向 `SKILL.md` 或归档文件的下载 URL；根目录若有合法的 `SKILL.md` 也会被识别为一个 Skill。[CLI Source Formats](https://github.com/vercel-labs/skills/blob/main/README.md#source-formats) · [发现实现](https://github.com/vercel-labs/skills/blob/main/src/skills.ts)（访问：2026-08-28）
- **官方事实：** CLI 的 `init` 输出发布建议为“推送到 GitHub，然后执行 `npx skills add <owner>/<repo>`”；这说明根目录仅含一个 Skill 的仓库可被直接分发，但该命令没有把“一仓库一 Skill”规定为唯一模型。[CLI 实现](https://github.com/vercel-labs/skills/blob/main/src/cli.ts)（访问：2026-08-28）

**推论：** 单 Skill 仓库适合确实独立的维护、版本、许可证、依赖、测试环境或访问权限边界；采用时，仓库名默认应与 `SKILL.md:name` 相同（如 `dsa-design`），从而保持 GitHub URL、安装命令与 Skill 标识一致。是否增加 `-skill` 后缀是品牌选择，不是社区或规范要求。

### 3. catalog / registry（目录与发现层）

- **官方事实：** `npx skills find` 的安装提示是 `npx skills add <owner/repo@skill>`；这表明 Skills CLI 的发现结果保留或返回真实 source，而安装仍针对该 source 执行。[查找命令实现](https://github.com/vercel-labs/skills/blob/main/src/find.ts)（访问：2026-08-28）
- **官方事实：** 对一个 Vercel CLI source，`add` 会下载或克隆该 source，随后仅在下载/克隆出的目录中调用 `discoverSkills`；若没有找到合格 `SKILL.md` 则报错。[安装管线实现](https://github.com/vercel-labs/skills/blob/main/src/add.ts)（访问：2026-08-28）
- **官方事实：** CLI 会读取 Claude plugin manifest 以发现本地 plugin 的 Skill 路径，但其实现明确写为“只解析本地路径，跳过 remote sources”。因此，该 manifest 不能让 `npx skills add <catalog-repo>` 透明地转而安装外部 Git 仓库的 Skill。[`plugin-manifest.ts`](https://github.com/vercel-labs/skills/blob/main/src/plugin-manifest.ts)（访问：2026-08-28）
- **官方事实：** Claude Code 的官方插件目录是另一种 marketplace：同一 [`marketplace.json`](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json) 既可引用仓库内 plugin，也有 `git-subdir`、URL 等外部 source 条目；Anthropic README 说明该目录可通过 Claude Code plugin system 安装。[官方目录 README](https://github.com/anthropics/claude-plugins-official/blob/main/README.md) · [manifest](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json)（访问：2026-08-28）

**推论：** catalog 有两种不同含义，必须分开设计：

| 类型                                        | 能否直接分发外部仓库                                                                                                                                           | 适用边界                                                               |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 面向 Vercel Skills CLI 的普通 `skills` 仓库 | **不能依靠 README 或远程 manifest 转发。** `npx skills add lzm0x219/skills` 只能安装该仓库实际包含或下载得到的 Skill；catalog 应提供每个子仓库的明确安装命令。 | 跨客户端的人类可读发现页、迁移索引与版本状态页。                       |
| Claude Code plugin marketplace              | **可以，但采用的是 Claude plugin marketplace 的外部 source 语义。** 这不是通用 Agent Skills 规范，也不是 Vercel CLI 的远程转发能力。                           | 已决定维护 Claude Code plugin manifest、审核第三方 source 和兼容性时。 |
| 独立 registry/目录站                        | **可以提供“发现 → 原仓库安装命令”，但不能凭空改变安装器的 source 解析规则。**                                                                                  | 可搜索、可筛选、可度量的发现层；真实版本与供应链仍归源仓库。           |

## 对 `lzm0x219/skills` 的可执行结论

1. **当前保留单一源码仓库。** 它直接分发所有 Skill，并让验证器、CI、行为契约与维护历史保持在同一 Module；这是目前单一维护者和共享基础设施下的最低管理成本选择。
2. **仓库内使用 `development`、`commerce`、`creative` 三个顶层分类。** 分类表达发现和维护导航，不改变每个 `SKILL.md` 目录才是独立 Skill 单元的事实。
3. **不为预期中的拆分复制基础设施。** 只有独立维护者、发布/许可证/访问权限边界，或真实的跨仓复用需求出现时，才重新评估拆仓或共享工具 Module。
4. **未来若改为 catalogue + 多源码仓库，仍须使用真实 source 安装命令。** 普通 Vercel Skills CLI 不会让 README 或远程 manifest 自动转发外部 source；该结论应随 CLI 版本复核。

## 命名的证据边界

- **有明确标准的只有 Skill 名：** 小写 kebab-case，并与 leaf directory 一致。[规范](https://agentskills.io/specification)（访问：2026-08-28）
- **仓库名没有统一社区标准：** 官方例子同时存在通用集合名 `skills`、`agent-skills` 与插件目录名 `claude-plugins-official`；它们反映仓库的角色，不是要求每个仓库都带 `skills` 后缀。[Anthropic Skills](https://github.com/anthropics/skills) · [Vercel Agent Skills](https://github.com/vercel-labs/agent-skills) · [Anthropic Plugin Directory](https://github.com/anthropics/claude-plugins-official)（访问：2026-08-28）

因此，当前命名职责可以清晰分为：`skills` 表示单一源码合集；`development`、`commerce` 与 `creative` 是仓库内分类；内部 Skill 保持规范要求的精确 name 与目录名。只有将来出现独立发布/权限/维护边界时，才进一步拆为源码仓库。

## 核验范围

本文没有对 GitHub 全站做样本统计，也不将上述少量官方仓库外推为“唯一社区惯例”。它验证的是：开放规范未强制仓库边界；主流 CLI 同时支持合集和单 Skill source；catalog 对外部 source 的直接分发能力取决于具体安装器/marketplace，而不是 `SKILL.md` 格式本身。
