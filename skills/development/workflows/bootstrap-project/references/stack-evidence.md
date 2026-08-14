# Stack evidence

Read this reference only when the user did not explicitly name the stack or when an existing target must be checked for conflicting evidence.

## Evidence priority

Prefer committed manifests and toolchain constraints over source extensions, documentation prose, generated caches, installed hooks, or directory names. A manifest is evidence for a stack; it does not by itself prove library versus CLI/application shape.

| Stack              | Primary evidence                               | Shape evidence                                                                                |
| ------------------ | ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Zig                | `build.zig.zon`, `build.zig`                   | Exported modules suggest library; an installed executable artifact suggests CLI/application   |
| Rust               | `Cargo.toml`, optional `rust-toolchain.toml`   | `[lib]` or `src/lib.rs` suggests library; `[[bin]]` or `src/main.rs` suggests CLI/application |
| TypeScript/Node.js | `package.json`, `tsconfig.json`, pnpm lockfile | `exports` suggests library; `bin` suggests CLI/application                                    |
| Python             | `pyproject.toml`, uv lockfile                  | Import package metadata suggests library; project scripts suggest CLI/application             |
| Go                 | `go.mod`                                       | Importable packages suggest library; `package main` suggests CLI/application                  |

## Ambiguity rules

- Treat two primary manifests from different stacks as ambiguous unless the user names the target subproject.
- Treat multiple workspace members, packages, or modules as a monorepo boundary that requires an exact target.
- Treat README claims as supporting evidence only.
- Ignore build outputs, caches, virtual environments, vendored dependencies, and generated hook shims when identifying the stack.
- Preserve a declared version even when a newer stable release exists; report disagreement between primary manifests and environment-manager pins.
