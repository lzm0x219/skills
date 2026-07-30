---
name: napi-rs
description: "Build, modify, debug, test, package, or review Rust Node-API addons with napi-rs. Use for adoption or migration, #[napi] exports, Rust/JavaScript type conversion, classes, functions, errors, buffers, lifetimes, async and threads, CLI, packaging, cross-compilation, WebAssembly, compatibility, testing, publishing, and troubleshooting. When versioned APIs, CLI flags, target support, or publish behavior are involved, consult current official napi-rs documentation first."
---

# napi-rs general workflow

Complete Rust Node-API addon work using the current project's language, package manager, and build conventions. Do not assume a specific repository, crate name, domain model, test data, or release platform. When the request is unrelated to Rust, Node-API, or napi-rs, complete the original task directly and do not emit this skill's process or terminology.

## Establish boundaries first

1. Inspect existing Rust crates, Node packages, build scripts, support matrix, and user authorization. Do not scaffold, migrate, publish, or change public APIs merely because this skill is in use.
2. Define the JavaScript contract first: export names, parameters and return values, sync or async semantics, error shape, generated `.d.ts`, module loading, and compatibility commitments.
3. If the project already has an independent core crate, keep Node-API code as a thin adapter layer. Do not copy business rules, I/O policy, or domain models into the binding layer. An independent addon does not need an extra crate split just to follow that pattern.

## Use current official documentation

1. For unfamiliar or version-sensitive tasks, first read the [official documentation inventory](references/official-documentation-inventory.md), then open the official pages for the capabilities you touch.
2. When CLI, Cargo features, target platforms, WASI, publishing, or migration are involved, always treat the current official pages as authoritative. Do not infer exact flags, versions, or support matrices from this skill.
3. Run `node scripts/verify-official-docs-coverage.mjs --check` only when refreshing the inventory or claiming that local material still fully covers the official site; add `--verify-links` before publishing or after documentation refreshes.

| Work | Prefer these official topics |
| --- | --- |
| Adopt an existing project, create a package, use the `napi` CLI | Introduction, CLI |
| `#[napi]`, functions, classes, enums, type declarations, errors | Exports and JavaScript API |
| Value conversion, `Env`, `this`, references, buffers, Promise, lifetimes | Values, conversion, and lifetime management |
| `async fn`, `AsyncTask`, thread callbacks, Tokio | Async and concurrency |
| Cargo features, prebuilt artifacts, cross-compilation, WASI | Build, targets, and WebAssembly |
| Runtime loading, bundlers, testing, crashes, or platform failures | Quality, integrations, and troubleshooting |
| Versions, artifacts, npm publish, or v2/v3 migration | Release, migration, and historical context |

Read pages according to the capabilities you actually touch. For example, when exporting an async `TypedArray`, also read the async, typed array, lifetime, error handling, and export/type conversion pages.

## Keep boundaries safe

- Validate inputs, paths, option combinations, and resource bounds at the JavaScript boundary. Keep export names, `.d.ts`, loaders, and `package.json` consistent.
- Map expected errors to stable, actionable, machine-readable JavaScript errors. By default do not expose credentials, absolute paths, or raw internal errors.
- Use Node-API handles and borrowed JavaScript values only within their `Env` and lifetime. Do not store them in long-lived Rust state or send them across workers or threads.
- Do not perform expensive CPU, filesystem, network, or external-process work on the JavaScript main thread. Choose `async fn`, `AsyncTask`, or `ThreadsafeFunction` according to current official guidance, and hand only owned Rust data to background work.
- Unless the public contract says otherwise, do not change the deterministic order, precision, or error classification provided by the core layer inside the binding layer.

## Implement and verify

1. When the project has configured Rust commands, run formatting, Clippy, and Rust tests. Do not invent a workspace structure that is not present.
2. Build artifacts with the project's configured napi CLI or the commands from current official docs. Import the addon from the final package with Node integration tests covering at least one success path, one invalid input or expected error path, and every new async behavior.
3. Claim support for a Node.js, OS, CPU, libc, runtime, or WASI combination only when you have both a generated artifact and a real import test in a clean environment. Node-API ABI compatibility alone is not enough.
4. Separate cross-platform, loader, bundler, or performance conclusions from the actual test matrix. Keep unrun combinations as unverified.
5. Treat `napi pre-publish`, `napi prepublish`, npm publish, GitHub releases, and artifact uploads as external side effects. Do not run them without the user's explicit authorization.

## Local resources

- [Official documentation inventory](references/official-documentation-inventory.md): capability routing and scope notes for current official Docs/Blog pages.
- [Coverage verifier](scripts/verify-official-docs-coverage.mjs): compares the local inventory with the official `llms.txt`/sitemap and can verify link reachability.
