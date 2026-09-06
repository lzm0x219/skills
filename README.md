# Skills

让 AI 帮你做开发、准备电商素材、制作插画。按类别找到需要的 Skill，再把安装提示词发给 AI。

[![Validation](https://badges.ws/github/workflow/lzm0x219/skills/validate.yml?style=flat-square&label=validation&labelColor=111827&icon=githubactions&iconColor=white)](https://github.com/lzm0x219/skills/actions/workflows/validate.yml)
[![License: Apache-2.0](https://badges.ws/github/l/lzm0x219/skills?style=flat-square&labelColor=111827&color=111827&icon=apache&iconColor=white)](LICENSE)

[开发](#开发) · [电商](#电商) · [创作](#创作) · [安装](#让-ai-帮你安装) · [使用](#安装后怎么用)

## 有哪些 Skills

Skill 是 AI 可以读取的一份任务指南，告诉它怎样完成一类工作。点击名称可以查看完整说明。

### 开发

| Skill                                                                                    | 能帮你做什么                                                                           |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [bootstrap-project](skills/development/workflows/bootstrap-project/SKILL.md)             | 搭建新项目或补齐已有项目的开发配置，支持 Zig、Rust、TypeScript/Node.js、Python 和 Go。 |
| [dsa-design](skills/development/engineering/dsa-design/SKILL.md)                         | 为程序选择合适的数据结构与算法，比较速度、内存占用和实现成本。                         |
| [napi-rs](skills/development/framework/napi-rs/SKILL.md)                                 | 把 Rust 功能接入 Node.js，处理接口、异步任务、内存管理、打包和测试。                   |
| [zig](skills/development/languages/zig/SKILL.md)                                         | 编写、调试和维护 Zig 项目，按项目版本处理构建、依赖与兼容性问题。                      |
| [mise](skills/development/tools/mise/SKILL.md)                                           | 统一项目的开发工具版本、环境变量和常用命令，让本地与持续集成环境保持一致。             |
| [durable-execution-state](skills/development/workflows/durable-execution-state/SKILL.md) | 保存长任务的目标、进度与证据，帮助 AI 在中断后恢复工作，并核对外部操作的结果。         |

### 电商

| Skill                                                                           | 能帮你做什么                                                                                     |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| [china-commerce-asset-pack](skills/commerce/china-commerce-asset-pack/SKILL.md) | 为中国市场的非服装商品制作销售战略、商品详情页文案与图片，以及小红书、私域、朋友圈和公众号素材。 |

### 创作

| Skill                                                                       | 能帮你做什么                                                                 |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [reference-style-reframe](skills/creative/reference-style-reframe/SKILL.md) | 将参考图改造成水墨、工笔、拼贴等十种风格的插画，保留主体、构图与关键细节。   |
| [juanjuan-illustrations](skills/creative/juanjuan-illustrations/SKILL.md)   | 为中文文章规划或制作「卷卷」角色的怀旧手绘插图，用画面表达观点、情绪或隐喻。 |

## 让 AI 帮你安装

在支持本地 Skills 安装、能读写文件并执行命令的 AI 工具中，复制下面这段话。把 `【Skill 名称】` 换成上方的名称，例如 `juanjuan-illustrations`。

```text
请帮我从 https://github.com/lzm0x219/skills 安装【Skill 名称】。

识别我当前使用的 AI 工具，按它支持的方式安装。
默认只安装到当前工具、当前项目；没有项目时使用该工具的用户级目录。
安装完整的 Skill 目录及所需文件，保留已有自定义修改。
安装后检查文件是否齐全、能否被当前工具识别，并告诉我如何调用。
如果需要重启会话，或当前环境无法安装，请明确说明。
```

可以填写多个名称；想安装全部时，把 `【Skill 名称】` 换成 `这个仓库的全部 Skills`。

熟悉命令行？查看[手动安装方式](docs/usage-and-maintenance.md#手动安装)。

## 安装后怎么用

在对话里写出 `$Skill名称`，再描述具体任务。例如：

**开发项目**

```text
$bootstrap-project 检查这个项目，先给出初始化计划，不修改文件。
```

**准备电商素材**

```text
$china-commerce-asset-pack 为这款冷泡茶包做销售战略，先不要生成商品图片。
```

**制作文章插图**

```text
$juanjuan-illustrations 为这篇文章规划三张卷卷插图，暂不生成图片。
```

调用语法以当前 AI 工具为准；也可以直接告诉它要使用的 Skill 名称。图片生成还需要当前工具具备相应能力。

## 更多说明

[使用与维护说明](docs/usage-and-maintenance.md) · [行为评测](docs/behavior-evals.md) · [反馈问题](https://github.com/lzm0x219/skills/issues) · [Apache-2.0 许可证](LICENSE)
