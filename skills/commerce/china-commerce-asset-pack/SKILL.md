---
name: china-commerce-asset-pack
description: 将面向中国市场的非服装商品资料转化为「电商素材包」：供品牌方决策的销售战略、供商品页成交的文案与视觉资产，以及供多渠道传播的原生内容。适用于新品上市、商品页设计、社媒种草、私域推广和页面优化；暂不适用于服装类商品。默认使用通用电商底座，用户指定平台时叠加平台差异。
---

# China commerce asset pack

将同一商品整理为三层可复用资产：供品牌方决策、商品页成交和多渠道传播。它不代替最终经营决策、账号运营、上架或投放。

当前流程暂不适用于服装类商品。用户请求服装选品、尺码、版型、面料或穿搭商品页时，说明范围不适用并停止，不创建产物。

## 三层交付

- **品牌方决策**：商品研究、目标顾客、差异化、核心主张、SKU、人民币价格及销售战略报告。
- **商品页成交**：不同说服路径的商详文案、确认后的逐屏视觉资产及视觉母版。
- **多渠道传播**：从同一传播母题派生的小红书、私域、朋友圈、公众号和按需补充的渠道内容。

所有外部素材共享同一战略母稿；商品页、社媒和私域不得改写产品事实、核心主张、SKU、价格或证据边界。

## 阶段门

```text
资料审计 → 品牌方决策包 → 确认商品战略与传播母题
→ 商品页成交文字 → 确认最终文案
→ 商品页成交图片与视觉母版 → 首屏确认
→ 多渠道传播包 → 全包验收
```

默认停在当前阶段门。只有用户明确授权自动完成全套流程时才能采用推荐方向继续；仍须在进入对应图片生产前，把战略、最终商详和渠道文案分别落盘。

用户只要求某一层或某一阶段时，只生成该范围的文件，不为目录完整制造空文件。

## 按需读取

### 品牌方决策包

读取 [research.md](references/research.md)、[compliance.md](references/compliance.md)、[strategy.md](references/strategy.md) 和 [pricing.md](references/pricing.md)，再按 [strategy-report-template.md](references/strategy-report-template.md) 生成商品销售战略报告。

需要分享版 PDF 时，额外读取 [deliverable-pack.md](references/deliverable-pack.md) 与 [pdf-style.md](references/pdf-style.md)。用户未要求 PDF 时，不自行导出。

### 商品页成交包

用户确认战略后，读取 [pdp-copy.md](references/pdp-copy.md) 产出 2—3 套有不同说服路径的完整商详文字。用户选择、合并或确认前，不开始图片工作。

确认最终文字并收到所需商品与品牌素材后，读取 [image-production.md](references/image-production.md) 制作视觉母版和逐屏图片。没有图像工具时，按 [operation-boundaries.md](references/operation-boundaries.md) 降级交付，不声称完成成图。

### 多渠道传播包

战略方向和最终商详文字确定后，读取 [social-media-pack.md](references/social-media-pack.md)，按渠道原生表达制作传播素材；不要把同一段长文机械截短后到处发布。

### 条件路由

- 用户未指定成交平台时，直接使用通用电商底座，不追问渠道。
- 用户明确指定成交平台或要求「按某平台可直接上架」时，读取 [platform-overlays.md](references/platform-overlays.md)，只叠加平台差异，不重做通用资产。
- 需要写入文件、制作清单、补做某阶段或验收整包时，读取 [deliverable-pack.md](references/deliverable-pack.md)。
- 使用 helper、联网研究、云端图像、Markdown 转 PDF 或真实发布前，读取 [operation-boundaries.md](references/operation-boundaries.md)。

## 共同约束

- 明确区分三类内容：可核验事实、可用营销表达、待验证商业假设。营销表达可以压缩和修辞，但不得捏造具体奖项、数字、机构背书、成分、功效、销量、用户身份或排他性事实。
- 高风险品类在关键事实或当前官方规则未核实前，只能交付带阻塞项的草案，不得标记为「可直接上架」。具体核查与发布阻塞项见 [compliance.md](references/compliance.md)。
- 首次使用 helper 时先运行 `python3 <skill-directory>/scripts/check_environment.py`；它只报告环境状态，且不得自动安装依赖、修改系统配置或读取浏览器凭据。
- 商品资料、成本、库存、评论截图与结果只写入用户指定目录；未指定时在当前项目内创建商品目录。
- 不读取 Cookie、API Key、浏览器配置、通讯录或无关文件；不自动发布商品、社媒内容、广告或外部消息。真实上架、发布和投放均需用户另行明确授权。

## 交付前

读取本轮实际使用的 reference 中的验收项，并确认 `00-电商素材包清单.md` 清楚列出已交付、未交付、待客户补充和发布阻塞项。
