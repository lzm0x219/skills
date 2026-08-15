# Apple 与 OpenAI 设计原则在中文 A4 报告中的安全转译

核对日期：2026-08-15。本文只使用 Apple 与 OpenAI 官方公开资料，并区分三类内容：**官方明确规范**、**从官方页面得到的视觉观察**、**本报告的转译建议**。后两类不声称是 Apple 或 OpenAI 的品牌规范。

## 结论

适合商品销售战略报告的组合是：用 Apple 的信息纪律组织内容，用 OpenAI 公开品牌页所表达的几何精度与人文温度控制气质，再建立报告自己的字体、颜色和几何系统。

- **安全借鉴：** 内容优先、清晰层级、稳定对齐、克制颜色、充足负空间、有限字重、语义一致和无障碍对比度。
- **不直接移植：** Apple 平台控件、Safe Area、Dynamic Type、Liquid Glass、深浅模式和触控交互；这些是动态 UI 规则，不是静态 A4 规范。
- **不复制：** 两家公司的 Logo、文字标识、专有字体、图标、模板、产品图、品牌锁定组合或相似标识，也不暗示官方制作、认可、赞助或合作。
- **视觉主张：** 取消砖红，以白、近黑和冷灰为主；只允许极浅冷色承担少量分组，不把任何自定色值描述为 Apple 或 OpenAI 官方色。

## Apple：可转译原则与 UI 边界

### 设计原则与层级

Apple 当前 Human Interface Guidelines 首页提出 hierarchy、harmony 和 consistency；单独的 Design principles 页面则强调 purpose、familiarity、flexibility、simplicity、craft 等原则，并明确指出 simplicity 不等于 minimalism，层级应帮助人理解当前内容和下一步。[Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) · [Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles)

安全转译为报告规则：

- 每页先确定一个主结论，再安排依据、限制和来源；装饰不能与结论争夺注意力。
- 相同信息使用相同视觉语法，例如风险、假设、价格和行动项各自保持固定结构。
- harmony 在 Apple 原文中包含与硬件和平台几何协调的含义；A4 只借鉴内部对齐、比例和节奏，不仿制 Apple 设备轮廓、同心圆角或系统界面。
- consistency 在 UI 中包含遵循平台惯例；A4 对应的是跨页重复的标题、表格、图表和页码规则，而不是复制 Apple 控件。

### Typography

Apple Typography 指南要求通过字号、字重和颜色表达层级，尽量减少字体种类；小字号应避免 Ultralight、Thin 和 Light，并在不同条件下验证可读性。[Typography](https://developer.apple.com/design/human-interface-guidelines/typography)

安全转译为报告规则：

- 中文正文只使用一套许可清楚、字形完整的无衬线家族；用 Regular、Medium、Semibold、Bold 建立层级。
- 正文约 10.5–11pt，来源与表格不得因塞版而无限缩小；等宽数字特性只在字体确实支持时启用。
- Dynamic Type、系统字号表和随用户设置自动缩放属于 UI 能力。PDF 只能用明确最小字号、行距、灰度检查和原尺寸目视检查替代。

### Layout

Apple Layout 指南建议用负空间、背景形状、颜色、材质或分隔线表达分组，让重要信息获得足够空间；阅读顺序、对齐和缩进共同建立视觉层级。[Layout](https://developer.apple.com/design/human-interface-guidelines/layout)

安全转译为报告规则：

- 使用稳定栅格和少量页面模板；标题、正文、表格、图表与注释共享对齐线。
- 先放结论摘要，再逐步提供分析与来源，以页面顺序替代 UI 的 progressive disclosure。
- Safe Area、窗口自适应、设备方向、控件悬浮层和滚动行为是 UI 专属，不转译为印刷尺寸。

### Color 与 accessibility

Apple 要求颜色具有一致语义，避免让同一颜色表达不同含义；颜色不能成为唯一的信息编码，并需考虑不同文化语境。Accessibility 页面以 WCAG Level AA 作为检查参考：17pt 及以下普通文字 4.5:1，18pt 或粗体文字 3:1。[Color](https://developer.apple.com/design/human-interface-guidelines/color) · [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility/)

安全转译为报告规则：

- 正文、来源和表格文字统一按至少 4.5:1 检查；大标题、粗体和有意义图形至少 3:1。
- 风险、状态和图表系列同时使用文字、形状、线型或位置，不只依赖红绿或深浅差异。
- Apple 的动态 system colors、Dark Mode、Increase Contrast 和屏幕环境适配属于运行时 UI；PDF 应改为彩色、灰度和打印三种静态检查。

### Apple 字体、模板和商标边界

Apple Fonts 页面附带的 San Francisco 许可把用途限制为 Apple 平台软件 UI 的 mock-up，并明确排除一般文档、艺术品、网站内容等其他作品；Apple Design Resources 也只许可用于 Apple 平台 UI mock-up。[Fonts for Apple platforms](https://developer.apple.com/fonts/) · [Apple Design Resources License](https://developer.apple.com/support/downloads/terms/apple-design-resources/Apple-Design-Resources-License-20230621-English.pdf)

Apple 的第三方商标规范还禁止未经授权使用 Apple Logo、仿制其标志、字体与 trade dress，或造成关联、赞助和认可的印象。[Guidelines for Using Apple Trademarks and Copyrights](https://www.apple.com/legal/intellectual-property/guidelinesfor3rdparties.html)

因此，本报告不使用 SF Pro、New York、SF Symbols、Apple Design Resources、Apple Logo、产品图或 Apple 风格的品牌锁定组合。中文字体优先选择许可清楚、允许嵌入和分发的思源黑体或 Noto Sans CJK，并在交付前核对实际字体文件的许可证。

## OpenAI：公开规范、视觉观察与边界

### 官方公开规范

OpenAI 公共 Design Guidelines 明确规定：wordmark 比例固定并需要净空；Blossom 不能加色、改形、加入未经授权元素、覆盖复杂背景或作为主要品牌；Logo 只应在直接涉及 OpenAI 服务时按原样使用，不能比自有品牌更突出，也不能暗示 endorsement、sponsorship 或 incorporation into another brand。[OpenAI Design Guidelines](https://openai.com/brand/)

同一页面对 OpenAI Sans 的明确描述是：几何精度与功能性结合圆润、亲和的性格，具有 Light、Regular、Medium、Semibold、Bold 五种字重及相应斜体，并包含 tabular figures 等 OpenType 能力，目标是在数字与印刷场景中兼顾清晰度和人文温度。[OpenAI Design Guidelines — Typography](https://openai.com/brand/#typography)

可安全转译的只有抽象原则：

- 几何应服务清晰度，圆润只提供少量亲和感，不能让卡片和装饰主导页面。
- 数据表使用稳定对齐和可用时的等宽数字；正文使用稳健字重，不复制 OpenAI Sans 字形。
- 平衡留白与层级，避免标识、标题或合作方名称彼此拥挤。

### 视觉观察，不是公开 token

OpenAI 公共 Brand 页的 Gallery 可观察到大字号、黑白基底、充足开放空间、简洁几何和少量柔和色面。但公开页面没有给出可供第三方直接采用的完整 palette 数值、A4 栅格、间距 token 或图形组件规则；其“full design guidelines”链接在核对日跳转到需要认证的 `brand.openai.com`。[OpenAI Design Guidelines](https://openai.com/brand/) · [Full design guidelines 登录入口](https://brand.openai.com/)

因此，黑白编辑感和柔和色面只能标为视觉观察。下文色值与网格是本报告的自有建议，不是 OpenAI 官方规范。

### OpenAI 品牌资产与背书边界

OpenAI 把名称、Logo、ChatGPT、GPT、图标和其他识别性设计元素定义为其 Marks；公开条款要求按指南使用，不得让 OpenAI 标识比自有品牌更突出，并允许 OpenAI 要求修改或停止使用。共同品牌材料还需要双方审批。[OpenAI Design Guidelines — Usage terms](https://openai.com/brand/#usage-terms)

因此：

- 不使用 OpenAI wordmark、Blossom、ChatGPT/GPT 品牌或仿制标识作为报告自身身份。
- 不把 OpenAI Sans 当作可自由使用的通用商业字体；只有取得适用的完整许可后才能考虑使用。
- 对外报告不写“Apple/OpenAI 官方风格”“联合设计”“获得认可”等表达；若正文确需提及服务，只做准确事实说明。

## 中文 A4 报告的自有视觉系统建议

以下数值是对官方原则的工程化转译，不属于 Apple 或 OpenAI 的品牌资产。

### 中性颜色系统

| 角色             | 建议色值  | 用途                         |
| ---------------- | --------- | ---------------------------- |
| `page`           | `#FFFFFF` | 纸张背景                     |
| `ink`            | `#111111` | 大标题、关键数字和决策轨道   |
| `text-body`      | `#2C2C2E` | 正文                         |
| `text-secondary` | `#48484A` | 副标题、次要说明             |
| `text-muted`     | `#636366` | 页眉、页码、来源辅助信息     |
| `surface`        | `#F5F5F7` | 普通分组面                   |
| `surface-cool`   | `#EDF2F4` | 少量决策摘要，不承担状态语义 |
| `border`         | `#D1D1D6` | 细分隔线                     |
| `border-strong`  | `#8E8E93` | 表格收尾、附录边界           |

不使用砖红、品牌绿、彩色渐变或仿 Liquid Glass 材质。封面和阅读导航使用黑色决策轨道，最终决策页使用黑色标题轨道与白色正文双栏；其余页面保持白底和中性灰层级。

### 排版与几何系统

- A4 竖版使用约 23mm 左右页边距和 6 栏编辑栅格；表格可跨栏，但标题、段落和注释必须落在共享对齐线上。
- 间距只取 `2 / 4 / 6 / 10 / 16 / 24mm`；跨页组件沿用同一节奏，不临时制造近似数值。
- 封面约 42pt、一级标题约 30pt、二级标题约 16pt、三级标题约 12pt、正文约 10.8pt、来源约 9.2pt、页眉页码约 8.6pt。
- 卡片保持平面化：无阴影、无玻璃、无大面积渐变；用负空间、0.35–0.6pt 横线和浅灰面分组。
- 圆角只在确有分组价值时使用，并保持单一小尺度；不使用胶囊按钮、Apple 控件轮廓或 Blossom 式图形作为装饰。
- 表格优先横线而非密集框线；金额、比例、数量和日期右对齐并统一格式，数字字形支持时启用 tabular figures。
- 封面与章节开场可以非对称留白；正文页保持高密度、稳定基线。每页只允许一个视觉焦点。

## 验收边界

这套方向的成功标准不是“像 Apple 或 OpenAI”，而是：读者先找到决策，再核对证据；黑白打印仍保留层级；中文正文和宽表格可读；任何页面都不会造成两家公司制作、赞助或认可该报告的印象。
