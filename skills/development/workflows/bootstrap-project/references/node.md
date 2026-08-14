# TypeScript and Node.js bootstrap adapter

Use the Node adapter for one ESM TypeScript package that is either a library or CLI/application. New mode accepts only an absent or empty target. Existing mode accepts only the exact root of a Git repository with repository-local `.git` metadata.

## Resolve versions and shape

Use the standard version priority: explicit user choice, then an exact existing package constraint, then the current stable release verified from the responsible official source on the execution date. The packaged baseline was verified on 2026-08-14 with Node.js LTS `24.19.0`, pnpm `11.21.0`, TypeScript `7.0.2`, Oxfmt `0.63.0`, Oxlint `1.78.0`, Vitest `4.1.10`, `@types/node` `24.13.3`, Lefthook `2.1.10`, and mise `2026.8.5`; treat these values as dated evidence.

New mode requires an exact version for every listed tool and dependency, a valid lowercase npm package name, and `library` or `cli`. Existing mode derives its shape from `bin`, `exports`, and the recognized `src` layout. It preserves compatible package scripts and configuration. Exact existing constraints take precedence and must agree with any explicit argument.

## Run the adapter

Use a fresh report path outside the target:

```sh
python3 <skill-directory>/scripts/bootstrap_node.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <package-name> \
  --node-version <x.y.z> \
  --pnpm-version <x.y.z> \
  --typescript-version <x.y.z> \
  --node-types-version <x.y.z> \
  --oxfmt-version <x.y.z> \
  --oxlint-version <x.y.z> \
  --vitest-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

For existing mode, omit `--name`. Version arguments may be omitted only when the same exact version already exists in the recognized package metadata. `--shape` is optional but must agree when supplied.

New mode initializes Git without a commit, writes the selected minimal ESM skeleton, installs exact mise tools, creates the pnpm lockfile, installs from that frozen lockfile, installs Lefthook, and runs `mise run ci`. Node and TypeScript do not provide a single official library/CLI scaffolder, so the adapter owns and tests the complete known template boundary.

Existing mode preserves sources, package scripts, README, and compatible TypeScript, Oxc, Vitest, and pnpm configuration. It performs a structured package metadata merge only for missing exact runtime and development dependency pins. npm, Yarn, Bun, Volta, Husky, pre-commit, Prettier, ESLint, and typescript-eslint are blocking migration conflicts rather than silent replacements.

## Generated quality baseline

- `format` and `format-check`: local Oxfmt, with check mode read-only;
- `lint`: local Oxlint with Vitest rules and warnings denied;
- `check`: strict `tsc --noEmit` under NodeNext ESM;
- `test`: one-shot `vitest run` with imported APIs;
- `build`: TypeScript emit of JavaScript, source maps, and declarations;
- serial `ci`: frozen install, format-check, lint, check, test, then build;
- pre-commit: `piped: true` enforces stop-on-failure order across the partial-stage guard, staged Oxfmt and explicit restage of only those files, whole-project Oxlint, then type-check; full tests and build remain outside the hook. Lefthook treats every `pre-commit` run as staged and normally hides unstaged changes before jobs. The version-locked installer validates its generated hook, adds the official `--no-stage-fixed` run flag, and scopes `MISE_TRUSTED_CONFIG_PATHS` to this hook process without persisting global trust. The formatter helper then reads NUL-delimited paths directly from the Git index, so the guard remains first even before the repository's initial commit;
- Ubuntu CI through `mise run ci`, immutable action SHAs, and Renovate coverage for mise, npm/pnpm, and Actions.

No Prettier, ESLint, typescript-eslint, or `node:test` dependency, configuration, or command is generated. A new CLI keeps `src/cli.ts` as a thin output boundary and puts tested logic in `src/index.ts`.

## Failure semantics

`blocked` means a target, package boundary, version, VCS, manager, hook, shape, or destination conflict prevented apply. `partial` means a known write or external command failed; retain the report, exact failed command, and partial changes. `completed` requires an installed hook, exact mise and pnpm lockfiles, a successful full gate, and—for new mode—an empty Git history.
