# Zig builds, dependencies, and version migrations

Use the target Zig version established in `SKILL.md`. When neither the user nor the repository provides a version, query the Zig website in real time and use the current latest stable release. Base every Build API, manifest, dependency, and migration decision below on that target version.

## Discover the build contract

- Confirm the Zig version before reading `build.zig`, `build.zig.zon`, and version-pinning files.
- Treat `build.zig` as executable code. Before running an untrusted build, inspect dependencies, system commands, generation steps, and possible network or filesystem side effects.
- After reviewing the trust boundary, use the target version's `zig build --help` to obtain the steps and `-D` options actually declared by the project. This command also loads `build.zig`, so it is not a safe probe for an unreviewed project. A step named `test` is not a built-in promise that the step exists or runs tests.
- Keep the build graph declarative: use it to connect artifacts, modules, generated inputs, dependencies, tests, runs, and installation while keeping domain logic in ordinary Zig modules.

## Confirm that tests actually execute

1. Locate where the test artifact is created.
2. Locate the step that runs the artifact; verify against the target Build API that it runs the test artifact rather than merely compiling it.
3. Confirm that the named step invoked by the user depends on the run step.
4. After running it, record `compiled`, `executed`, and `passed` separately.

If the run edge is missing, report that the tests compiled but did not execute, and propose the smallest version-matched build-graph correction.

## Modify dependencies and `build.zig.zon`

- Confirm the dependency source, version or revision, license, expected module, target support, and supply-chain boundary first.
- Treat `build.zig.zon` fields, hash rules, and `zig fetch` options as version-sensitive. Check the target version's `zig fetch --help`, language reference, release notes, or source first.
- Generate or verify dependency hashes with the target-version toolchain. Do not guess them manually or reuse an unverified manifest fragment produced by another Zig version.
- Explain side effects before running a command that can access the network, write caches, or modify the manifest; obtain confirmation when the request has not authorized those effects.
- Preserve the existing dependency-pinning strategy. When updating one dependency, do not opportunistically update unrelated dependencies or rewrite the whole manifest.
- After a change, verify dependency resolution with an isolated or clean cache. Use cache options supported by the target version and preserve the user's global cache.

A dependency change is complete only after its source, integrity, module wiring, clean resolution, and project tests have all been verified.

## Perform a Zig version migration

Migrate only when the user explicitly requests it:

1. Record the current and target Zig versions, every version-pinning location, supported targets, and the CI matrix.
2. Read the official release notes across the version span and list changes to the language, standard library, Build API, `build.zig.zon`, C ABI, and tool options.
3. Reproduce and classify failures with the target compiler before beginning unrelated refactoring.
4. Update version pins, the manifest, build graph, and source in the smallest coherent increments; keep either an explainable failure or green verification result for each increment.
5. For multi-version support, prefer capability detection and make the support window explicit. If only the target version remains supported, remove compatibility branches that are no longer needed.
6. With the target version, complete formatting, compilation, test execution, target builds, and runtime verification on available platforms.

The migration report should list breaking changes, the compatibility strategy, command evidence, unverified targets, and the boundary required to roll back to the old toolchain.

## Package and publish

- Check the package name, version, exported modules, included paths, license files, and generated artifacts. Exclude caches, secrets, and local machine paths.
- From a clean checkout with an isolated cache, verify that a consumer can resolve the dependency, import the public module, and run a minimal program.
- Publication and remote tag creation are external side effects. Confirm the target, version, credential source, and authorization before performing them.

Use the target version's [build system guide](https://ziglang.org/learn/build-system/), [language reference](https://ziglang.org/documentation/), and release notes as the authority for concrete Build API and manifest fields.
