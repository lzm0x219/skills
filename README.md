# Skills

[![Validation](https://badges.ws/github/workflow/lzm0x219/skills/validate.yml?style=flat-square&label=validation&labelColor=111827&icon=githubactions&iconColor=white)](https://github.com/lzm0x219/skills/actions/workflows/validate.yml)
[![Format: Agent Skills](https://badges.ws/badge/format-Agent%20Skills-7C3AED?style=flat-square&labelColor=111827&icon=markdown&iconColor=white)](https://agentskills.io/specification)
[![Install: npx skills](https://badges.ws/badge/install-npx%20skills-0EA5E9?style=flat-square&labelColor=111827&icon=npm&iconColor=white)](#install-and-start-using)
[![License: Apache-2.0](https://badges.ws/github/l/lzm0x219/skills?style=flat-square&labelColor=111827&color=111827&icon=apache&iconColor=white)](LICENSE)

Each skill here comes from a problem I actually hit, and the set grows as new needs appear. Skills follow the open [Agent Skills](https://agentskills.io/specification) format, so any compatible agent can load the same `SKILL.md`.

## Choose the right skill

When you are unsure whether to use a skill, start with the boundaries below. Explicit invocation is the most reliable path. Implicit matching depends on the agent and model, so this repo does not promise that installation alone guarantees automatic triggers.

### Engineering

**[`dsa-design`](skills/engineering/dsa-design/SKILL.md)** · `$dsa-design`

- **Good for:** data structure or algorithm choices that materially affect correctness, performance, resource bounds, interfaces, or maintenance cost
- **Not for:** pure copy edits, and routine CRUD with no material DSA trade-off

### Framework

**[`napi-rs`](skills/framework/napi-rs/SKILL.md)** · `$napi-rs`

- **Good for:** adopting, designing, implementing, debugging, testing, building, or publishing Rust Node-API addons with napi-rs
- **Not for:** tasks unrelated to Rust, Node-API, or napi-rs

**[`mise`](skills/framework/mise/SKILL.md)** · `$mise`

- **Good for:** managing project tools, environment variables, tasks, lockfiles, CI, or IDE integration with mise
- **Not for:** tasks unrelated to the project development environment, tool versions, environment variables, or tasks

When `napi-rs` and `mise` need exact APIs, CLI flags, target support, backends, or release flows, they return to the current official docs instead of treating skill-time knowledge as permanent fact.

## Install and start using

Prefer the [Vercel Labs Skills CLI](https://github.com/vercel-labs/skills) to discover and install skills. It places skills into the directories your agents already read (Claude Code, Codex, Cursor, OpenCode, and many others). List available skills first without changing the project:

```sh
npx skills add lzm0x219/skills --list
```

### Install into the current project

Install one skill for every agent the CLI detects:

```sh
npx skills add lzm0x219/skills --skill napi-rs --agent '*'
```

Or install for specific agents only:

```sh
npx skills add lzm0x219/skills \
  --skill napi-rs \
  --agent claude-code cursor codex
```

Omit `--agent` to let the CLI choose interactively from detected agents.

### Install globally

Use the same skill across projects:

```sh
npx skills add lzm0x219/skills \
  --skill napi-rs --agent '*' --global
```

### Install everything

Install all skills from this repository to all agents (skips prompts):

```sh
npx skills add lzm0x219/skills --all
```

Replace `napi-rs` with `dsa-design` or `mise` as needed. Check what is installed:

```sh
npx skills list
npx skills list --global
npx skills list --agent claude-code
```

`npx` may download the third-party `skills` CLI on first run. Before installing, use `--list` and review the target skill's `SKILL.md`, scripts, and related assets. Keep interactive confirmation on by default; add `--yes` only in automation where the source is fixed and the content has already been reviewed.

### Use a skill

Invocation syntax varies by agent. Many tools accept an explicit `$skill-name` mention; others rely on description matching. If a newly installed skill does not appear, restart the agent session, then try an explicit call:

```text
$napi-rs Review this addon's async, lifetime, and release boundaries without changing code.
$mise Design reproducible tools, environment variables, and a test task for this project without modifying files.
```

Without installing, you can also generate a one-shot prompt:

```sh
npx skills use lzm0x219/skills@napi-rs
```

## Understand the repository layout

The repository follows the base directory model defined by the [Agent Skills specification](https://agentskills.io/specification). Optional Codex UI metadata and this repo's behavior-evaluation conventions sit alongside the portable skill content.

```text
.
├── skills/
│   ├── engineering/dsa-design/
│   └── framework/
│       ├── mise/
│       └── napi-rs/
├── evals/
│   ├── fixtures/
│   └── *.behavior.json
├── tests/
├── scripts/
└── .github/workflows/validate.yml
```

Different files own different responsibilities:

| Path | Responsibility |
| --- | --- |
| `skills/**/SKILL.md` | Portable entrypoint for any Agent Skills-compatible agent; frontmatter is used for discovery, and the body loads only when the skill is used |
| `skills/**/agents/openai.yaml` | Optional Codex UI metadata, default prompts, and implicit-invocation policy |
| `skills/**/references/` | Reference material loaded by task need, so `SKILL.md` does not have to hold everything |
| `skills/**/scripts/` | Deterministic checks or helper tools |
| `evals/*.behavior.json` | Machine-readable behavior contracts, source assertions, and required scenarios |
| `evals/fixtures/` | Fixed answers used by CI to verify the assertion runner, not current model quality |
| `tests/`, `scripts/` | Validate repository structure, evaluation isolation, and contract execution logic |

`agents/openai.yaml` and `evals/` are conventions of this repository, not required files in the open Agent Skills specification. Agents that only consume `SKILL.md` (plus `references/` and `scripts/`) do not need them.

## What validation can and cannot prove

Validation is split into four layers. Each layer answers a different question:

| Check | Can prove | Cannot prove |
| --- | --- | --- |
| Repository static validation | Frontmatter, paths, links, optional Codex metadata, behavior contracts, and source assertions match repository rules | The skill will give correct answers in a live model or every agent |
| Fixed-answer regression | The behavior-eval runner and regex assertions stably recognize known outputs | The current model still produces those outputs |
| Live Codex evaluation | The current Codex CLI, model, and skill satisfy the assertions on the final visible output for a scenario | Other agents behave the same way, or the model did or did not load a skill internally |
| napi-rs/mise docs inventory checks | Local routing matches the official index at check time, and links are reachable | Future versions or unrun platforms still work |

GitHub Actions runs static validation, runner unit tests, and fixed-answer regression. Default CI does not call a model and does not access the official napi-rs or mise websites.

## Run local checks

Run the offline checks before you commit. These commands use only repository files and the Python standard library:

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
python3 scripts/run_behavior_evals.py \
  --skill mise --answers evals/fixtures/mise
```

Live behavior evaluation currently uses an authenticated Codex CLI and sends evaluation prompts plus skill content to the configured Codex service:

```sh
python3 scripts/run_behavior_evals.py --skill dsa-design
python3 scripts/run_behavior_evals.py --skill napi-rs
python3 scripts/run_behavior_evals.py --skill mise
```

Before refreshing or publishing the `napi-rs` or `mise` official-docs inventory, also run the network checks:

```sh
node skills/framework/napi-rs/scripts/verify-official-docs-coverage.mjs \
  --check --verify-links
node skills/framework/mise/scripts/verify-official-docs-inventory.mjs \
  --check --verify-links
```

See the [behavior evaluation notes](docs/behavior-evals.md) for scenarios, isolation, and limits.

## Add or change a skill

Every skill needs an executable quality path. When adding or changing one:

1. Maintain portable skill content in `skills/<category>/<skill-name>/SKILL.md`
2. Optionally provide Codex UI metadata and invocation policy in `agents/openai.yaml`
3. Define source assertions and required scenarios in `evals/<skill-name>.behavior.json`
4. Add `evals/fixtures/<skill-name>/<case-id>.txt` for each scenario
5. Update the skill inventory and run all offline checks

`description` should say both what the skill does and when to use it. Put longer material in `references/`, put deterministic tools in `scripts/`, and do not make `SKILL.md` carry background that is irrelevant to the current task.

The current validator locks required scenarios for listed skills. When you add a skill, also register its case categories and invocation modes in `scripts/validate_skills.py`.

## Compatibility and limits

- **Portable surface:** `SKILL.md`, `references/`, and `scripts/` follow the Agent Skills format and are the primary interface for all agents.
- **Optional metadata:** `agents/openai.yaml` improves Codex UI discovery and defaults; other agents can ignore it.
- **Quality gates:** Live behavior evaluation and some validation paths currently run against Codex. That is a repository quality harness, not a hard requirement for end users installing skills into Claude Code, Cursor, OpenCode, or other supported agents.
- **Agent differences:** Discovery paths, script permissions, and implicit invocation still vary by agent. After install, verify the skill appears in your agent and prefer explicit invocation when reliability matters.

A skill is task guidance and tooling, not a runtime security boundary. Before running scripts, going online, publishing, or changing external systems, still check the code, credential scope, and user authorization.

## License

This repository is licensed under the [Apache License 2.0](LICENSE).
