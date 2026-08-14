# Zig coding best practices and style

## Resolve the target version first

Use the target Zig version or supported range already established in `SKILL.md`.

For the target version, read the corresponding language reference's Style Guide, standard library documentation, release notes, compiler-bundled source, and `zig fmt`/CLI behavior. If the Style Guide is absent or does not cover the question, derive conventions from the official source for the same version. Do not let rules from another version override the target version.

Continue with style and best-practice decisions only after the exact target version and its official evidence can be reported.

## Precedence

1. Follow the repository's existing public API, directory, naming, and testing conventions.
2. Verify semantics and current conventions against the target Zig version's official language reference, Style Guide, standard library, and source.
3. Let `zig fmt` determine whitespace, indentation, and line breaks; do not create manual formatting rules that compete with it.
4. Follow the target version's Style Guide when it exists. Otherwise, derive current conventions from that version's official Zig and standard library source, and label any additional choice explicitly as a project default.
5. Use the engineering defaults below only when neither the target version nor the repository covers the question.

Do not present personal preferences as Zig compiler requirements. Generated code, C names, and stable public APIs may preserve external conventions; do not introduce breaking renames merely for stylistic consistency.

## Naming and file organization

- Prefer the naming and file rules in the target version's Style Guide. If that version has no Style Guide or it does not cover the question, this skill's engineering default is: use `TitleCase` for types and callables that return a type, `camelCase` for other callables, and generally `snake_case` for other variables and values. Do not present this default as a compiler requirement for every Zig version.
- Apply the same casing rule for a category to abbreviations, initialisms, and proper nouns; preserve established names from external protocols or platforms.
- Use names that express meaning or units, such as `timeout_ns` and `byte_count`; prefer boolean names that read as assertions.
- Let namespaces supply context instead of repeating the type or module name in members.
- Use `TitleCase` for files that represent types and `snake_case` for files and directories that represent namespaces; generated files and external ABI files follow their source conventions.
- Give each file and module one clear responsibility. Split by dependency boundaries and comprehensibility, not mechanical line counts.
- Keep declaration visibility minimal; mark only stable, genuinely required surfaces as `pub`.

## Data and API design

- Prefer `const`; use `var` only when the binding must be reassigned. Distinguish binding mutability from the mutability of the referenced memory.
- Use `undefined` only for storage that will definitely be initialized before it can be read; do not use it as a zero value, empty value, or sentinel.
- Prefer slices, which carry their length, over a separate pointer and length. Use more specific pointer types only when required by an ABI, sentinel, or low-level layout.
- Use optionals for "no value" and error unions for "operation failed"; do not conflate these states with magic numbers, empty slices, or `undefined`.
- Public functions must specify input validity, return-value ownership, allocator use, errors, thread/reentrancy constraints, and lifetimes.
- For state shared across threads, specify the synchronization owner, thread-safe allocator, and shutdown order. Compilation alone is not evidence of freedom from data races or safe reentrancy.
- Let namespaces carry context; follow adjacent API conventions such as paired `init`/`deinit`, `create`/`destroy`, or their equivalent for construction and cleanup.
- Keep abstractions removable: start with clear concrete code and introduce generics or helpers only after a repeated pattern and caller need are evident.

## Memory and resources

- Accept allocators at reusable library boundaries instead of hiding a process-wide allocator or assuming one allocator strategy inside a library.
- Select allocators by lifetime: consider an arena for short-lived objects released together, a fixed buffer for a fixed upper bound, and a project-appropriate general-purpose allocator for general ownership. Verify concrete types and initialization APIs against the target Zig version.
- Schedule `defer` immediately when acquiring a resource; protect failure paths with `errdefer` until construction transfers ownership to the return value.
- A borrowed value must not outlive its owner, buffer, iterator, container, or C resource. When a longer lifetime is required, copy explicitly and document the releaser.
- Test allocating code with the target version's test allocator or an equivalent leak-detection mechanism, including partial-construction failures.

## Errors and control flow

- Use an error set that describes the possible failures; avoid unnecessarily widening library boundaries to `anyerror`.
- Use `try` to propagate errors the current layer cannot handle; use `catch` to recover, add context, or translate an error at a boundary.
- Use `catch unreachable` only when a type, precondition check, or inviolable invariant has already proven the condition.
- Keep the happy path contiguous and leave cleanup to `defer`/`errdefer`; when nesting becomes complex, first narrow the function or extract a semantic helper.
- Use `for`, `while`, `switch`, and labeled blocks for actual control flow. Do not use `comptime` as a substitute for an ordinary runtime branch.

## `comptime` and version compatibility

- Use `comptime` only when a type, generic parameter, compile-time validation, or code generation genuinely requires it; document its impact on compile time, diagnostics, and code size.
- Prefer type inference from the call site and avoid unnecessarily widening interfaces with `anytype`.
- For multi-version compatibility, prefer capability or feature detection, such as `@hasDecl` or `@hasField` when supported by the target versions, instead of scattering version comparisons throughout the codebase.
- Compile-time reflection should produce a clear `@compileError` that identifies the violated contract and how the caller can fix it.

## Runtime safety and Illegal Behavior

- Validate external input, I/O, protocol data, and FFI return values as ordinary errors; use `unreachable` only for invariants already proven by types or precondition checks.
- Restrict `@setRuntimeSafety(false)` to the smallest measured, test-protected scope and document the preconditions it depends on. Ordinary application code should retain the target optimization mode's default safety policy.
- Before pointer, alignment, integer, enum, or sentinel conversions, prove the range, alignment, valid values, and lifetime. Verify the specific builtins and failure behavior against the target version.
- Cover invalid inputs and boundaries in a mode with runtime safety enabled. If the project supports ReleaseFast, ReleaseSmall, or another mode that disables some checks, verify its behavior on the target platform separately.

## Comments and documentation

- Use `///` for a declaration's public contract, `//!` for a container or module's purpose, and `//` for local implementation rationale.
- Comments should explain constraints, ownership, units, protocols, ABI details, or non-obvious tradeoffs, not restate the code's literal behavior.
- Public API documentation must at least state ownership and the releaser, error semantics, preconditions, and cross-thread or cross-ABI constraints.
- When a code change makes a comment inaccurate, correct or remove the comment in the same change.

## Testing and review checklist

- Place tests as close as possible to the behavior they protect; cover success, boundary inputs, expected errors, and resource cleanup.
- When testing errors, assert error semantics rather than complete diagnostic text or unstable internal layouts.
- For target, optimization, C ABI, concurrency, or allocator concerns, record the test matrix and uncovered combinations explicitly.
- During review, verify each item: version matching, `zig fmt`, public API, ownership, errors, `comptime` cost, actual test execution, and target runtime evidence.

For detailed semantics and style, defer to the target version's [language reference](https://ziglang.org/documentation/) and its Style Guide, standard library documentation, release notes, `zig fmt`, and compiler-bundled source. Another version's Style Guide explains only that version and is not the default authority for the target version or an unspecified version.
