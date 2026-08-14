# Zig bootstrap adapter

Use this adapter only for a new, single-package Zig library or CLI in an absent or empty target on macOS or Linux.

## Resolve inputs

Record the absolute target, lowercase project identifier, shape, and exact versions before writing. Version precedence is explicit user choice, then an existing constraint, then the current stable release verified from authoritative sources on the execution date.

The packaged baseline was verified on 2026-08-14 with Zig `0.16.0`, Lefthook `2.1.10`, mise `2026.8.5`, `actions/checkout` `v7.0.1`, and `jdx/mise-action` `v4.2.5`. Treat this as dated evidence, not a permanent default. When choosing current versions, recheck the official Zig, Lefthook, mise, and action release sources.

The project name must match `[a-z][a-z0-9_]*`. If a desired display name does not match, ask for the package identifier rather than silently rewriting it.

## Run the adapter

Create a fresh report path outside the target, then run:

```sh
python3 <skill-directory>/scripts/bootstrap_zig.py \
  --target <absolute-target> \
  --name <project_identifier> \
  --shape <library|cli> \
  --zig-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

Do not pre-create files in the target. The adapter refuses a non-empty target before running Git or mise.

The adapter performs these boundaries in order:

1. `git init`, with no commit;
2. Render the common baseline and create `mise.lock`;
3. `mise install` with target-scoped `MISE_TRUSTED_CONFIG_PATHS`;
4. `mise exec -- zig init` in a temporary child named after the project, validate its exact four-file output, and preserve its fingerprint;
5. Render the selected library or CLI build and smoke-test sources;
6. Run the version-locked hook installer into the target-local `.git/hooks`;
7. `mise run ci`.

The project-name initializer directory matters because Zig validates the package fingerprint against the package name. Do not run the initializer in an unrelated directory and then replace only `.name`.

## Generated baseline

Both shapes receive:

- Exact Zig and Lefthook pins in `mise.toml` and `mise.lock`;
- Real `format`, `format-check`, `lint`, `check`, `test`, `build`, and serial `ci` tasks;
- A test step connected to `addRunArtifact`, so tests execute rather than only compile;
- Ordered Lefthook jobs: partial-stage guard, staged `zig fmt` with explicit restage, staged per-file `zig ast-check`, and `mise run check`;
- README, ignore rules, EditorConfig, an Ubuntu GitHub Actions workflow with immutable action SHAs, and `.github/renovate.json`;
- No license, contribution guide, commit, push, external App authorization, automerge, or lockfile maintenance.

The installer validates Lefthook's generated hook, adds `--no-stage-fixed`, and scopes `MISE_TRUSTED_CONFIG_PATHS` to the repository root for that hook process. It does not persist global trust. The formatter helper reads NUL-delimited paths from the Git index, prefixes formatter arguments with `./`, and restages only those exact files. The partial-stage guard therefore runs before any formatter and rejects a tracked file whose index and worktree columns are both changed.

## Interpret the report

`completed` means the full adapter and `mise run ci` succeeded. `partial` means the target may contain useful output, but an initializer, install, hook, or validation command failed. `blocked` means validation stopped before supported initialization could proceed.

On `partial`, report the exact `failed_command`, retain the target for inspection, and give a command-specific retry or recovery step. Do not claim completion and do not delete the partial target automatically.
