# 场景路由

仅当 `scene_mode` 不是 `standard` 时读取所选章节。路由把场景特有事实补进画面取证卡；所有内容仍受 P0/P1/P2、`style_profile`、`style_intensity`、`text_area` 与权利边界约束。

## `portrait-figure`

适用于一至三名人物是画面主体的生活照、旅行照和环境肖像；不用于要求可验证身份、精确五官复现、换脸或生物特征比对的任务。

**取证与提示词约束**

```text
Scene route: portrait-figure. Record the visible person count, each person's position and body direction, the main pose or gesture, head direction, clothing silhouette and two to four clothing color groups. Treat person count, relative placement, pose, and any user-designated gesture as P0 or P1. Preserve them without adding, removing, merging, or substituting people. Keep faces simplified and non-photorealistic; do not infer names, age, identity, emotion, accessories, or unseen body parts.
```

QA: 检查人数、站坐关系、动作、朝向和服饰色组；人物脸部可风格化，但不得借“风格化”替换身份线索、凭空补首饰/手持物或改变明确手势。第三方人物图仍需由用户确认可用范围。

## `product-still-life`

适用于无品牌或可去标识的器物、家居物件和商品静物的编辑性重构；不用于电商主图、精确尺寸/材质/规格展示、功效承诺或品牌资产复刻。

**取证与提示词约束**

```text
Scene route: product-still-life. Record the product count, outer silhouette, visible components, open/closed state, orientation, overlap order, material color groups, and any user-designated functional contour. Treat product count, silhouette, visible components, orientation, and overlap order as P0 or P1. Preserve those facts without inventing buttons, ports, seams, functions, labels, or brand marks. Replace logos and unreadable labels with blank, non-branded surface; exact marketing text belongs to the separate post-layout step.
```

QA: 检查数量、外轮廓、可见部件、朝向、开合状态、叠放关系和材质色组；不能借由风格简化改出新产品结构。输出是编辑性插画，不证明材质、性能、尺寸或商用合规。

## `dense-narrative`

适用于多人、多物或多区域共同构成事件关系的日常叙事场景；不用于要求每张脸、每件商品、每块招牌或每条文字都准确可读的任务。

**取证与提示词约束**

```text
Scene route: dense-narrative. Divide the image into foreground, middle ground, and background event zones. Record the total visible subject count only when it is clearly observable or explicitly required, each zone's main action and spatial relationship, and at most five user-prioritized recognition details. Treat event zones, their primary action, subject count when recorded, and user-prioritized details as P0 or P1. Preserve every zone without merging subjects, inventing a new action, or moving an action into another zone. Represent faces with simple, non-photorealistic marks; actions, pose, and zone relationship take priority over facial detail. Simplify only P2 micro-objects and repeated texture; do not guess unreadable text, brands, identities, or off-frame story details.
```

QA: 检查前中后景事件区、关键动作与被记录的数量；高密场景允许删除 P2，但不能把所有区域做成同一团色块，也不能为“丰富叙事”增加人物、道具或情节。脸部应退为概括的非写实标记，不得以高精度五官和厚重明暗抢占事件信息。若用户需要超过五个中层细节，先要求其标注优先级。
