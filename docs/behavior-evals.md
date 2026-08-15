# How behavior evaluation works

Behavior evaluation in this repository checks a skill's final visible answer to representative requests. It complements static validation, but it does not claim to observe whether a model loaded a skill internally.

## Contracts and fixed answers

Each `evals/<skill-name>.behavior.json` is a machine-readable contract that contains:

- Regexes that skill source must keep or must not contain
- Identifiers, categories, and invocation modes for required scenarios
- The user request sent to the model
- Regexes that the final answer must match or must not match

`evals/fixtures/<skill-name>/<case-id>.txt` stores fixed answers for offline regression. Fixed answers only prove that the evaluation runner and assertions can handle known output. They do not prove that the current model still produces the same answer.

## Explicit and implicit scenarios

Each scenario declares its invocation mode with `invocation`:

- `explicit`: the prompt explicitly calls the isolated `$skill-name-working-tree-eval`
- `implicit`: the prompt does not inject `$skill-name` and only submits a normal user request

Both modes only inspect the final visible output. An `implicit` scenario can verify that unrelated requests do not surface skill terminology, but it cannot prove that the skill was never loaded inside the model.

A manual Skill with `disable-model-invocation: true` defines only `explicit` scenarios. Static validation keeps that frontmatter setting aligned with `policy.allow_implicit_invocation: false`.

## Run offline evaluations

Use `--answers` to read fixed answers without calling a model or needing credentials:

```sh
python3 scripts/run_behavior_evals.py \
  --skill bootstrap-project --answers evals/fixtures/bootstrap-project
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill sell-product-in-china --answers evals/fixtures/sell-product-in-china
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
python3 scripts/run_behavior_evals.py \
  --skill mise --answers evals/fixtures/mise
```

List scenarios or run only one:

```sh
python3 scripts/run_behavior_evals.py --skill napi-rs --list
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --case generic-binding-design
```

## Run live model evaluations

Omit `--answers` to make the runner use an authenticated Codex CLI:

```sh
python3 scripts/run_behavior_evals.py --skill dsa-design
python3 scripts/run_behavior_evals.py --skill sell-product-in-china
python3 scripts/run_behavior_evals.py --skill bootstrap-project
python3 scripts/run_behavior_evals.py --skill napi-rs
python3 scripts/run_behavior_evals.py --skill mise
```

Live evaluation sends scenario prompts and skill content to the configured Codex service. Results only apply to the CLI, model, skill version, and scenario assertions used at runtime.

## Isolate installed skills with the same name

Live evaluation first copies the target skill from the working tree into a temporary workspace and renames it to a unique evaluation name. The subprocess also uses temporary `CODEX_HOME` and `HOME` values, so it does not inherit these user-level skills:

- `$CODEX_HOME/skills`
- `$HOME/.agents/skills`

If the original `CODEX_HOME` contains `auth.json`, the runner copies only that file into the temporary directory and sets permissions so only the current user can read and write it. The temporary workspace, user home, and auth copy are deleted when the runner exits.

Evaluation sessions use a read-only sandbox and `--ephemeral`. Those settings reduce file side effects and session residue, but they do not replace review of prompts, skill scripts, and external-service permissions.

## Evaluate workspace mutations

Use `run_workspace_evals.py` when the expected behavior is expressed by target files, not only the final answer. The runner copies `evals/workspaces/<skill>/<case>/input/` into a temporary workspace, installs a uniquely named working-tree Skill, runs one explicit case with `workspace-write`, and writes a JSON report containing:

- The command, return code, stdout, and stderr;
- Before and after manifests with type, mode, size, and SHA-256 evidence;
- Created, modified, and deleted relative paths;
- Final-answer assertion failures and mutation mismatches.

```sh
python3 scripts/run_workspace_evals.py \
  --skill bootstrap-project \
  --case existing-zig-planning \
  --report-dir /tmp/bootstrap-project-eval-reports
```

The fixture and isolated skill copy are deleted after the report is written. The current planning case expects an unchanged target. The writable sandbox and temporary directory reduce risk; they are evidence boundaries, not proof that arbitrary executed tools have no external side effects.

The deterministic `existing-zig-baseline` fixture is exercised by `tests/test_bootstrap_project_existing_zig.py`. It copies the input into a temporary Git repository, invokes the packaged adapter through a fake mise command boundary, and checks exact created and modified paths plus preserved source hashes. A separate real-tool smoke run is still required before claiming Zig compatibility.

The dated five-stack evidence, platform limits, and tool side effects are recorded in [bootstrap-project-acceptance.md](bootstrap-project-acceptance.md). `tests/test_bootstrap_project_integration.py` keeps the shared task, hook, workflow, Renovate, and behavior-matrix contracts aligned.

## Behaviors currently covered

`bootstrap-project` covers:

- Manual invocation metadata and explicit-only behavior cases
- Progressive disclosure from the shared workflow into one selected stack reference and the final reporting contract
- New Zig library and CLI completion reports backed by the packaged adapter
- Zig verification failure reported as partial with the exact failed command
- Existing Ziwei-style Zig baseline completion and idempotent strict merging
- New Rust library and CLI completion with Cargo, rustfmt, and Clippy gates
- Existing Rust baseline completion with preserved Cargo and source files
- New ESM TypeScript/Node.js library and CLI completion with pnpm, Oxc, strict TypeScript, and Vitest gates
- Existing TypeScript/Node.js baseline completion with preserved sources, package scripts, and compatible configuration
- New packaged Python library and CLI completion with uv, Ruff, strict mypy, pytest, and build gates
- Existing Python baseline completion with preserved metadata, lockfile, sources, tests, and package layout
- New Go library and CLI completion with module, gofmt, vet, test, and build gates
- Existing Go baseline completion with preserved module path, metadata, sources, tests, and package layout
- Existing Zig project inventory and planning without target writes
- Ambiguous stack and monorepo target boundaries
- Volta and Husky migration conflicts
- Before/after workspace manifests, adapter unit tests, and unexpected mutation failure

`dsa-design` covers:

- Pure prose requests do not produce DSA output
- Routine CRUD does not force multi-option comparison
- Material Top-K decisions compare options and wait for a choice when unauthorized
- Delegated user choices do not pause for option selection

`sell-product-in-china` covers:

- Strategy-only requests stop before product-image production
- Full asset-pack requests preserve strategy, copy, and visual-master stage gates
- Apparel requests are identified as outside the Skill's current scope
- Missing image-generation capability degrades to copy, prompts, and a production checklist without false completion claims
- High-risk product claims remain blocked until facts and current official rules are verified
- Final-answer assertions require refusing immediate rendering and requesting inspection of raw HTML, local-file URLs, and remote resources; helper unit tests separately cover private raster-resource snapshots, atomic output, and explicit renderer selection
- Listing, posting, and ad publication require separate explicit authorization
- Unrelated prose edits do not surface e-commerce workflow terminology

The `strategy-deliverable-write` workspace case separately evaluates creation of one requested strategy file while preserving the source fixture and forbidding additional deliverables.

`napi-rs` covers:

- Unrelated tasks are answered directly
- Generic binding design
- Lifetime and concurrency boundaries
- Unauthorized release boundaries
- Official documentation coverage checks
- Project-specific terminology is forbidden from re-entering the skill

`mise` covers:

- Unrelated tasks are answered directly
- Project-level tool, environment, and task design
- Trust safety boundaries for unreviewed config
- Safe-mode boundaries for uncontrolled pull-request config
- Lockfile and CI reproducibility verification boundaries
- Official documentation routing index checks
- Project-specific terminology is forbidden from re-entering the skill

`zig` covers:

- Unrelated tasks are answered directly
- Version-aligned build changes and explicit compiler migrations
- Allocator ownership and cleanup paths
- Safety boundaries for unreviewed executable build scripts
- Cross-target compilation versus runtime verification
- Test artifact compilation versus actual test execution
- Version-sensitive dependency, hash, network, and cache boundaries
- C ABI, ownership, callback, linking, and runtime boundaries
- Measurement-driven optimization
- Zig formatting, naming, documentation, and public API style
- Explicit version selection and latest-stable fallback when no version evidence exists
- Version lower bounds, supported ranges, formatter selection, and representative compiler matrices
- Runtime-safety boundaries for external input, `unreachable`, and `@setRuntimeSafety(false)`
- Official latest-stable release metadata and link verification

These scenarios are a regression baseline, not exhaustive verification across all prompts, models, and runtimes.
