# Rust bootstrap adapter

Use the Rust adapter for one edition-2024 Cargo package that is either a library or CLI. New mode accepts only an absent or empty target. Existing mode accepts only the exact root of a Git repository with repository-local `.git` metadata.

## Resolve versions and shape

Use the standard version priority: explicit user choice, then an exact existing Cargo or Rust toolchain constraint, then the current stable release verified from official Rust sources on the execution date. The packaged baseline was verified on 2026-08-14 with Rust `1.97.1`, Lefthook `2.1.10`, and mise `2026.8.5`; treat these as dated evidence.

New mode requires a lowercase Cargo package name, exact Rust and Lefthook versions, and `library` or `cli`. Existing mode derives the name, shape, and Rust version from `Cargo.toml` and `src/lib.rs`/`src/main.rs`. An existing `rust-toolchain.toml` or `rust-toolchain` is preserved only when its exact channel agrees with Cargo.

## Run the adapter

Use a fresh report path outside the target:

```sh
python3 <skill-directory>/scripts/bootstrap_rust.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <package-name> \
  --rust-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

For existing mode, omit `--name` and normally omit `--rust-version`; an explicitly supplied version must agree with Cargo. `--shape` is optional but must agree when supplied.

New mode initializes Git without a commit, pins the local hooks path, installs the mise toolchain, runs official `cargo init --edition 2024 --vcs none`, validates its output boundary, then replaces only those known generated files with the selected minimal templates.

Existing mode never runs `cargo init`. It preserves `Cargo.toml`, `Cargo.lock` when present, Rust sources, README, toolchain files, and layout. It creates baseline destinations only when absent or already byte-identical. asdf, Husky, pre-commit, conflicting toolchains, linked worktrees, and differing baseline files are blocking conflicts.

## Generated quality baseline

- `format`: `cargo fmt --all`;
- `format-check`: `cargo fmt --all --check`;
- `lint`: Clippy for all targets and features with warnings denied;
- `check`, `test`, and `build`: all targets and features with `--locked`;
- serial `ci`: format-check, lint, check, test, then build;
- pre-commit: partial-stage guard, staged rustfmt and restage, project Clippy, then quick Cargo check; full test and build remain outside the hook;
- Ubuntu CI through the same `mise run ci` entry, immutable action SHAs, and Renovate coverage for mise, Cargo, and Actions.

Small libraries remain flat. New CLI projects keep `main.rs` as a thin output boundary and place tested logic in `lib.rs`. Unit tests live under `#[cfg(test)]` and use behavior-descriptive names.

## Failure semantics

`blocked` means a target, version, VCS, tool-manager, Cargo, shape, or destination conflict prevented apply. `partial` means a known write or external command failed; retain the report, exact failed command, and partial changes. `completed` requires an installed hook, a generated lockfile, a successful full gate, and—for new mode—an empty Git history.
