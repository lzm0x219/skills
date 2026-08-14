# 生图与编辑提示词

## 单张生成模板

把尖括号替换为当前任务信息。把 `../assets/juanjuan-character-reference-v3.png` 作为图像参考传入，不要只靠文字重画角色。

从 `character-dna.md` 注入当前身份不变量，从 `style-dna.md` 注入当前风格约束；不要在本文件维护第二份角色清单。

```text
Use case: editorial illustration with strict identity and source fidelity
Asset type: near-16:9 Chinese article body illustration
Reference image: Use the provided Juanjuan reference as the strict identity, costume, palette, proportion, and medium reference. Do not redesign the character.
Identity block: <copy the current identity invariants from character-dna.md without summarizing or improvising>

Source core claim: <core_claim>
Exact source terms: <exact_terms>
Unsupported inferences to avoid: <unsupported_inferences>

Physical metaphor: <one readable object-action metaphor>
Character action: <one exact action Juanjuan must perform>
Required body contacts: <body part -> exact object; use none only when truly irrelevant>
Required object counts: <exact counts>
Required relationships and directions: <exact matching, sequence, direction, or separation>
Required traceable paths: <start -> intermediate -> end, or none>

Composition: <single scene / before-after / light path / 2–4 panel comic>. Use one focal action, asymmetric depth, generous negative space, and a main subject occupying about 40–65% of the frame.
Scene elements: <2–5 necessary elements only>

Allowed Chinese labels: <exact 0–5 label whitelist>
Source script: <traditional / simplified / mixed / none>. Preserve the source script exactly. Render no title, paragraph, explanation, watermark, signature, or other text.

Visual style block: <copy the relevant style-dna constraints>
Avoid: identity drift, passive mascot posing, substituted actions, wrong counts, broken paths, unsupported symbolism, PPT cards, left-center-right teaching boards, regular grids, dense diagrams, flat vectors, 3D, photography, anime rendering, or extra text.
```

## 关键文字的两阶段流程

1. 先把 `Allowed Chinese labels` 设为 `none`，生成无字底图。
2. 确认身份、动作、数量、对应和路径全部通过 QA。
3. 逐个局部加入白名单文字，保持原文繁简体。
4. 逐字核对；任何额外字符都必须删除。

## 局部编辑模板

```text
Edit the provided illustration. Change only: <precise edit>. Preserve every other character feature, object, count, relationship, path, label, position, aspect ratio, paper texture, and color. Do not add new text, props, characters, titles, logos, signatures, or watermarks.
```

## 加入精确文字

```text
Edit the provided no-text illustration. Add only the exact text “<allowed label>” at <location>, preserving its original Traditional or Simplified Chinese form. Add no other characters, title, callout, underline, logo, signature, or watermark. Preserve everything else exactly.
```

## 去除错误文字

```text
Edit the provided illustration. Remove only the text “<exact text>” and its attached underline or callout. Reconstruct the same warm cream paper and subtle grain behind it. Preserve everything else exactly. Do not add replacement text or new objects.
```

## 身份漂移时重生成

```text
Regenerate the illustration from the Juanjuan reference. Preserve the approved source fact card, action, constraints and composition, but restore the complete identity block copied from character-dna.md. Do not patch the drifted character or reinterpret the design.
```

## 同名记录模板

每张最终图片保存一个同名 `.prompt.md`：

```markdown
# <image filename>

## 来源锚点

<原文摘录或明确位置>

## 来源事实卡

core_claim: <本图唯一要表达的原文判断>
exact_terms: <必须原样保留的术语；没有则写 none>
required_relationships: <必须画对的关系；没有则写 none>
required_counts: <必须画对的数量；没有则写 none>
unsupported_inferences: <不得补写的含义；没有则写 none>
script: <traditional | simplified | mixed | none>
allowed_labels: <精确标签白名单；没有则写 none>

## 最终提示词

<实际传给图像工具的提示词>

## 参考与工具

- reference: <相对路径>
- tool: <工具与模式>

## QA

- result: pass | fail
- notes: <逐项结果>

## 迭代记录

<生成、编辑或重生成记录；没有则写 none>

## 最终输出

<图片绝对路径>
```
