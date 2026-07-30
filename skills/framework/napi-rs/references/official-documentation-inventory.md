# napi-rs official documentation full-coverage inventory

> Snapshot: 2026-07-29 (Asia/Shanghai). This inventory is a page directory for task routing and coverage audits, not an offline copy of API syntax. When implementing, still open the corresponding official pages to confirm current version details.

## Authoritative entry points and capture method

- The official site's [robots.txt](https://napi.rs/robots.txt) points to [sitemap.xml](https://napi.rs/sitemap.xml). This snapshot cross-checked the sitemap, site sidebar, and per-page HTTP `200` responses: Docs has **50** English canonical pages; Simplified Chinese and pt-BR each have the same set of **50** localized pages, for **150** Docs URLs total.
- The official machine-readable entry is [llms.txt](https://napi.rs/llms.txt). It lists Docs, Blog, and Changelog by site navigation and is useful for rediscovering pages during documentation refreshes.
- Structural sources live in the napi-rs-maintained [website repository](https://github.com/napi-rs/website): the snapshot's [Docs navigation metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json) defines 6 Docs sections, and the [navigation generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs) generates sidebars for three languages from the English structure. Full source trees: [content/docs](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs) and [content/blog](https://github.com/napi-rs/website/tree/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog).

### Routing rules and counts

- Below lists **50 English canonical Docs URLs** and **3 English canonical Blog URLs**; each URL is a separate capability/topic entry.
- Every Docs path below has an English `https://napi.rs/docs/` prefix and corresponding localized pages under `https://napi.rs/cn/docs/` and `https://napi.rs/pt-BR/docs/`. Localized pages are not additional capabilities, so the 100 mirror URLs are not repeated. This rule is defined jointly by the [official route-map generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-route-map.mjs) and the [Docs navigation generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/build-nav.mjs).
- `https://napi.rs/docs` itself is not a topic page; use the actual leaf routes. A page's `.md` form is a machine-readable representation of the same page, not an extra capability page; see the [sitemap generator](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/scripts/generate-sitemap.mjs).

## Classification, inclusion policy, and full page map

Inclusion policy meaning: **core** = durable safety boundaries/workflows that should be condensed into the skill; **topic reference** = local reference index loaded by task, not a substitute for the official site; **online lookup** = strongly version-, CLI-, target-, or publish-dependent; open the official page before acting.

### 1. Getting started and project adoption (3 pages; core + topic reference)

Keep the core flow of "thin Node adapter, define the JS contract first, do not scaffold/publish without authorization". Confirm template steps and dependency versions online per task.

- [Getting started](https://napi.rs/docs/introduction/getting-started) — Create, build, and test a napi-rs v3 package from a template.
- [Build your first package](https://napi.rs/docs/introduction/simple-package) — Complete first-package build, test, and pre-publish preparation.
- [Manual setup](https://napi.rs/docs/introduction/manual-setup) — Manually adopt napi-rs in an existing Rust crate, JavaScript package, or workspace.

### 2. JavaScript exports and public API (11 pages; topic reference)

These pages determine the Rust/JS public contract, generated TypeScript, and error semantics. Skill core keeps only "write the contract first, stable naming, classifiable errors"; attribute combinations and conversion rules must be looked up online per page.

- [Exports](https://napi.rs/docs/concepts/exports) — Control how Rust functions, classes, and constants export to JavaScript.
- [Module Initialization](https://napi.rs/docs/concepts/module-init) — Run custom initialization when Node loads the native module.
- [Naming conventions](https://napi.rs/docs/concepts/naming-conventions) — Define name conversion rules between Rust and JavaScript.
- [`#[napi]` attributes](https://napi.rs/docs/concepts/napi-attributes) — Reference all public `napi-derive` attributes and their runtime and TypeScript effects.
- [Class](https://napi.rs/docs/concepts/class) — Define and export a Rust `struct` as a JavaScript class.
- [Enum](https://napi.rs/docs/concepts/enum) — Map Rust enums to JavaScript string unions or numeric enums.
- [Object](https://napi.rs/docs/concepts/object) — Pass plain JavaScript objects between Rust and Node.
- [Function](https://napi.rs/docs/concepts/function) — Define, receive, and call JavaScript function values.
- [Error handling](https://napi.rs/docs/concepts/error-handling) — Handle thrown, rejected, retained, and classified errors for sync/async APIs.
- [Types Overwrite](https://napi.rs/docs/concepts/types-overwrite) — Override generated TypeScript declarations.
- [Type conversions](https://napi.rs/docs/concepts/type-conversions) — Describe the conversion matrix, direction, ownership, and required features.

### 3. Values, memory, lifetimes, and low-level Node-API (11 pages; topic reference; online lookup when handles are involved)

Skill core should enforce "do not store Node-API handles or borrowed JS values in Rust state or send them across threads". Specific traits, lifetimes, `Env` APIs, zero-copy behavior, and feature requirements follow only the current official pages.

- [Values](https://napi.rs/docs/concepts/values) — High-level conversion entry between Rust and JavaScript values.
- [TypedArray](https://napi.rs/docs/concepts/typed-array) — Work with JavaScript TypedArray primitives and Rust data.
- [Understanding Lifetime](https://napi.rs/docs/concepts/understanding-lifetime) — Explain lifetimes of JavaScript values and Rust borrow boundaries.
- [`Reference` / `WeakReference`](https://napi.rs/docs/concepts/reference) — Create and use strong/weak object references.
- [External](https://napi.rs/docs/concepts/external) — Carry Rust native values with `External` on JavaScript objects.
- [Env](https://napi.rs/docs/concepts/env) — Access low-level Node-API environment, value creation, cleanup, and memory interfaces.
- [Inject Env](https://napi.rs/docs/concepts/inject-env) — Inject Node-API `Env` into exported functions and methods.
- [Inject This](https://napi.rs/docs/concepts/inject-this) — Inject the JavaScript `this` receiver into bound APIs.
- [Cargo features](https://napi.rs/docs/concepts/cargo-features) — Select Node-API level, async, conversion, diagnostic, and compatibility features.
- [Promise](https://napi.rs/docs/concepts/promise) — Represent and await JavaScript Promise from Rust.
- [Iterators and async iterators](https://napi.rs/docs/concepts/iterators) — Implement Generator and AsyncGenerator JavaScript iteration protocols.

### 4. Async, threads, and concurrency (4 pages; core + topic reference)

Core should fix "do not block the JavaScript main thread, send only owned Rust data to workers, and use supported mechanisms for non-JS-thread callbacks". Runtime, cancellation, and shutdown details require reading this group's full pages.

- [async fn](https://napi.rs/docs/concepts/async-fn) — Run exported Rust `async fn` on the Tokio runtime.
- [AsyncTask](https://napi.rs/docs/concepts/async-task) — Run work on the libuv thread pool and handle `AbortSignal` cancellation.
- [ThreadsafeFunction](https://napi.rs/docs/concepts/threadsafe-function) — Safely call JavaScript callbacks from other threads.
- [Async and concurrency](https://napi.rs/docs/more/async-concurrency) — Choose APIs and safety boundaries for cancellation, JS access, workers, and runtime shutdown.

### 5. CLI, build artifacts, and publishing (13 pages; topic reference + online lookup)

CLI options, generated templates, platform package layout, npm permissions, and GitHub releases can change by version. Core keeps only "test claimed runtimes, publishing commands need explicit authorization, publish is not transactional". Open the touched pages online before executing.

- [New](https://napi.rs/docs/cli/new) — Create a project from maintained Yarn/pnpm templates.
- [Rename](https://napi.rs/docs/cli/rename) — Rename a project and related generated assets.
- [Build](https://napi.rs/docs/cli/build) — Use `napi build`, cross-compile flags, actual build commands, and environment.
- [NAPI Config](https://napi.rs/docs/cli/napi-config) — Configure builds, generated bindings, targets, and WASI output.
- [Programmatic API](https://napi.rs/docs/cli/programmatic-api) — Customize builds through the `@napi-rs/cli` programmatic API.
- [Create npm directories](https://napi.rs/docs/cli/create-npm-dirs) — Create platform npm package directories.
- [Artifacts](https://napi.rs/docs/cli/artifacts) — Collect CI build artifacts into platform packages.
- [Universalize](https://napi.rs/docs/cli/universalize) — Merge into a universal binary.
- [Version packages](https://napi.rs/docs/cli/version) — Update versions of created platform packages.
- [Pre Publish](https://napi.rs/docs/cli/pre-publish) — Version, publish, and attach platform packages; this has network and registry side effects.
- [Release native packages](https://napi.rs/docs/deep-dive/release) — Explain multi-platform package build, verification, publish, and partial-failure recovery.
- [Native module](https://napi.rs/docs/deep-dive/native-module) — Explain what a native module is and how Node loads/runs it.
- [WebAssembly and WASI](https://napi.rs/docs/concepts/webassembly) — Build, package, test, and run Node/browser WASI fallbacks.

### 6. Target platforms and cross-compilation (3 pages; online lookup)

Target triples, glibc, SDKs, linkers, Node-API ABI, and continuous test matrices are time-sensitive facts. Do not freeze them into the skill.

- [Cross build](https://napi.rs/docs/cross-build) — Host/target decision matrix, target recipes, glibc, C/C++ dependencies, and Docker image migration.
- [Support and compatibility](https://napi.rs/docs/more/support-compatibility) — Distinguish Node-API ABI, tested runtimes, and napi-rs target support.
- [Cross-build FAQ](https://napi.rs/docs/more/faq) — Common cross-compile and native loading issues.

### 7. Testing, integration, and troubleshooting (3 pages; core + topic reference)

Core should require Rust tests, Node import integration tests, and real runtime verification for every claimed platform. Specific bundlers, frameworks, debuggers, and error symptoms are looked up per page.

- [Testing and debugging](https://napi.rs/docs/more/testing-debugging) — Test addons at the Rust/JavaScript boundary and debug native code in Node.
- [Integrations and bundlers](https://napi.rs/docs/more/integrations) — Load addons in CJS, ESM, bundlers, frameworks, Electron, and serverless.
- [Troubleshooting](https://napi.rs/docs/more/troubleshooting) — Diagnose outward from failure layers for build, loader, platform, TypeScript, async, and WASI.

### 8. Migration and background (3 Docs pages + 3 Blog pages; online lookup)

Use this section for version upgrades, legacy project compatibility, and understanding the origin of unsafe older APIs. It does not replace current Concepts & reference pages.

- [V2 to V3 Migration Guide](https://napi.rs/docs/more/v2-v3-migration-guide) — Configuration, CLI, type, and compatibility migration from napi-rs v2 to v3.
- [History](https://napi.rs/docs/deep-dive/history) — Background on Node native addon evolution.
- [Functions and Callbacks in NAPI-RS](https://napi.rs/blog/function-and-callbacks) — Background and patterns for function and callback bindings.
- [Announcing NAPI-RS v3](https://napi.rs/blog/announce-v3) — Records v3 lifetime, ThreadsafeFunction, and migration context.
- [Announcing NAPI-RS v2](https://napi.rs/blog/announce-v2) — Records historical v2 change context.

## Coverage completeness and known limits

### Verified coverage

- This file enumerates all **50/50** English canonical Docs pages from the official Docs sidebar: Introduction 3, Concepts & reference 26, CLI 10, Deep dive 3, Cross build 1, Guides & help 7. Sections and order can be rechecked against the [Docs metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/docs/_meta.en.json).
- It also enumerates all **3/3** pages from the official Blog navigation; that is the full public set in the [Blog metadata](https://github.com/napi-rs/website/blob/889b288021b7bb385687fd6ffa4d478752cad03c/content/blog/_meta.en.json).
- Therefore the directory covers the current publicly executable capability docs: **53/53** canonical Docs/Blog routes. The 100 Docs localization mirrors are covered by the same routing rules. The live discovery entry remains [llms.txt](https://napi.rs/llms.txt).

### Boundaries and refresh rules

- Changelog is a versioned historical release log, not a stable capability reference. When you need a crate/CLI version change, enter from the official [Changelog](https://napi.rs/changelog/napi) online; do not compress it into the skill's behavior rules.
- This inventory does not copy full Rust API function signatures and does not guarantee that a feature works on your Node, CPU, libc, WASI runtime, or CLI version. That is why Cargo features, Support and compatibility, Cross build, and related CLI pages should be consulted online during a task.
- After the official site adds, removes, renames pages, or changes navigation, the 53 count becomes invalid. On refresh, re-enumerate from [llms.txt](https://napi.rs/llms.txt), [sitemap.xml](https://napi.rs/sitemap.xml), and the official [website source](https://github.com/napi-rs/website), keep canonical HTTPS URLs one by one, and only claim full coverage again after links are reachable.
