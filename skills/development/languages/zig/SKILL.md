---
name: zig
description: "Build, modify, debug, test, optimize, migrate, and review Zig applications and libraries. Use for `.zig` source, coding style, API design, `build.zig`, `build.zig.zon`, dependencies, the Zig build system, `comptime`, allocators and ownership, error unions, C interoperability, cross-compilation, performance diagnostics, compiler diagnostics, and Zig package maintenance. Coding style, best practices, syntax, standard library APIs, Build API, compiler options, and target behavior must match the target Zig version; when neither the user nor the repository specifies a version, query the Zig website and use the latest stable release at that time."
---

# Zig development

## General workflow

### Establish the repository and version boundaries

- Before proposing changes, read the repository instructions, `git status`, `build.zig`, `build.zig.zon`, version-pinning files, adjacent source, and tests.
- Determine the task's target Zig version or supported range in this order: an explicit user requirement; otherwise repository version pins, manifest constraints, CI configuration, or the project toolchain; when none of that evidence exists, query the official Zig [Download](https://ziglang.org/download/) or [Learn](https://ziglang.org/learn/) page and use the latest stable release at that time.
- Distinguish the minimum version, supported range, active compiler version, and formatter version. A lower bound such as `minimum_zig_version` is not an exact pin. When a project supports multiple versions, preserve its CI matrix and select an explicit compiler for each verification run. By default, verify at least the minimum supported release and the latest stable release within the supported range.
- Use the formatter version specified by the repository. When none is specified separately, run `zig fmt` with the compiler used for the current verification. If different compilers produce different formatting, follow the repository-specified version and report the difference.
- When there is no version evidence, do not use a version number from memory or treat master/nightly as the "latest version"; target master/nightly only when the user explicitly requests a development release.
- When Zig is available locally, compare `zig version` with the target version. If the local version conflicts with the user or repository version, treat it as a different environment rather than migrating the project automatically.
- If the official website is unavailable and there is no other version evidence, report that the latest stable release could not be verified and request version information instead of silently falling back to a historical release.
- Preserve the compiler versions and existing conventions supported by the project. Treat a newer local compiler as a different environment, not as a reason to migrate the project automatically.
- When the request is unrelated to Zig source, build configuration, toolchains, or diagnostics, complete it directly without introducing Zig-specific process.

Complete this step when the target files, supported version range, active compiler, formatter version, version evidence, existing command entrypoints, and request scope are all explicit.

### Use version-matched evidence

For exact syntax, standard library APIs, Build API, compiler options, target behavior, or version compatibility, rely on official evidence that matches the target version:

- Use `zig env` and the standard library source bundled with the installed compiler to verify the toolchain actually in use.
- To confirm the current stable release on the official website, run the [official release verification script](scripts/verify-official-release.mjs); add `--verify-links` before publishing or refreshing version data. This network check proves only the state of the official index and links at query time.
- For a stable release, use the target version's [language reference](https://ziglang.org/documentation/), its Style Guide, standard library documentation, release notes, and compiler-bundled source. Use master documentation only when the user explicitly targets master. Do not let another version's Style Guide override the target version's rules.
- Use the official [build system guide](https://ziglang.org/learn/build-system/) for concepts, then verify the API against the target compiler; the Build API evolves continuously.
- Use `zig <command> --help` and the build steps and options declared by the project instead of applying options remembered from another version.
- When the language reference is insufficient, inspect the official Zig source and label conclusions derived from source as implementation details.

When reporting a version-sensitive conclusion, state the target version, the basis for choosing it, and the documentation source, and distinguish verified facts, engineering defaults, and migration recommendations.

### Load task-specific rules

- When writing, refactoring, or reviewing Zig code, or when the user asks about best practices, coding style, runtime safety, or illegal behavior boundaries, read [Coding best practices and style](references/best-practices-and-style.md).
- When modifying `build.zig`, `build.zig.zon`, dependencies, package metadata, version constraints, or the Zig version, read [Builds, dependencies, and version migrations](references/build-packages-and-migrations.md).
- When using C headers, C libraries, `@cImport`, `zig translate-c`, `extern`, callbacks, or data across an ABI, read [C interoperability boundaries](references/c-interop.md).

Complete this step after performing the checks required by the detailed rules and reflecting every applicable boundary in the design, implementation, and verification plan.

### Design ownership and failure paths

- Define the public contract, error behavior, allocation strategy, and lifetime boundaries before implementation.
- Make the owner and release mechanism of every allocation explicit. Prefer caller-provided allocators at reusable boundaries, and pair cleanup with resource acquisition using `defer` or `errdefer`.
- Distinguish borrowed slices from owned slices through names, documentation, or return types. Copy data when it must outlive its backing storage.
- Keep error unions meaningful and handle expected failures explicitly. Use `catch unreachable` only for invariants already proven at that location.
- Use optionals for absence and error unions for failure; preserve that distinction across adapters and public APIs.

Complete this step when every return value, allocation, borrowed view, error, and cleanup path has an explicit owner and a testable contract.

### Make build and test evidence explicit

- Treat `build.zig` as executable project code; `zig build --help` also loads the build graph. For an untrusted project, inspect build scripts, dependency declarations, and every reachable system-command step before running any `zig build` subcommand.
- Derive step names and `-D` options from the current `build.zig` and `zig build --help`, and preserve the project's existing target and optimization option model.
- Distinguish a test artifact that compiled from one that executed and one that passed. Confirm that the test step depends on the step that runs the artifact; report tests as passing only after the artifact actually runs and succeeds.
- Before dependency resolution, downloads, global toolchain changes, package publication, or other out-of-scope external side effects, make the impact explicit and confirm authorization.

Complete this step when the build steps, test execution path, dependency side effects, and success criteria can all be explained.

### Apply measurement-driven performance optimization

- Establish a reproducible performance baseline first, fixing the Zig version, target, optimization mode, inputs, warm-up procedure, execution environment, and sampling method.
- Locate the bottleneck before proposing a change; vary one major factor at a time while retaining correctness tests.
- Repeat measurements under the same conditions and report the distribution or variance rather than comparing only the single fastest result.
- Treat compile time, binary size, memory, throughput, and latency as separate metrics; optimize only the metrics the user cares about and that have been measured.

Claim a performance improvement only when the baseline, bottleneck evidence, post-change measurements, and correctness regression results are all available.

### Implement the smallest compatible change

- Follow adjacent code and every applicable rule in [Coding best practices and style](references/best-practices-and-style.md).
- Keep the first change small enough that one targeted compile or test can reject it quickly.
- Add tests next to the behavior they protect; cover failure and cleanup paths for allocation or I/O changes.
- Run `zig fmt` only on modified Zig paths; use `zig fmt --check` for a read-only check.
- Preserve the existing language version and change boundary unless the request includes a version migration or broad rewrite.

Complete this step when the code, tests, and documentation contain only the smallest compatible change required by the request.

### Expand verification in layers

Prefer the repository's existing commands. Otherwise, expand verification only within the range supported by the project:

1. Run `zig fmt --check` on modified Zig files.
2. Run the smallest applicable `zig test` command, or run a named `zig build` test step and verify that it actually executes the test artifact.
3. Run the project build and remaining tests with the compiler pinned by the project.
4. When a change affects portability, safety, ABI, or performance, cover the target and optimization combinations declared by the project.
5. Run generated binaries or integration tests in a compatible environment. A successful cross-compilation does not prove correctness on the target runtime.

When validating this skill's minimal examples, run the [toolchain smoke script](scripts/run-toolchain-smoke.mjs) for each representative toolchain. It checks formatting, the build graph, and actual test execution in an isolated temporary directory; it does not replace the target repository's test matrix.

Report the exact Zig version, commands, target, optimization mode, and observations. Mark `compiled`, `executed`, `passed`, and currently unavailable checks separately.

## Diagnostic order

1. Reproduce the failure with the project-pinned compiler and the smallest command.
2. Read the first causal diagnostic and its compile-time reference trace before addressing later errors.
3. Classify the failure as language semantics, version drift, ownership/lifetime, `comptime` evaluation, build graph, dependency resolution, C ABI/linking, target behavior, or performance regression.
4. Narrow the failing boundary while preserving the relevant allocator, target, optimization mode, and external dependencies.
5. For disputed behavior, check the version-matched language reference, local standard library source, Build API, release notes, or compiler source.
6. Handle caches only when evidence points to them; scope the action to a specific project or isolated cache path and preserve unrelated artifacts.

Conclude with the root cause, the smallest verified fix, regression coverage, and any platform, runtime, or performance boundary that remains unverified.
