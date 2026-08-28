# 运行环境与外部处理边界

仅在使用本 Skill 的 helper、联网研究、云端图像工具、Markdown 转 PDF 或真实发布时读取本文件。

## 环境检查与本地 helper

首次使用 helper 时运行：

```bash
python3 <skill-directory>/scripts/check_environment.py
```

它只报告可用和缺失的组件；不得自动安装依赖、修改系统配置或读取浏览器凭据。helper 需要 Python 3.11 或更高版本，基础依赖记录在 `requirements.txt`；只有用户明确授权后才安装。

图片尺寸统一、Markdown 转 PDF 和环境检查都在本地执行。具体图片处理要求读取 [image-production.md](image-production.md)，PDF 版式、渲染器和目视检查读取 [pdf-style.md](pdf-style.md)。

## 联网、云端处理与本地资料

- 联网研究会把商品名、品牌、关键词和目标 URL 发送给当前 Agent 的搜索或浏览服务；报告中保留实际使用的来源 URL。
- 使用云端图像生成或编辑工具时，商品图和 Prompt 会按该工具的规则发生外部请求；没有用户授权或处理边界不明确时，先说明并等待决定。
- 商品资料、成本、库存、评论截图与生成结果默认只写入用户指定的本地输出目录；未指定时在当前项目内创建商品目录，不写入作者机器的固定路径。
- 不读取 Cookie、API Key、浏览器配置、通讯录或与任务无关的文件。

## Markdown 与图片处理

- 只渲染本轮生成或已经审查的 Markdown。渲染第三方 Markdown 前，先检查原始 HTML、`script`、`file:` URL、远程资源和越界路径；发现风险时停止并说明原因。
- 本地报告图片只接受报告目录内真实存在、内容与扩展名匹配的 PNG、JPEG 或 WebP；PDF helper 会复制经验证的私有资源快照再渲染。
- 没有图像工具时，按 [image-production.md](image-production.md) 交付最终文字、逐图 Prompt 和制作清单，不得声称已经生成成图。

## 账号与发布

不登录店铺、社媒、广告或支付账户，不自动发布商品、社媒内容、广告或外部消息。任何真实上架、发帖、投放或外部发送，都需要用户另行明确授权。
