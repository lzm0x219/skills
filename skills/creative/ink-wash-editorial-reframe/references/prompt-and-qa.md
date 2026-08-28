# 提示词与质检模板

先完整填写画面取证卡。不要把没有从参考图中看见的对象、方位、文字或色彩写成事实。

```text
source_aspect_ratio: <例如 3:4；以实际参考图为准>
subject_and_relationship: <主体、动作或景物间必须保留的关系>
composition: <主体位置、远近层次、必要裁切和留白分布>
native_structure: <2–4 个决定识别的结构>
palette_groups: <2–5 个综合色组；说明明暗和冷暖关系>
remove: <细碎纹理、杂物、厚重光影等>
text_title: <exact English title | none>
text_subtitle: <exact English short sentence | none>
```

## 无字底图模板

```text
Use case: style-transfer
Asset type: <source_aspect_ratio> editorial illustration with a typography-safe lower margin
Input image: use the provided image only for observable subject matter, composition, crop, spatial hierarchy, native structure, and overall color relationships. Do not copy its signature, watermark, logo, identifiable character, or distinctive rendering details.

Reference facts: <copy the completed card>
Primary request: Reconstruct the reference as a minimal ink-wash flat illustration on warm off-white matte specialty paper. Preserve the reference aspect ratio, subject hierarchy, native structure, and overall color relationships.
Style and material: relaxed soft block shapes; layered opaque flat color fields with casual pale-ink blooms; naturally loose edges; restrained academic editorial finish; paper must remain visibly matte and off-white.
Composition: place the main subject centered slightly above the midpoint. Keep expansive, intentional negative space. Reserve the lower <20–28>% as a clean, quiet, low-contrast, unobstructed typography-safe area.
Constraints: simplify scenery without changing the verified native structure. Remove fine texture, incidental clutter, heavy lighting, and hard cast shadows. Do not use hard contour lines.
Avoid: photorealism, 3D rendering, thick outlines, dense detail, decorative borders, seals, calligraphy, unrequested Chinese motifs, text, watermark, signature, logo, and extra ornaments.
```

## 后期文字规格

只在 `text_title` 与 `text_subtitle` 都由用户明确提供时使用。

```text
Canvas: keep the approved base image dimensions and aspect ratio.
Safe area: lower reserved area, horizontally centered; do not cover the subject.
Title: exact text “<text_title>”; elegant serif or handwriting-inspired Latin typeface; centered; medium visual weight.
Subtitle: exact text “<text_subtitle>”; small sans-serif Latin typeface; centered below the title with restrained spacing.
Color: sample a quiet dark neutral from the approved palette; no glow, outline, shadow, badge, or ornament.
```

## QA 硬门槛

- [ ] 比例、主体关系、构图主次和原生结构均可回查到参考图。
- [ ] 色彩保持整体调性而非逐色抄写；没有新增无依据的高饱和主色。
- [ ] 米白哑光纸底、块面平涂、淡墨晕染与松散边缘同时成立。
- [ ] 没有硬轮廓线、厚重光影、细碎纹理、杂物、印章、题跋、边框或多余装饰。
- [ ] 主体居中偏上，底部留白和文字安全区完整、无碰撞。
- [ ] 若有文字，标题和短句都与用户提供的字符串逐字一致；否则图片无文字。
- [ ] 没有签名、水印、Logo、原作特有角色或未经请求的作者模仿。

失败处理：结构问题重做事实卡；风格问题只调整材质、边线或光影；排版问题只在无字底图上重排文字。不要同时改动场景、配色和文字来掩盖失败。
