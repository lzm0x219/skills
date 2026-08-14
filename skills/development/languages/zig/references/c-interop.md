# Zig and C interoperability boundaries

Use the target Zig version established in `SKILL.md`. Verify `@cImport`, `zig translate-c`, the Build API, C ABI, and linker options against that target version.

## Choose a binding approach

- Prefer evaluating `@cImport` when headers must be consumed directly and a consistent include-path and macro environment can be supplied at compile time.
- Evaluate the target version's `zig translate-c` workflow when the translated output must be inspected, separate `cflags` are required, declarations that cannot be translated automatically need correction, or explicit Zig bindings must be maintained.
- Treat generated or translated bindings as a boundary layer. Access them through a narrow, handwritten Zig adapter so C representations do not spread throughout the codebase.
- Record the headers, library, target, ABI, macros, include paths, and generation command. Revalidate the bindings whenever any of them changes.

## Model the ABI and data

- For every cross-boundary type, verify the calling convention, integer width and signedness, alignment, `extern` layout, enums, bitfields, sentinels, nullable pointers, and string-termination rules.
- Do not assume that C `long`, `size_t`, enums, or structs have the same layout across targets.
- Define explicit serialization for stable disk or network formats instead of using native C or Zig memory layouts directly as a protocol.
- Convert C representations into semantic Zig types inside a narrow adapter, and translate errors and ownership in the same place.

## Make ownership, lifetimes, and callbacks explicit

- For every pointer, buffer, handle, and string, state the allocator, release function, mutability, length, termination convention, and lifetime.
- Pass Zig-allocated memory to C only when the allocator and ABI contract permits it. Release resources returned by C only with the function designated by that library.
- A callback must define the owner of its userdata, registration and unregistration order, thread, reentrancy rules, and maximum lifetime. It must not retain an expired stack address or borrowed slice.
- Cross-thread callbacks may carry only data that meets the thread-safety and lifetime requirements. Translate C status codes, null, `errno`, or library-specific errors into a stable Zig error boundary.

## Configure the build and linker

- Use the target version's Build API to configure include paths, C sources, macros, libc, system libraries, static or dynamic linking, and runtime search paths.
- Propagate target and optimization options through Zig artifacts, C compilation, and link steps to avoid mixing incompatible ABIs or runtimes.
- For a system library, record the minimum version and discovery mechanism. For vendored C source, record compiler options and licensing.

## Verify the boundary

1. Compile the smallest header import or translated binding.
2. Link a real or controlled test library and verify symbols and ABI.
3. Run a smoke test in a compatible target environment, covering one successful call and one failure translation.
4. For resource-owning APIs, cover allocation, release, partial failure, and repeated-call boundaries.
5. For callbacks, cover registration, invocation, unregistration, failure, and thread/reentrancy constraints.

Compilation or linking alone does not prove runtime ABI correctness. Record compilation, linking, execution, and uncovered targets separately in the report.

Use the target version's [C interoperability section](https://ziglang.org/documentation/) and `zig translate-c --help` as the authority for syntax and tool options.
