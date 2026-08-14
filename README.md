# Skills

[![Validation](https://badges.ws/github/workflow/lzm0x219/skills/validate.yml?style=flat-square&label=validation&labelColor=111827&icon=githubactions&iconColor=white)](https://github.com/lzm0x219/skills/actions/workflows/validate.yml)
[![Format: Agent Skills](https://badges.ws/badge/format-Agent%20Skills-7C3AED?style=flat-square&labelColor=111827&icon=markdown&iconColor=white)](https://agentskills.io/specification)
[![Install: npx skills](https://badges.ws/badge/install-npx%20skills-0EA5E9?style=flat-square&labelColor=111827&icon=npm&iconColor=white)](#install-and-start-using)
[![License: Apache-2.0](https://badges.ws/github/l/lzm0x219/skills?style=flat-square&labelColor=111827&color=111827&icon=apache&iconColor=white)](LICENSE)

Each skill here comes from a problem I actually hit, and the set grows as new needs appear. Skills follow the open [Agent Skills](https://agentskills.io/specification) format, so any compatible agent can load the same `SKILL.md`.

## Choose the right skill

When you are unsure whether to use a skill, start with the boundaries below. Explicit invocation is the most reliable path. Implicit matching depends on the agent and model, so this repo does not promise that installation alone guarantees automatic triggers.

### Engineering

**[`dsa-design`](skills/development/engineering/dsa-design/SKILL.md)** · `$dsa-design`

- **Good for:** data structure or algorithm choices that materially affect correctness, performance, resource bounds, interfaces, or maintenance cost
- **Not for:** pure copy edits, and routine CRUD with no material DSA trade-off

### Framework

**[`napi-rs`](skills/development/framework/napi-rs/SKILL.md)** · `$napi-rs`

- **Good for:** adopting, designing, implementing, debugging, testing, building, or publishing Rust Node-API addons with napi-rs
- **Not for:** tasks unrelated to Rust, Node-API, or napi-rs

### Languages

**[`zig`](skills/development/languages/zig/SKILL.md)** · `$zig`

- **适用于：** 设计、实现、调试、测试、优化、迁移、评审或维护 Zig 源码、构建、依赖、包和 C 互操作
- **不适用于：** 与 Zig 代码、构建配置、工具链或诊断无关的任务

### Tools

**[`mise`](skills/development/tools/mise/SKILL.md)** · `$mise`

- **Good for:** managing project tools, environment variables, tasks, lockfiles, CI, or IDE integration with mise
- **Not for:** tasks unrelated to the project development environment, tool versions, environment variables, or tasks

### Workflows

**[`bootstrap-project`](skills/development/workflows/bootstrap-project/SKILL.md)** · `$bootstrap-project` · manual invocation only

- **Good for:** creating new Zig or Rust libraries/CLIs, strictly completing recognized existing Zig or Rust baselines, or planning other supported targets
- **Current boundary:** applies to supported single-package Zig and Rust targets; TypeScript/Node.js, Python, and Go remain planning-only

When `napi-rs`, `zig`, and `mise` need exact APIs, CLI flags, target support, backends, or release flows, they return to the current official docs instead of treating skill-time knowledge as permanent fact.

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

Replace `napi-rs` with `bootstrap-project`, `dsa-design`, `mise`, or `zig` as needed. Check what is installed:

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
$bootstrap-project Inspect this existing project and prepare its initialization plan without writing files.
```

Without installing, you can also generate a one-shot prompt:

```sh
npx skills use lzm0x219/skills@napi-rs
```

## Understand the repository layout

The repository keeps each portable skill in a leaf directory under `skills/development/`. The surrounding evaluation, test, and workflow files validate repository-specific contracts.

```text
.
├── skills/
│   └── development/
│       ├── engineering/dsa-design/
│       ├── framework/napi-rs/
│       ├── languages/zig/
│       ├── tools/mise/
│       └── workflows/bootstrap-project/
├── capabilities/map.json
├── evals/
│   ├── fixtures/{bootstrap-project,dsa-design,mise,napi-rs,zig}/
│   ├── workspaces/bootstrap-project/
│   └── {bootstrap-project,dsa-design,mise,napi-rs,zig}.behavior.json
├── docs/behavior-evals.md
├── scripts/{run_behavior_evals,run_workspace_evals,validate_skills}.py
├── tests/test_{run_behavior_evals,run_workspace_evals,validate_skills}.py
└── .github/workflows/validate.yml
```

Each path has one role:

| Path                                 | Responsibility                                                                |
| ------------------------------------ | ----------------------------------------------------------------------------- |
| `skills/development/<area>/<skill>/` | Leaf package for a development skill, grouped by engineering area             |
| `skills/**/SKILL.md`                 | Portable entrypoint and discovery metadata for Agent Skills-compatible agents |
| `skills/**/agents/openai.yaml`       | Optional Codex UI metadata, default prompt, and implicit-invocation policy    |
| `skills/**/references/`              | Reference material loaded only when a task needs it                           |
| `skills/**/scripts/`                 | Deterministic helpers distributed with a skill                                |
| `evals/*.behavior.json`              | Behavior contracts, source assertions, and required scenarios                 |
| `evals/fixtures/<skill>/`            | Fixed answers that test the evaluation runner, not current model quality      |
| `evals/workspaces/<skill>/`          | Copied target fixtures and their expected path-level mutations                |
| `capabilities/map.json`              | Minimal registry for implemented Composite Skills and their safety boundaries |
| `docs/behavior-evals.md`             | Behavior-evaluation design and usage                                          |
| `scripts/`                           | Repository validators and the behavior-evaluation runner                      |
| `tests/`                             | Unit tests for repository validation and evaluation tooling                   |
| `.github/workflows/validate.yml`     | Required continuous integration checks                                        |

The category directories, `agents/openai.yaml`, and `evals/` are repository conventions. They are not required by the [Agent Skills specification](https://agentskills.io/specification). Agents that consume only the portable skill package need `SKILL.md` and any referenced `references/` or `scripts/` content.

## What validation can and cannot prove

Validation is split into four layers. Each layer answers a different question:

| Check                              | Can prove                                                                                                             | Cannot prove                                                                          |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Repository static validation       | Frontmatter, paths, links, optional Codex metadata, behavior contracts, and source assertions match repository rules  | The skill will give correct answers in a live model or every agent                    |
| Fixed-answer regression            | The behavior-eval runner and regex assertions stably recognize known outputs                                          | The current model still produces those outputs                                        |
| Live Codex evaluation              | The current Codex CLI, model, and skill satisfy the assertions on the final visible output for a scenario             | Other agents behave the same way, or the model did or did not load a skill internally |
| Isolated workspace evaluation      | A copied fixture's before/after manifest, command result, output, and expected path changes agree                     | The invoked command cannot affect anything outside the subprocess sandbox             |
| napi-rs/mise docs inventory checks | Local routing matches the official index at check time, and links are reachable                                       | Future versions or unrun platforms still work                                         |
| Zig official release check         | The official index currently identifies one latest stable release and its versioned documentation links are reachable | The compiler or a project works on any host, target, or future release                |
| Zig toolchain smoke                | The selected local compiler formats the fixture and its build-system test artifact actually executes                  | A real project, unsupported compiler, or target-specific runtime works                |

GitHub Actions runs static validation, runner unit tests, and fixed-answer regression. Default CI does not call a model or access official documentation and download websites.

## Run local checks

Run the offline checks before you commit. These commands use only repository files and the Python standard library:

```sh
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_behavior_evals.py \
  --skill bootstrap-project --answers evals/fixtures/bootstrap-project
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
python3 scripts/run_behavior_evals.py \
  --skill mise --answers evals/fixtures/mise
python3 scripts/run_behavior_evals.py \
  --skill zig --answers evals/fixtures/zig
```

Live behavior evaluation currently uses an authenticated Codex CLI and sends evaluation prompts plus skill content to the configured Codex service:

```sh
python3 scripts/run_behavior_evals.py --skill dsa-design
python3 scripts/run_behavior_evals.py --skill bootstrap-project
python3 scripts/run_behavior_evals.py --skill napi-rs
python3 scripts/run_behavior_evals.py --skill mise
python3 scripts/run_behavior_evals.py --skill zig
```

Workspace mutation evaluation uses a copied fixture and an explicit writable sandbox. Persist the report outside the temporary workspace:

```sh
python3 scripts/run_workspace_evals.py \
  --skill bootstrap-project \
  --case existing-zig-planning \
  --report-dir /tmp/bootstrap-project-eval-reports
```

Before refreshing or publishing official-document routing or Zig release claims, also run the network checks:

```sh
node skills/development/framework/napi-rs/scripts/verify-official-docs-coverage.mjs \
  --check --verify-links
node skills/development/tools/mise/scripts/verify-official-docs-inventory.mjs \
  --check --verify-links
node skills/development/languages/zig/scripts/verify-official-release.mjs \
  --check --verify-links
```

When a Zig compiler is available, validate the bundled fixture with every representative version in the declared support range:

```sh
node skills/development/languages/zig/scripts/run-toolchain-smoke.mjs \
  --zig /absolute/path/to/zig
```

See the [behavior evaluation notes](docs/behavior-evals.md) for scenarios, isolation, and limits.

## Add or change a skill

Every skill needs an executable quality path. When adding or changing one:

1. Maintain portable skill content in `skills/<category>/<skill-name>/SKILL.md`
2. Optionally provide Codex UI metadata and invocation policy in `agents/openai.yaml`
3. Define source assertions and required scenarios in `evals/<skill-name>.behavior.json`
4. Add `evals/fixtures/<skill-name>/<case-id>.txt` for each scenario
5. For workspace-writing behavior, add an isolated input and expectation under `evals/workspaces/<skill-name>/`
6. Register an implemented Composite in `capabilities/map.json`
7. Update the skill inventory and run all offline checks

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
