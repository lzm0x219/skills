---
name: bootstrap-project
description: Create or plan a safe project scaffold and development baseline.
disable-model-invocation: true
---

# Bootstrap Project

Prepare a deterministic project-bootstrap plan while preserving user-owned work. This slice can apply supported new or strictly recognized existing Zig, Rust, and TypeScript/Node.js projects. Python and Go remain planning-only until their adapters are available.

## Establish the target boundary

Resolve the exact target directory first. Read every applicable repository instruction file whose scope includes that directory.

Accept only these v1 boundaries:

- One language and one package or module;
- Zig, Rust, TypeScript/Node.js, Python, or Go;
- A library or CLI/application shape;
- A new target or an existing project that needs its baseline completed.

Require the user to name the target subproject when the directory is a monorepo. Treat Git and mise as host prerequisites; report their absence without changing global shell configuration.

## Inventory before deciding

Use read-only inspection to record:

- Existing manifests, source layout, tests, lockfiles, repository instructions, CI, formatter, linter, type or compile checks, and build commands;
- Git state, including staged and unstaged changes, without modifying the index;
- Runtime and tool versions declared by the user or repository;
- Existing environment managers and hook systems, including asdf, Volta, Husky, and pre-commit;
- Evidence of multiple packages, modules, languages, or project shapes.

When the user did not explicitly provide the stack or shape, read [stack-evidence.md](references/stack-evidence.md). Ask one concise question when the evidence is ambiguous or a missing answer would change the plan. Do not infer a single target from conflicting evidence.

Complete this step only when every detected project fact is either recorded or called out as unknown.

## Resolve mode, stack, shape, and versions

Resolve facts in this order:

1. Use an explicit user choice.
2. Otherwise use one unambiguous existing project constraint.
3. Otherwise use the current stable release verified from an authoritative source at execution time.

Classify the mode as `new` only for an absent or intentionally empty target. Otherwise classify it as `existing` and preserve its source layout.

Treat any of these as a blocking conflict:

- More than one credible stack or package boundary;
- A monorepo without an exact target subproject;
- An existing alternative to mise or Lefthook that would require migration;
- Cross-file version constraints that disagree;
- An existing file that cannot be merged structurally without discarding unknown content;
- A requested service, Web, GUI, framework, multi-language, or multi-package shape.

Complete this step only when mode, stack, shape, version source, and every conflict have an evidence-backed value.

## Build the change plan

Classify every operation as `create`, `merge`, `preserve`, or `conflict`.

Assign every relevant path exactly one operation:

- `create`: the path is absent and can be added without replacing user content;
- `merge`: the path has a known structure and each preserved field is identified;
- `preserve`: the path or behavior already satisfies the requirement or is outside scope;
- `conflict`: a user decision is required before any write.

Cover the prospective code skeleton, smoke test, exact version pins, mise tasks, Lefthook, GitHub Actions, `.github/renovate.json`, README, ignore rules, EditorConfig, dependency installation, lockfile generation, Git initialization, hook installation, and verification. For each item, name the evidence, intended path, operation, proposed command or content responsibility, and verification command. Do not use an empty task as a placeholder for an unsupported gate.

The planned version priority is user-specified version, then existing constraint, then current stable from an authoritative source. Record the source and the date checked whenever the last branch is used.

Complete this step only when every prospective write is classified and every conflict has a precise decision request.

## Apply a supported plan

For a new Zig project, apply only when all of these are true:

- The user requested initialization rather than a plan-only inspection;
- The mode is `new`, the stack is Zig, and the shape is `library` or `CLI`;
- The exact target is absent or empty, the plan has no conflicts, and the project name is a valid lowercase Zig identifier;
- Git and mise are available on the host;
- Exact Zig and Lefthook versions have been resolved and their evidence recorded.

Read [zig.md](references/zig.md) completely before applying. Use the packaged `scripts/bootstrap_zig.py` adapter and assets; do not reproduce the files from memory or invoke `zig init` separately. Give `--report` a fresh path outside the target.

The adapter initializes Git without creating a commit, runs the official Zig initializer in an isolated project-name directory, preserves its package fingerprint, installs the exact mise tools and local hooks, and runs `mise run ci`. It trusts the new target only for its child mise processes through `MISE_TRUSTED_CONFIG_PATHS`; do not modify global mise trust or shell configuration.

Do not apply when the target becomes non-empty after inventory, an initializer output is unfamiliar, or any command fails. Do not delete partial output automatically. Use the report as the evidence boundary and surface the exact failed command.

For an existing Zig project, apply only when all of these are true:

- The user requested baseline completion rather than plan-only inspection;
- The target is the exact root of a single-package Zig library and an existing Git repository;
- `mise.toml` pins exact Zig and Lefthook versions, and Zig agrees with `build.zig.zon` and any existing `mise.lock`;
- `build.zig` proves that its `test` step uses `addRunArtifact`;
- There is no alternative environment or hook manager, unrecognized hook entry, custom hooks path, unknown Lefthook behavior, conflicting mise task, or unknown destination file.

Read [zig-existing.md](references/zig-existing.md) completely before applying. Use `scripts/baseline_existing_zig.py`; do not rerun `zig init`, move source, rewrite the build graph, or replace unknown configuration. The adapter only performs strict structural additions and the one recognized legacy Lefthook migration.

For Rust, read [rust.md](references/rust.md) completely before applying. Use `scripts/bootstrap_rust.py` for a new library or CLI, or for a strictly recognized existing single-package Rust library or CLI. New mode requires an absent or empty target, an exact Rust version, and an exact Lefthook version. Existing mode requires an exact Cargo `rust-version`, edition 2024, repository-local Git metadata, a recognized source shape, no alternative tool manager, and only absent or byte-identical baseline destinations.

The Rust adapter uses official `cargo init --vcs none`, keeps small source trees flat, gives a CLI a thin `main.rs` and testable `lib.rs`, preserves existing Cargo and source files, and runs rustfmt, Clippy, check, test, and build through locked Cargo commands. It never runs `cargo fmt` during initialization.

For TypeScript/Node.js, read [node.md](references/node.md) completely before applying. Use `scripts/bootstrap_node.py` for a new or strictly recognized existing single-package ESM TypeScript library or CLI/application. New mode requires an absent or empty target plus exact Node LTS, pnpm, TypeScript, `@types/node`, Oxfmt, Oxlint, Vitest, and Lefthook versions. Existing mode requires exact package constraints or matching explicit versions, repository-local Git metadata, recognized ESM sources and Vitest tests, no alternative manager or quality-tool migration, and only safe structured package metadata additions.

The TypeScript/Node.js adapter owns the complete library/CLI template because the official runtime and compiler do not provide one unified scaffold. It preserves existing sources, scripts, README, and compatible configuration; creates a frozen pnpm lockfile; and runs Oxfmt, Oxlint, strict `tsc --noEmit`, Vitest, and TypeScript emit through local exact dependencies. It never generates Prettier, ESLint, typescript-eslint, or `node:test` configuration, dependencies, or commands.

For Python, Go, or an unsupported existing Zig, Rust, or TypeScript/Node.js shape, return the plan and state that the matching apply adapter is not yet available. Never improvise an unsupported scaffold.

## Verify and report

After a completed adapter run, verify from the report and target that:

- Every public task required by the selected stack exists and `mise.lock` records its exact managed tool versions;
- `build.zig.zon`, `mise.toml`, and the CI toolchain agree on the Zig version;
- The test build step uses `addRunArtifact`, and `mise run ci` completed;
- Lefthook is installed and orders the partial-stage guard, staged formatter and restage, staged lint, then quick check without parallel execution;
- Pre-commit excludes the full test and build tasks;
- The Ubuntu workflow pins actions by full commit SHA and calls only `mise run ci`;
- `.github/renovate.json` exists without automerge or lockfile maintenance;
- Git has no commit.

For Rust, also verify that `Cargo.toml`, mise, and any preserved toolchain file agree on the exact Rust version; `Cargo.lock` exists; rustfmt, Clippy, check, test, and build all passed with `--locked` where applicable; library tests use `#[cfg(test)]`; and CLI logic is outside the thin entry point. Existing mode must report no unexpected Cargo, source, README, or project-layout mutation.

For TypeScript/Node.js, also verify that `package.json`, mise, and `pnpm-lock.yaml` agree on exact Node, pnpm, and local dependency versions; package modules are ESM; Oxfmt check, Oxlint, strict `tsc --noEmit`, Vitest, and build all passed; and no rejected formatter, linter, or test runner was generated. A CLI keeps behavior outside its thin `src/cli.ts` entry. Existing mode must report preserved sources, scripts, README, compatible configs, and package layout.

Return this compact result:

```text
Status: completed | partial | planned | blocked
Target: <absolute path>
Mode: new | existing
Stack: Zig | Rust | TypeScript/Node.js | Python | Go | unresolved
Shape: library | CLI/application | unresolved
Versions: <value, precedence branch, evidence>

Changes:
- created: <paths, or none>
- modified: <paths, or none>
- preserved: <paths, or none>

Conflicts:
- <decision needed, or none>

Verification:
- <command> — <passed|failed|not run>

Failed command:
- <exact argv, or none>

Next step:
- <recovery command, adapter boundary, or none>
```

Use `blocked` when a conflict prevents apply, `partial` when a write or external command fails after apply begins, `planned` when the stack has no apply adapter or the user requested planning only, and `completed` only when every verification passes. Never describe inspection or planning as successful initialization.
