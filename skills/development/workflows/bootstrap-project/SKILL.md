---
name: bootstrap-project
description: Plan a safe project scaffold or development-baseline initialization.
disable-model-invocation: true
---

# Bootstrap Project

Prepare a deterministic project-bootstrap plan while preserving user-owned work. This slice is planning-only: inspect the target and report the proposed changes, but stop before writing files, installing dependencies, initializing Git, or installing hooks.

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

Assign every relevant path exactly one operation:

- `create`: the path is absent and can be added without replacing user content;
- `merge`: the path has a known structure and each preserved field is identified;
- `preserve`: the path or behavior already satisfies the requirement or is outside scope;
- `conflict`: a user decision is required before any write.

Cover the prospective code skeleton, smoke test, exact version pins, mise tasks, Lefthook, GitHub Actions, `.github/renovate.json`, README, ignore rules, EditorConfig, dependency installation, lockfile generation, Git initialization, hook installation, and verification. For each item, name the evidence, intended path, operation, proposed command or content responsibility, and verification command. Do not use an empty task as a placeholder for an unsupported gate.

The planned version priority is user-specified version, then existing constraint, then current stable from an authoritative source. Record the source and the date checked whenever the last branch is used.

Complete this step only when every prospective write is classified and every conflict has a precise decision request.

## Report and stop

Return this compact result:

```text
Status: planned | blocked
Target: <absolute path>
Mode: new | existing
Stack: Zig | Rust | TypeScript/Node.js | Python | Go | unresolved
Shape: library | CLI/application | unresolved
Versions: <value, precedence branch, evidence>

Plan:
- <create|merge|preserve|conflict> <path> — <reason>; verify with <command>

Conflicts:
- <decision needed, or none>

Next step:
- Review the plan. This planning-only slice has not changed the target.
```

Use `blocked` when any conflict remains; otherwise use `planned`. Never describe inspection or planning as successful initialization.
