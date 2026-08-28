# 提示词与质检模板

先完整填写画面取证卡。不要把没有从参考图中看见的对象、方位、文字或色彩写成事实。

```text
source_aspect_ratio: <例如 3:4；以实际参考图为准>
subject_and_relationship: <主体、动作或景物间必须保留的关系>
composition: <主体位置、远近层次、必要裁切和留白分布>
native_structure: <2–4 个决定识别的结构>
palette_groups: <2–5 个综合色组；说明明暗和冷暖关系>
p0_core_structure: <2–4 个不能丢失的结构，例如河道-拱桥-岸边建筑的关系>
p1_recognition_details: <0–5 个必须可辨的中层细节；例如屋檐节奏、门框台阶、桥面砌块分组、倒影带；极简图可写 none>
p2_remove: <仅列出未进入 P0/P1 的微纹理、杂物、厚重光影等>
text_title: <exact English title | none>
text_subtitle: <exact English short sentence | none>
text_area: <none | reserved | overlay；两段精确英文都有时默认 reserved；只有明确要求时才用 overlay>
```

## 无字底图模板

```text
Use case: style-transfer
Asset type: <source_aspect_ratio> editorial illustration
Input image: use the provided image only for observable subject matter, composition, crop, spatial hierarchy, native structure, and overall color relationships. Do not copy its signature, watermark, logo, identifiable character, or distinctive rendering details.

Reference facts: <copy the completed card>
Primary request: Reconstruct the reference as a minimal ink-wash flat illustration on warm off-white matte specialty paper. Preserve the reference aspect ratio, subject hierarchy, native structure, and overall color relationships.
Style and material: relaxed soft block shapes; layered opaque flat color fields with casual pale-ink blooms; naturally loose edges; restrained academic editorial finish; paper must remain visibly matte and off-white.
Layering: use only warm off-white matte paper, opaque flat color blocks for P0, and sparse pale-ink atmosphere. Do not turn pale ink into dense watercolor texture.
Structure and detail: preserve every P0 core structure. Preserve every item in p1_recognition_details as a legible, low-contrast secondary shape, irregular color cluster, or broken pale-ink mark. Do not flatten P1 into one generic silhouette. P1 must not be enclosed by continuous dark contour lines; reserve any light edge only for necessary local P0 occlusion or contact.
Composition: place the main subject centered slightly above the midpoint and keep expansive, intentional negative space. For text_area=reserved, reserve the lower <20–28>% as a clean, quiet, low-contrast, unobstructed typography-safe area. For text_area=overlay, use only existing quiet negative space and never cover P0 or P1. For text_area=none, do not intentionally create a lower typography-safe band.
Constraints: simplify scenery without changing P0 or p1_recognition_details. Remove only P2 microtexture, incidental clutter, heavy lighting, and hard cast shadows. Do not use universal hard contour lines.
Avoid: photorealism, 3D rendering, thick outlines, dense detail, decorative borders, seals, calligraphy, unrequested Chinese motifs, text, watermark, signature, logo, and extra ornaments.
```

## 后期文字规格

只在 `text_title` 与 `text_subtitle` 都由用户明确提供时使用。

```text
Canvas: keep the approved base image dimensions and aspect ratio.
Placement: for text_area=reserved, use the lower reserved area, horizontally centered. For text_area=overlay, use the approved existing negative space. Do not cover P0 or P1.
Title: exact text “<text_title>”; elegant serif or handwriting-inspired Latin typeface; centered; medium visual weight.
Subtitle: exact text “<text_subtitle>”; small sans-serif Latin typeface; centered below the title with restrained spacing.
Color: sample a quiet dark neutral from the approved palette; no glow, outline, shadow, badge, or ornament.
```

## QA 硬门槛

- [ ] 比例、主体关系、构图主次和 P0 核心结构均可回查到参考图。
- [ ] 每一项 P1 识别细节都可独立辨认，并以低对比小块面、色组或松散墨痕呈现，而非被抹成单一轮廓。
- [ ] P2 以外的细节没有被当作“简化”误删；除非数量有识别意义，不强加精确数量。
- [ ] 色彩保持整体调性而非逐色抄写；没有新增无依据的高饱和主色。
- [ ] 米白哑光纸底、P0 块面平涂、稀疏淡墨晕染与松散边缘同时成立。
- [ ] P1 没有连续深色闭合描边；任何轻边界只服务局部 P0 的遮挡或接触。
- [ ] 没有厚重光影、P2 以外的细碎纹理、杂物、印章、题跋、边框或多余装饰。
- [ ] 主体居中偏上；`reserved` 的文字安全区完整、`overlay` 没有碰撞 P0/P1、`none` 没有被人为切出底部文字带。
- [ ] 若有文字，标题和短句都与用户提供的字符串逐字一致；否则图片无文字。
- [ ] 没有签名、水印、Logo、原作特有角色或未经请求的作者模仿。

失败处理：结构问题重做事实卡；细节丢失时只补回 P1 的缺项；边线问题只减弱 P1 的闭合深线；文字区问题只调整 `text_area` 或排版；风格问题只调整材质或光影。不要同时改动场景、配色和文字来掩盖失败。
