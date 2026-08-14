# Existing Zig baseline adapter

Use this adapter only for an existing, single-package Zig library at the exact root of a Git repository. Inventory remains read-only until every preflight check passes.

## Recognized input

The current adapter requires regular `build.zig.zon`, `build.zig`, `src/root.zig`, `mise.toml`, and `lefthook.yml` files. It preserves the project name, source tree, build graph, README, and existing exact Zig and Lefthook pins.

The Zig version in `mise.toml` must equal `.minimum_zig_version` in `build.zig.zon` and any Zig entry in `mise.lock`. Existing Lefthook lock entries must match its mise pin. A mismatch is a conflict, not a version-selection opportunity.

The build script must already connect its `test` step to `addRunArtifact`. The adapter does not rewrite an existing build graph. Its compile-only `check` task uses `zig test --test-no-exec -fno-emit-bin src/root.zig`; projects requiring dependency injection, a different root, or generated inputs are outside this slice.

## Conflict boundary

Stop before writes when any of these are present:

- asdf `.tool-versions`, Volta configuration, Husky, pre-commit, or an unrecognized existing pre-commit hook;
- A custom `core.hooksPath` other than the target-local `.git/hooks`;
- Unknown or conflicting required mise tasks;
- Lefthook content other than the exact recognized parallel formatter-plus-test legacy shape or the generated ordered shape;
- A symlink, non-regular file, or differing existing CI, Renovate, or partial-stage guard destination;
- A target that is not the exact Git root, or a linked worktree whose metadata is outside the target.

Report every detected conflict together. Do not partially migrate a target with unresolved conflicts.

## Run the adapter

Give the report a fresh path outside the repository:

```sh
python3 <skill-directory>/scripts/baseline_existing_zig.py \
  --target <absolute-repository-root> \
  --report <absolute-report-path>
```

The adapter then:

1. Adds `lockfile = true` only through a recognized mise settings structure;
2. Preserves compatible tasks and appends missing `format`, `format-check`, `lint`, `check`, `test`, `build`, and serial `ci` task tables;
3. Replaces only the exact recognized legacy Lefthook file with the ordered partial-stage guard, staged formatter and restage, staged lint, then quick compile check;
4. Creates only absent, known CI, Renovate, partial-stage guard, and lockfile paths;
5. Runs `mise install`, installs Lefthook into the target-local hooks directory, and runs `mise run ci`;
6. Compares before and after manifests, rejects unexpected mutations, and verifies preserved project-file hashes.

The operation is idempotent: rerunning a completed baseline produces no tracked-content changes.

## Interpret failure

`blocked` means preflight found a version, tool, structure, destination, or repository-boundary conflict before writes. `partial` means installation, hook setup, validation, or a postcondition failed after known changes began. Preserve partial evidence, name the exact failed command when one exists, and provide a targeted recovery step.
