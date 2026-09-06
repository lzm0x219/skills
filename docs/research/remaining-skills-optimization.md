# 剩余 Skills 优化记录

日期：2026-09-07。承接已完成的 `dsa-design` 与 `durable-execution-state`，其余 7 个 Skill 按下列顺序独立优化、验证、提交。

| Skill                     | 发现与改进                                                                                                      | 固定行为案例 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| bootstrap-project         | 六个适配器在执行前拒绝已占用的报告路径，报告采用独占创建；明确 partial 恢复不能清空已有产物或盲目重跑初始化。   | 22           |
| china-commerce-asset-pack | 区分相互冲突的 SKU 资料，追踪价格／规格变更导致的旧图片与 PDF 失效，从已有 QA 状态恢复生产。                    | 15           |
| napi-rs                   | 区分持有引用与内存同步；补充精确整数、协作取消、背压和最终 package 验收，并核对实际版本。                       | 9            |
| zig                       | 修正成功返回时的 defer／errdefer 所有权规则，补充扩容与重排导致的借用失效、分配失败验证和无编译器时的静态审阅。 | 19           |
| mise                      | 明确依赖列表不是串行顺序，补充失败传播、缓存输入与跳过状态、实际配置层及工作目录诊断。                          | 10           |
| juanjuan-illustrations    | 从读取 PNG 头改为流式检查分块与 CRC；拒绝截断文件、空记录和非有限容差，补充局部编辑的参考角色与保留项。         | 7            |
| reference-style-reframe   | 消除强制居中与保留原构图的冲突；支持独立标题／短句，统一模板与 QA，明确编辑目标和材质参考的作用。               | 27           |

本轮新增 19 个行为场景；上述 109 个固定答案案例均通过。固定答案只验证契约和运行器对已知回答的处理，不证明模型整体质量。

## 验证方式

每项提交前运行 `oxfmt .`、`oxfmt --check .`、`python3 scripts/validate_skills.py`、标准库全量单测，以及对应 Skill 的固定答案行为检查；所有 shell 命令使用仓库约定的 `rtk proxy` 前缀。

```sh
rtk proxy python3 -m unittest discover -s tests -p 'test_*.py'
rtk proxy python3 scripts/run_behavior_evals.py \
  --skill <skill-name> --answers evals/fixtures/<skill-name>
```

最终单测：190 项，185 项通过、5 项 Pillow 相关测试跳过。初始化报告和 PNG 校验器新增测试先复现失败，再验证修复；合法的连续 IDAT 分块样本和仓库角色参考 PNG 的结构检查通过。

PNG helper 按 [PNG 规范](https://www.w3.org/TR/png-3/) 检查分块框架、基本 IHDR 字段、CRC、图像数据存在及 IEND 终止。它不解码图像数据，也不是完整 PNG 一致性验证器；像素、文字和角色仍须单独检查。

## 真实模型抽查

使用现有 `/Applications/ChatGPT.app/Contents/Resources/codex`（0.153.4），模型 `gpt-6-astra`、推理强度 `high`、单例超时 90 秒，通过 `scripts/run_behavior_evals.py --case <id> --show-output` 执行只读回答评测。

已核查：

- 电商改价：正确标记旧 PDF／图片失效并复用未受影响资产。
- napi-rs 共享 Buffer：正确区分存活、Send 与并发访问安全，并要求安全复制或可证明的独占协议。
- Zig 返回分配：识别成功返回前释放与 double-free 风险，选择 errdefer 并设计成功／失败测试。
- mise 任务顺序：识别两个 depends 可并发，增加 test 对 generate 的依赖，并核查失败传播。
- 卷卷局部改字：正确区分编辑目标与角色参考，保留来源事实卡、动作和构图。
- 图文重构的两个场景：只排用户提供的单行标题，不追问或补造副标题；保持桥在左、河在右的原有构图，不套用居中默认值。

电商回答使用 “Reusable”，mise 回答使用 “concurrently”，单标题回答使用 “neither request nor invent a subtitle”，最初被过窄的正则误判；已修正同义表达匹配，并将原始回答保存为对应 fixture，用最终契约复核通过，没有重新生成回答来替换失败样本。

共抽查 7 个真实模型回答；逐项核查其决策，最终契约评分均通过。

这些抽查检验决策与回答，没有执行真实电商生产、Node addon 编译、Zig 编译、mise 项目任务或图片生成，不能据此声称平台兼容性、成图质量或总体模型效果已提升。

## 技术依据

- [napi-rs Type conversions](https://napi.rs/docs/concepts/type-conversions)、[Understanding lifetime](https://napi.rs/docs/concepts/understanding-lifetime)、[Async and concurrency](https://napi.rs/docs/more/async-concurrency)。
- [Zig 0.15.2 语言参考](https://ziglang.org/documentation/0.15.2/#errdefer)，仅用于核对所有权与清理语义，不把该版本固化为默认工具链。
- [mise Task Configuration](https://mise.jdx.dev/tasks/task-configuration.html) 与 [Configuration](https://mise.jdx.dev/configuration.html)，具体语法仍须匹配使用项目的实际版本。
