# 风格档案

每次只选一个档案。所有档案都保留画面取证卡、P0/P1/P2 与 `text_area`；下面内容只定义可变化的视觉语言。除非用户明确要求并图中可见，不添加新的符号、人物、文字或装饰。

## 复杂 P1 转写

遇到车轮辐条、砖缝、密集枝叶、栏杆或重复瓦片时，先保留轮廓、方向和少数识别节点，再删除重复细线；不要把原图的每一根线都当作 P1。`ink-wash-flat`、`gouache-matte` 与 `soft-pastel` 用外形、主轴和少量色团；其中粉彩的圆形物体只留外圈与主轴，不保留辐条或同心内线。`paper-collage` 用剪纸缺口和纸层；`gongbi-traditional` 用轮廓、主轴和有限的细线组；`linocut-editorial` 用留白与短方向刻线；`risograph-editorial` 用一个主轮廓、少量色点和套印错位；`colored-pencil-storybook` 用少量定向色铅笔线与色层，类似自行车的圆形 P1 只留外圈、车架和不超过三条主结构线，不保留辐条；`folk-papercut` 用外轮廓和必要镂空；`minimal-vector-poster` 用几何形与负空间。对所有档案，复杂 P1 的重复线条都属于 P2，除非其数量或节奏本身已被列为 P1。

## `ink-wash-flat`

适合克制、留白充足的旅行与建筑图文；也是默认档案。

**Prompt addendum**

```text
Material and layering: warm off-white matte specialty paper; relaxed opaque flat color blocks for P0; sparse pale-ink blooms only for atmosphere and depth. Keep naturally loose broken edges and a restrained academic editorial finish.
Detail and edge budget: render P1 as low-contrast color clusters, paper gaps, or broken pale-ink marks. Do not enclose P1 in continuous dark contour lines; allow a light edge only at a necessary local P0 overlap or contact.
Typography direction: elegant serif or handwriting-inspired Latin title with a small restrained sans-serif subtitle.
```

QA: 淡墨必须稀疏、服务层次；不得变成稠密水彩纹理或泛化“国风”装饰。

## `gongbi-traditional`

适合需要清晰细节、平稳设色与克制传统绘画秩序的花鸟、园林、建筑与静物。

**Prompt addendum**

```text
Material and layering: fine warm ivory xuan-paper texture; controlled even fine ink outlines for P0 and selected P1, followed by thin mineral-pigment color layers, gentle fenran tonal transitions, and restrained zhaoran glazing. Keep pigments clear, flat-to-gently-modeled, and non-photorealistic.
Detail and edge budget: preserve P1 with precise but varied fine lines, small pigment groups, and limited tonal layering. Do not turn every surface into a black outline, loose ink wash, dense realistic shading, or a repetitive decorative pattern.
Typography direction: restrained Song-style serif title with a small neutral sans-serif subtitle; use no calligraphy, seal, inscription, or antique-paper simulation unless the user explicitly supplies it.
```

QA: 细线应服务形体和 P1，设色应薄而清晰；不得混入泼墨、水彩纸边、版画刻线、现代拼贴阴影、题跋、印章或仿古复制效果。

## `gouache-matte`

适合色彩关系鲜明、需要更饱满块面的风景、静物和街景。

**Prompt addendum**

```text
Material and layering: warm uncoated paper with opaque matte gouache layers; use broad soft-edged color masses, a few visible dry-brush transitions, and restrained value steps. Keep the finish flat and tactile, not glossy or photorealistic.
Detail and edge budget: render P1 with two or three simplified opaque color shapes or short dry-brush separations. Do not use black perimeter lines, transparent watercolor washes, or dense individual brush hairs.
Typography direction: quiet old-style serif title with a compact neutral sans-serif subtitle.
```

QA: 水粉应呈不透明、哑光、色块优先；不应混入墨晕、水彩透明渐变或塑料般高光。

## `paper-collage`

适合强调层次、形状和材质差异的建筑、静物与叙事场景。

**Prompt addendum**

```text
Material and layering: compose the scene from warm matte colored-paper layers, with deliberate cut or gently torn edges and subtle paper-fiber variation. Use overlapping paper planes to organize P0; preserve a calm editorial collage finish.
Detail and edge budget: render P1 as small layered paper pieces, cut notches, or paper gaps. Keep overlap shadows nearly absent and soft; do not simulate thick 3D craft, black outlines, glue, tape, or random scrap clutter.
Typography direction: refined serif title with a simple geometric sans-serif subtitle, printed flat on the paper.
```

QA: 能看出层叠纸片和受控纸边，但不应像立体手工卡片；纸纹不可压过 P1 或变成杂乱拼贴。

## `soft-pastel`

适合柔和光线、季节感和安静叙事，特别适合自然与生活场景。

**Prompt addendum**

```text
Material and layering: warm lightly toothed paper; large chalky soft-pastel masses with gentle rubbed transitions and a very small amount of pastel dust. Preserve soft value grouping and breathable paper gaps.
Detail and edge budget: render P1 as muted pastel masses, short rubbed accents, or small color shifts. Avoid dark line drawing, individual pencil strokes, shiny highlights, and excessive powder texture.
Typography direction: soft serif title with a light humanist sans-serif subtitle.
```

QA: 粉蜡笔应有颗粒但仍由大色团主导；类似自行车的复杂 P1 仅保留车架和每轮一圈不闭合或弱化的色带，不能画出辐条、内圈或机械线稿；不得退化成铅笔素描、写实喷枪或脏灰噪点。

## `linocut-editorial`

适合强构图、有限色版和更有张力的建筑、植物与风景图文。

**Prompt addendum**

```text
Material and layering: ecru uncoated paper with two to four flat ink colors, high-contrast P0 silhouettes, and a small number of directional carved hatch groups that follow form. Keep an editorial printmaking finish with slight hand-printed irregularity.
Detail and edge budget: use a limited dark keyline only to clarify selected P0 silhouette breaks. Render P1 with short hatch groups, small flat ink shapes, or negative-space cuts; do not fully enclose every P1 object, add dense crosshatching, or use photographic shading.
Typography direction: compact high-contrast serif title with a small uppercase or neutral sans-serif subtitle.
```

QA: 必须是有限色、刻线有方向且有留白的版画感；地面、水面等大平面应以一两块实色或留白处理，不能被横向排线铺满；允许局部 P0 主轮廓，但不得把每个 P1 物体包成黑色线稿。

## `risograph-editorial`

适合需要鲜明印刷节奏、轻微失准感与有限套色的旅行、街景和静物图文。

**Prompt addendum**

```text
Material and layering: warm uncoated paper printed with two to four spot-color risograph layers. Use controlled coarse halftone only in one or two selected P0 planes, occasional small registration offsets at selected P0 edges, and flat overlapping inks; leave all other planes and the paper background clean.
Detail and edge budget: render P1 with a key contour, small dot clusters, or one additional spot-color shape. Keep misregistration subtle and local; do not use photographic shading, smooth digital gradients, dense all-over grain, or black outlines around every object.
Typography direction: compact grotesk or old-style serif title with a small utilitarian sans-serif subtitle, printed as a flat spot-color layer.
```

QA: 套色应限定在 2–4 色，粗颗粒只服务一两块 P0，纸张底色和其余色面保持干净；不得变成满版噪点、数码渐变、CMYK 写实印刷或故意做旧的脏污纸。

## `colored-pencil-storybook`

适合花园、日常静物、动物和轻叙事场景，需要比粉彩更清晰的线性手绘感。

**Prompt addendum**

```text
Material and layering: warm lightly textured drawing paper with translucent colored-pencil layers, visible but sparse directional strokes, and preserved paper white. Build P0 from broad softly burnished color masses, then use a few coordinated pencil strokes for selected P1.
Detail and edge budget: render P1 with broken colored contour fragments, small directional hatching groups, or gentle color shifts. Keep every stroke purposeful; do not use waxy crayon fills, broad pastel smudges, dark graphite drawing, dense crosshatching, or photorealistic rendering.
Typography direction: warm literary serif title with a small humanist sans-serif subtitle, lightly printed rather than hand-lettered.
```

QA: 彩铅线必须有方向、可数且服务 P1，纸白仍可呼吸；自行车等圆形复杂 P1 只留外圈和车架，不能出现辐条；不得混成粉彩涂抹、蜡笔蜡感、黑白素描或密集铅笔毛刺。

## `folk-papercut`

适合花果、鸟兽、门窗与民居剪影等轮廓明确的题材，以当代平面方式借用民间剪纸的镂空关系。

**Prompt addendum**

```text
Material and layering: warm matte paper with two or three solid cut-paper colors, crisp hand-cut silhouettes, and deliberate negative-space openings. Use the source's own geometry to organize cuts; keep the result flat, balanced, and contemporary rather than festive by default.
Detail and edge budget: render P1 only as meaningful cutouts, notches, or one additional solid-color layer. Do not add generic auspicious symbols, symmetry, borders, seals, lanterns, or unrelated ornamental patterns; avoid 3D paper sculpture, drop shadows, and tiny filigree.
Typography direction: restrained serif title with a small neutral sans-serif subtitle, printed flat and separate from the cut shapes.
```

QA: 镂空须帮助识别 P0/P1，而非填满装饰；色数有限、边缘平整但略带手工感，不得凭空添加吉祥图案、红色铺满或立体纸雕阴影。

## `minimal-vector-poster`

适合主体关系清楚、需要最干净现代图文秩序的建筑、山海、器物与旅行场景。

**Prompt addendum**

```text
Material and layering: warm off-white matte paper with a restrained vector-poster system of four to six flat color shapes, clean negative space, and controlled geometric alignment. Every shape has one uniform opaque color with no tonal variation; preserve the source palette relationship while simplifying values into clear planes.
Detail and edge budget: render P1 as a small geometric inset, one thin local separator, or a distinct color block only when it preserves recognition. Avoid paper grain, brush marks, halftones, gradients, realistic shadows, and universal perimeter strokes.
Typography direction: refined display serif title or clean modern sans-serif title with a compact neutral sans-serif subtitle; place both as flat graphic elements.
```

QA: 必须呈现少量、清晰且可解释的平面几何关系与留白；每个色块内部必须纯平，无渐变或半透明阴影；不得混入纸纹、笔触、版画颗粒、厚光影或给所有物体描边。
