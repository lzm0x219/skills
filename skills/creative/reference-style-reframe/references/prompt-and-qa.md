# 提示词与质检模板

先完整填写画面取证卡。不要把没有从参考图中看见的对象、方位、文字或色彩写成事实。

```text
source_aspect_ratio: <例如 3:4；以实际参考图为准>
subject_and_relationship: <主体、动作或景物间必须保留的关系>
composition: <主体位置、远近层次、必要裁切和留白分布>
native_structure: <2–4 个决定识别的结构>
palette_groups: <2–5 个综合色组；说明明暗和冷暖关系>
style_profile: <ink-wash-flat | gongbi-traditional | gouache-matte | paper-collage | soft-pastel | linocut-editorial | risograph-editorial | colored-pencil-storybook | folk-papercut | minimal-vector-poster；未指定时 ink-wash-flat>
style_intensity: <restrained | balanced | pronounced；未指定时 balanced；横向对照固定 pronounced>
scene_mode: <standard | portrait-figure | product-still-life | dense-narrative；未指定时 standard>
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
Primary request: Reconstruct the reference as an editorial illustration in the selected style_profile. Preserve the reference aspect ratio, subject hierarchy, native structure, and overall color relationships.
Scene route: <copy the selected section's prompt constraints from references/scene-routes.md; for standard write none>
Style profile: <copy the selected Prompt addendum from references/style-profiles.md exactly; use one profile only>
Style intensity: <style_intensity>. Restrained follows the source closely; balanced gives the profile clear presence; pronounced makes the selected profile's material, edge, and layer rules unmistakable while preserving P0/P1 and composition.
Structure and detail: preserve every P0 core structure. Preserve every item in p1_recognition_details and the selected scene route's required invariants as a legible profile-appropriate secondary shape, color cluster, layered paper shape, pastel mass, or limited hatch group. Do not flatten P1 into one generic silhouette. Obey the selected profile's edge budget; do not add universal outlines.
Composition: when scene_mode=standard, place the main subject centered slightly above the midpoint and keep expansive, intentional negative space. For every other scene route, preserve the recorded people, products, or event-zone layout; never move, crop, or merge P0/P1 just to center the subject or create negative space. For text_area=reserved, reserve the lower <20–28>% as a clean, quiet, low-contrast, unobstructed typography-safe area. For text_area=overlay, use only existing quiet negative space and never cover P0 or P1. For text_area=none, do not intentionally create a lower typography-safe band.
Constraints: simplify scenery without changing P0 or p1_recognition_details. Remove only P2 microtexture, incidental clutter, heavy lighting, and hard cast shadows. Do not import another profile's texture, stroke, palette system, or edge treatment.
Avoid: photorealism, 3D rendering, decorative borders, seals, calligraphy, unrequested Chinese motifs, text, watermark, signature, logo, extra ornaments, artist imitation, and mixing style profiles.
```

## 后期文字规格

只在 `text_title` 与 `text_subtitle` 都由用户明确提供时使用。

```text
Canvas: keep the approved base image dimensions and aspect ratio.
Placement: for text_area=reserved, use the lower reserved area, horizontally centered. For text_area=overlay, use the approved existing negative space. Do not cover P0 or P1.
Title: exact text “<text_title>”; use the selected profile's typography direction; centered; medium visual weight.
Subtitle: exact text “<text_subtitle>”; use the selected profile's typography direction at small size; centered below the title with restrained spacing.
Color: sample a quiet dark neutral from the approved palette; no glow, outline, shadow, badge, or ornament.
```

## QA 硬门槛

- [ ] 比例、主体关系、构图主次和 P0 核心结构均可回查到参考图。
- [ ] 每一项 P1 识别细节都可独立辨认，并以所选档案允许的小块面、色组、纸层、粉蜡笔色团或刻线组呈现，而非被抹成单一轮廓。
- [ ] P2 以外的细节没有被当作“简化”误删；除非数量有识别意义，不强加精确数量。
- [ ] 色彩保持整体调性而非逐色抄写；没有新增无依据的高饱和主色。
- [ ] 所选风格档案的纸张、色层、纹理密度、边缘预算和排版方向同时成立，且没有混入其他档案的标志性处理。
- [ ] `style_intensity` 与结果一致；`pronounced` 的档案差异清晰可见，仍不牺牲 P0/P1 或构图关系。
- [ ] P1 遵守所选档案的次要边缘预算；没有不属于该档案的连续深色闭合描边或密集纹理。
- [ ] 没有厚重光影、P2 以外的细碎纹理、杂物、印章、题跋、边框或多余装饰。
- [ ] `standard` 主体居中偏上；其他场景路由保留取证卡中的人、产品或事件分区布局，且没有为了居中或留白移动、裁掉或合并 P0/P1。`reserved` 的文字安全区完整、`overlay` 没有碰撞 P0/P1、`none` 没有被人为切出底部文字带。
- [ ] 若有文字，标题和短句都与用户提供的字符串逐字一致；否则图片无文字。
- [ ] 没有签名、水印、Logo、原作特有角色或未经请求的作者模仿。

失败处理：结构问题重做事实卡；细节丢失时只补回 P1 的缺项；边缘或纹理问题只按所选档案修正；文字区问题只调整 `text_area` 或排版；风格问题只调整所选档案的材质、色层或光影。不要同时改动场景、配色和文字来掩盖失败。
