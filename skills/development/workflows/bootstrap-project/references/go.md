# Go bootstrap adapter

Use the Go adapter for one Go module that is either a library or CLI/application. New mode accepts only an absent or empty target. Existing mode accepts only the exact root of a Git repository with repository-local `.git` metadata.

## Resolve versions, module, and shape

Use the standard version priority: explicit user choice, then an exact existing repository constraint, then the current stable release verified from the responsible official source on the execution date. The packaged baseline was verified on 2026-08-14 with Go `1.26.6`, Lefthook `2.1.10`, and mise `2026.8.5`; treat these values as dated evidence.

New mode requires an exact Go version, exact Lefthook version, valid module path, lowercase project name, and `library` or `cli`. Existing mode preserves the module path from `go.mod`; its exact Go version may come from an explicit choice, existing mise pin, exact `toolchain` directive, or patch-level `go` directive. Every source must remain compatible with the `go` directive.

## Run the adapter

Use a fresh report path outside the target:

```sh
python3 <skill-directory>/scripts/bootstrap_go.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <project-name> \
  --module-path <module-path> \
  --go-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

For existing mode, omit `--name` and `--module-path`; `--shape` is optional but must agree when supplied. `--go-version` may be omitted only when an exact recognized repository constraint already resolves it.

New mode initializes Git without a commit, installs the exact mise tools, invokes official `go mod init`, validates that its only new file is `go.mod`, writes the selected minimal source and test skeleton, runs `go mod tidy`, installs Lefthook, and runs `mise run ci`.

Existing mode never runs `go mod init`, never rewrites `go.mod`, `go.sum`, sources, tests, README, or package layout, and uses `go mod tidy -diff` as its read-only module check. It accepts one module and one package boundary. A recognized CLI has one `cmd/<name>` thin entry plus a testable library package, which also prevents a single-main `go build` from writing an executable into the repository. Go workspaces, nested modules, asdf, Husky, pre-commit, custom hooks, and unknown baseline destinations are blocking conflicts.

## Generated quality baseline

- `install`: `go mod download`;
- `format`: recursively apply `gofmt -w` to non-vendored Go source;
- `format-check`: run `gofmt -d` over every non-vendored Go source without changing it;
- `check`: `go mod tidy -diff`;
- `lint`: `go vet -mod=readonly ./...`;
- `test`: `go test -mod=readonly -count=1 ./...`;
- `build`: `go build -mod=readonly ./...` over a library or multi-package thin-CLI layout, so no executable is written into the repository;
- serial `ci`: install, module check, format check, vet, test, then build;
- pre-commit: `piped: true` enforces stop-on-failure order across the partial-stage guard, staged gofmt and explicit restage, module metadata check, then vet. Full test and build remain outside the hook. The version-locked installer validates Lefthook's generated hook, adds the official `--no-stage-fixed` run flag, and scopes `MISE_TRUSTED_CONFIG_PATHS` to this hook process without persisting global trust; the staged helper reads NUL-delimited paths directly from the Git index;
- Ubuntu CI through the same `mise run ci` entry, immutable action SHAs, and Renovate coverage for mise, Go modules, Go directives, and Actions. Lockfile maintenance remains explicitly disabled; `go.sum` is checksum metadata, not a lockfile-maintenance target.

`GOTOOLCHAIN=local` prevents implicit toolchain downloads and `GOWORK=off` keeps the boundary on the selected single module. Go commands still use host or runner build, module, and temporary caches outside the repository.

## Failure semantics

`blocked` means a target, module, version, VCS, manager, hook, shape, source layout, or destination conflict prevented apply. `partial` means a known write or external command failed; retain the report, exact failed command, and partial changes. `completed` requires an installed hook, exact mise lock, a tidy module, a successful full gate, and—for new mode—an empty Git history.
