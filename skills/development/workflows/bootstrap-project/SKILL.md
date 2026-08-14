---
name: bootstrap-project
description: Create or plan a safe project scaffold and development baseline.
disable-model-invocation: true
---

# Bootstrap Project

Prepare a deterministic project-bootstrap plan while preserving user-owned work. Apply supported new or strictly recognized existing Zig, Rust, TypeScript/Node.js, Python, and Go projects only through the packaged adapters.

## Run the workflow

### 1. Establish the target boundary

Resolve the absolute target and read every repository instruction that applies to it. Accept one language, one package or module, and either a library or CLI/application shape. Require an exact subproject for a monorepo. Treat Git and mise as host prerequisites without changing global shell configuration.

Complete this step when the target, repository boundary, requested outcome, and applicable instructions are explicit.

### 2. Inventory without writing

Inspect manifests, source layout, tests, lockfiles, Git state, CI, quality tools, build commands, version constraints, environment managers, and hook systems. Record staged and unstaged changes without modifying the index.

When stack or shape evidence is incomplete, read [stack-evidence.md](references/stack-evidence.md). Ask one concise question when ambiguity would change the plan. Treat conflicting stack evidence or an unnamed monorepo target as unresolved.

Complete this step when every detected fact is recorded or marked unknown.

### 3. Resolve mode, stack, shape, and versions

Classify an absent or intentionally empty target as `new`; otherwise classify it as `existing` and preserve its source layout. Resolve versions by user-specified version, then existing constraint, then current stable from an authoritative source checked on the execution date.

Treat these as blocking conflicts:

- Multiple credible stacks, packages, or modules;
- A service, Web, GUI, framework, multi-language, or multi-package request;
- An alternative to mise or Lefthook that requires migration;
- Disagreeing version constraints;
- Unknown configuration that cannot be merged without discarding content.

Complete this step when mode, stack, shape, version evidence, and every conflict have an explicit value.

### 4. Build the change plan

Classify each relevant path once as `create`, `merge`, `preserve`, or `conflict`. Cover the code skeleton, scaffold smoke test, exact version pins, mise tasks, Lefthook, GitHub Actions, `.github/renovate.json`, README, ignore rules, EditorConfig, dependency and lockfile operations, Git initialization, hook installation, and verification.

For each proposed change, record its evidence, path, operation, command or content responsibility, and verification. Represent an unsupported quality gate explicitly instead of generating an empty successful task.

Complete this step when every prospective write is classified and each conflict has a precise decision request.

### 5. Route and apply

After mode and stack are resolved, read exactly one stack reference completely:

| Branch             | Reference                                     | Packaged adapter                   |
| ------------------ | --------------------------------------------- | ---------------------------------- |
| New Zig            | [zig.md](references/zig.md)                   | `scripts/bootstrap_zig.py`         |
| Existing Zig       | [zig-existing.md](references/zig-existing.md) | `scripts/baseline_existing_zig.py` |
| Rust               | [rust.md](references/rust.md)                 | `scripts/bootstrap_rust.py`        |
| TypeScript/Node.js | [node.md](references/node.md)                 | `scripts/bootstrap_node.py`        |
| Python             | [python.md](references/python.md)             | `scripts/bootstrap_python.py`      |
| Go                 | [go.md](references/go.md)                     | `scripts/bootstrap_go.py`          |

Use the selected adapter and its assets instead of reproducing generated files from memory. Apply only when the user requested initialization, the selected reference accepts the target, and the plan has no conflicts. Return `planned` for plan-only requests or unsupported shapes.

Stop at the first write or command failure. Retain partial output and the adapter report for diagnosis; preserve user-owned files and unrelated work.

Complete this step when the adapter has returned a report, or when a supported reason prevented apply.

### 6. Verify and report

After the selected adapter finishes or apply is skipped, read [reporting.md](references/reporting.md) completely. Combine its common result contract with the completion gates in the selected stack reference.

Complete this step only when the final status, changes, conflicts, commands, verification evidence, failed command, and next step are all accounted for. Never describe inspection or planning as successful initialization.
