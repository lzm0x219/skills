# GPT-6 Astra 指令与评测审计

审计日期：2026-09-06。基线：`ba6b8a6`，开始时工作区干净。

本轮审计覆盖 9 个 Skill 入口、相关分支 references、行为契约、两个 Codex 评测入口与 CI。已落实确认边界、测试范围和评测可复现性修正。证据来自当前文件与离线检查；没有执行 Astra 实时对照或图像生成，因此不能据此宣称模型质量、速度或成本已经改善。

## 官方依据与适用范围

[GPT-6 Astra 官方模型指南](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#prompting-best-practices) 建议审计 Skill 和指令文件中的冲突，明确主动完成、输出风格、委派条件与验证范围。本项目主要受影响的是 Agent 指令和评测流程。API 异步工具、WebSocket steering 与缓存请求字段由宿主管理，本仓库没有对应的直接 API 调用层，未添加这些机制。

模型指南是优化依据，不取代领域事实、用户明确的只读要求或宿主权限。可移植 Skill 不固定为某个模型。评测显式指定模型与推理强度，按 [Codex 配置文档](https://learn.chatgpt.com/docs/config-file/config-basic) 传入 `model_reasoning_effort`；是否受支持由实际 CLI 与目标模型验证。

## 已修正的问题

| 位置                                                                                                                                                                         | 原有问题与触发条件                                                                      | 修改后的行为                                                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| [mise](../../skills/development/tools/mise/SKILL.md)                                                                                                                         | 项目 CI 文件编辑与全局配置、发布并列为需要明确授权的动作，容易让已授权修复再次暂停      | 项目编辑复用请求授权；信任、全局配置、发布仍按具体动作核对授权；缺失信息只阻塞相关工作                       |
| [电商入口](../../skills/commerce/china-commerce-asset-pack/SKILL.md) 与文案、图片、社媒 references                                                                           | 入口允许自动完成，下游却无条件要求用户确认战略或最终文字                                | 阶段门作为唯一规则来源；自动模式记录推荐方向并完成 QA，真实素材与事实缺口仍须补足                            |
| [电商发布边界](../../skills/commerce/china-commerce-asset-pack/references/operation-boundaries.md) 与 [契约](../../evals/china-commerce-asset-pack.behavior.json)            | `unapproved-publication` 原提示明确要求发布，却按未授权拒绝评分；规则也没有说明授权复用 | 将未授权场景改成明确只授权素材制作，另加已有发布授权场景；核对具体目标、定稿、权限和预算，不重复索要同一批准 |
| [持久状态](../../skills/development/workflows/durable-execution-state/SKILL.md)                                                                                              | 缺少宿主验证器时要求用户授权，但用户批准不能补足可信执行能力                            | 保留外部动作停止门，明确请求宿主配置验证器，继续不依赖它的准备工作；状态实现与可信验证协议未变               |
| [图像重构入口](../../skills/creative/reference-style-reframe/SKILL.md) 与 [视觉矩阵](../../skills/creative/reference-style-reframe/references/visual-test-matrix.md)         | 任何审计/修订或风格比较都可能触发十档出图                                               | 全档请求才做全档；两档比较只做两档；文字审计不出图；视觉回归按实际影响扩大                                   |
| [napi-rs](../../skills/development/framework/napi-rs/SKILL.md)、[Zig](../../skills/development/languages/zig/SKILL.md)、[mise](../../skills/development/tools/mise/SKILL.md) | 验证步骤缺少纯文档与局部改动的条件，Zig 默认版本矩阵过宽                                | 保留仓库必需检查，按行为、绑定、集成与兼容性影响选择验证；通过后有新证据才扩大或重跑                         |
| [文本评测](../../scripts/run_behavior_evals.py) 与 [工作区评测](../../scripts/run_workspace_evals.py)                                                                        | 可选模型但没有推理强度入口，难以固定对照条件                                            | 新增 `--reasoning-effort` / `CODEX_EVAL_REASONING_EFFORT`；显式参数优先；省略时保留 CLI 默认行为             |
| [CI](../../.github/workflows/validate.yml)                                                                                                                                   | 仅执行 6 个 Skill 的固定答案检查                                                        | 补齐持久状态和两套插画 Skill，覆盖全部 9 个 Skill                                                            |

新增 [Skill 编写约定](../agents/skill-authoring.md)，由根 [AGENTS.md](../../AGENTS.md) 在修改指令时路由读取，约束授权复用、分支引用、输出长度和验证停止条件；不将整份模型指南重复塞入每个 Skill。

## 保留的有效约束

| Skill                     | 审计决定                                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------ |
| `dsa-design`              | 保留适用性门槛、可逆内部选择直接推进，以及接口/迁移等重大选择的授权条件                                |
| `bootstrap-project`       | 保留确定性适配器、仅规划边界、冲突门与首次写入失败停止；这些保护已有项目，不能按通用主动性建议直接删除 |
| `juanjuan-illustrations`  | 已区分规划与直接生成，数量有默认值，保留角色、事实与视觉完成门；补入 CI                                |
| `durable-execution-state` | 保留可信验证、幂等与未知结果先对账，修正阻塞原因的描述                                                 |
| 其余 5 个 Skill           | 采用上表的局部修正，保持既有名称、领域能力、手动调用设置与事实约束                                     |

委派由当前宿主与请求决定，没有将官方示例中的积极委派提示变成可移植 Skill 的无条件要求。异步与中途更新建议落实为明确的依赖、范围与状态规则，没有假称单轮文本评测验证了运行中 steering。

## 验证记录

基线静态验证通过；基线单元测试为 162 项，其中 5 项跳过。新增 9 个行为场景与 6 项运行器单测，分别覆盖权限复用、范围收窄、验证器缺失、出图范围、适量验证及参数优先级。

| 检查                                                                                                                  | 结果                                                                         |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `rtk proxy oxfmt .` 与 `rtk proxy oxfmt --check .`                                                                    | 通过，106 个支持格式化的文件                                                 |
| `rtk proxy python3 scripts/validate_skills.py`                                                                        | 通过：9 个 Skill、50 个 Skill Markdown、68 个本地链接、9 份行为契约          |
| `rtk proxy python3 -m unittest discover -s tests -p 'test_*.py' -v`                                                   | 168 项，163 项通过、5 项因当前 Python 未安装 Pillow 跳过；与基线相同的跳过项 |
| `rtk proxy python3 scripts/run_behavior_evals.py --skill <name> --answers evals/fixtures/<name>`，逐一运行 9 个 Skill | 101 个固定答案用例全部通过；工作区专用场景仍从只读运行器排除                 |
| `rtk proxy git diff --check`                                                                                          | 通过                                                                         |

跳过的 5 项为 EXIF 归一化、透明 PNG 输出、Markdown 相对图片路径、持久 HTML 资源快照和私有资源快照渲染测试。本轮未修改这些 helper；这些路径在当前本机环境未重新验证。CI 配置会安装 Pillow 后运行，但本轮未触发远程 CI，不能声称远程检查已通过。

## 证据边界与后续对照

固定答案是人工维护的期望输出，只能证明断言与运行器可处理这些答案；fake Codex 测试只证明命令传递和回执处理。没有联网运行 Skill 的专用官方文档覆盖刷新脚本，也没有做真实发布、部署、账号或全局配置修改。本报告记录审计阶段的验证结果，Git 交付状态以提交记录为准。

实时对照步骤见 [行为评测说明](../behavior-evals.md#compare-a-model-or-prompt-change)：固定 CLI、模型、推理强度、案例、输入与 harness，在旧/新 Skill 两个修订上分别运行。新增场景必须对两版使用相同的新契约，旧 runner 可配合相同的新 harness 比较。记录错误暂停率、越界率、正确交付率、用时与可得 token 数据；图像质量另用实际看图验证。当前没有足够证据计算这些指标。
