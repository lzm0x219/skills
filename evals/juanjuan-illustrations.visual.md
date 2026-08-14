# Juanjuan illustrations visual evaluation

This protocol covers evidence that `juanjuan-illustrations.behavior.json` cannot prove. The behavior runner checks instructions and final text only; it does not prove that an image was generated correctly.

## Preconditions

- Invoke the Skill explicitly with `$juanjuan-illustrations`.
- Use the bundled character reference only for internal visual testing while final-master and rights status remain unconfirmed.
- Save every output with a same-name `.prompt.md` record.
- Do not overwrite an existing artifact during evaluation.

## Deterministic artifact gate

Run this command for every scenario before visual review:

```sh
python3 skills/creative/juanjuan-illustrations/scripts/validate_artifact.py <image-path>
```

The command must exit with code 0. It verifies the PNG header and dimensions, a 16:9 relative-error tolerance of 1%, the same-name prompt record, required record sections, source-fact fields, `QA result: pass`, and the exact final output path. It does not inspect character identity, actions, paths, labels, or source meaning; those remain visual hard gates below.

## Scenario A: simple identity and action

Prompt: generate one no-text illustration for “消息没有消失，只是被塞进看不见的抽屉”.

Pass gates:

- one output image and one `.prompt.md` exist
- Juanjuan matches every identity invariant
- the character physically pushes the message object into the drawer
- no text, title, signature or watermark appears
- aspect-ratio error from 16:9 is at most 1%

## Scenario B: complex traceable relationships

Prompt: generate one scene where three distinct sources feed three threads through a routing device into three distinct destinations; require both hands to guide two named threads.

Pass gates:

- exactly three sources, three continuous paths and three destinations appear
- every path can be traced from its source to its destination
- both specified hands visibly contact the specified threads
- the routing device does not replace the required hand action
- the scene is physical and asymmetric rather than a card grid or teaching board

## Scenario C: Traditional Chinese domain fidelity

Prompt: use the source claim “同一；A 與 A 同、B 與 B 同；同聲相應是同類交易，同氣相求是等價交易” and allow only `同一`, `同聲`, `同氣`, `等價` as labels.

Pass gates:

- the source fact card preserves Traditional Chinese and all exact relationships
- only the four allowed labels appear, each exactly once and without extra characters
- A matches A, B matches B, and no unsupported A-to-B equivalence is shown
- the illustration remains one physical scene rather than a left-center-right information board

## Result record

Record for each scenario:

```markdown
- date:
- model/tool:
- image:
- prompt record:
- hard gates: pass | fail
- identity notes:
- source-fidelity notes:
- action/relationship notes:
- text notes:
- required retry:
```

Any failed hard gate makes the scenario fail. Do not average a hard failure into an overall visual-quality score.
