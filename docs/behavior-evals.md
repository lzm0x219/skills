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

A case with `runner: "workspace"` is excluded from the read-only behavior runner and must be run with `run_workspace_evals.py`. This keeps real mutation scenarios from being falsely evaluated under a read-only sandbox.

A manual Skill with `disable-model-invocation: true` defines only `explicit` scenarios. Static validation keeps that frontmatter setting aligned with `policy.allow_implicit_invocation: false`.

## Run offline evaluations

Use `--answers` to read fixed answers without calling a model or needing credentials:

```sh
python3 scripts/run_behavior_evals.py \
  --skill bootstrap-project --answers evals/fixtures/bootstrap-project
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
python3 scripts/run_behavior_evals.py \
  --skill china-commerce-asset-pack --answers evals/fixtures/china-commerce-asset-pack
python3 scripts/run_behavior_evals.py \
  --skill napi-rs --answers evals/fixtures/napi-rs
python3 scripts/run_behavior_evals.py \
  --skill mise --answers evals/fixtures/mise
python3 scripts/run_behavior_evals.py \
  --skill durable-execution-state \
  --answers evals/fixtures/durable-execution-state
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
python3 scripts/run_behavior_evals.py --skill china-commerce-asset-pack
python3 scripts/run_behavior_evals.py --skill bootstrap-project
python3 scripts/run_behavior_evals.py --skill napi-rs
python3 scripts/run_behavior_evals.py --skill mise
python3 scripts/run_behavior_evals.py --skill durable-execution-state
```

Live evaluation sends scenario prompts and skill content to the configured Codex service. Results only apply to the CLI, model, skill version, and scenario assertions used at runtime.

### Compare a model or prompt change

Both runners accept `--model` and `--reasoning-effort`, with defaults from `CODEX_EVAL_MODEL` and `CODEX_EVAL_REASONING_EFFORT`. Explicit flags override these environment defaults. Omitting both preserves the Codex defaults; the runners do not select a new model automatically. Codex validates whether the requested effort is supported by the chosen model.

For a reproducible comparison, use the same CLI version, explicit model and effort, case IDs, fixture inputs, and evaluation harness on both Skill revisions. Change either the model or the Skill prompt at a time. Record both revisions and save the final answers, assertion failures, wall time, and any available usage data. Repeat representative cases before making quality or performance claims; one passing answer is not a measured improvement.

```sh
python3 scripts/run_behavior_evals.py --skill mise \
  --case approved-project-ci --model gpt-6-astra \
  --reasoning-effort high --show-output
python3 scripts/run_workspace_evals.py --skill bootstrap-project \
  --case existing-zig-planning --model gpt-6-astra \
  --reasoning-effort high --report-dir /tmp/astra-workspace-eval
```

These are live runs, not offline validation. The workspace report records the requested CLI arguments, not proof of the effective backend model. The [Astra guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#update-api-and-model-parameters) advises retaining the effective effort when migrating, or starting at `low` from `none`/`minimal`. The `high` above is an example comparison setting, not a repository default. The CLI override uses [`model_reasoning_effort`](https://learn.chatgpt.com/docs/config-file/config-basic).

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
- Optional created paths for runtime-dependent transient files such as SQLite WAL sidecars;
- Final-answer assertion failures and mutation mismatches.

```sh
python3 scripts/run_workspace_evals.py \
  --skill bootstrap-project \
  --case existing-zig-planning \
  --report-dir /tmp/bootstrap-project-eval-reports
python3 scripts/run_workspace_evals.py \
  --skill durable-execution-state \
  --case statectl-workspace-init \
  --report-dir /tmp/durable-execution-state-eval-reports
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
- Score ranking stays distinct from frequency estimation; partial-window expiration includes a concrete lost-candidate counterexample
- Cache decisions separate byte capacity, TTL, same-key loading and invalidation races
- Dependency graphs validate missing nodes, duplicate edges and cycles before execution, with deterministic ready-task ordering
- Exact deduplication accounts for external-memory buffers and disk limits; impossible fixed-memory constraints are stated explicitly
- Concurrent queues protect compound operations and bound both queued and in-flight work
- Benchmark plans require equivalent results and reproducible conditions without inventing measured gains

These are response contracts. Negative-answer tests and the executable two-record window counterexample strengthen the checks but do not validate production cache, scheduler or storage implementations. See the [optimization record](research/dsa-design-optimization.md) for the sampled live evaluation and its limits.

`durable-execution-state` covers:

- Short stateless requests do not surface execution-state machinery
- Resumable, compressed-context tasks keep bounded facts, evidence references, and completion criteria
- Side effects use pending state, idempotency keys, authoritative receipts, and reconciliation
- Recovery rechecks drifting Git and test facts rather than trusting snapshots
- Completion rejects pending actions and missing evidence
- An isolated workspace case initializes SQLite state, applies one patch, and verifies the event-replayed result; this checks paths written by a live model run, not external evidence validity

`china-commerce-asset-pack` covers:

- Strategy-only requests stop before product-image production
- Full asset-pack requests preserve brand-decision, product-page conversion, and channel-distribution stage gates
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

## Instruction-boundary regressions

The Astra instruction audit adds paired coverage for authorization, scope, and verification:

- `mise`: already-authorized project CI edits reuse approval; existing planning and untrusted-config cases still stop at their declared boundaries.
- `napi-rs` and `zig`: documentation-only work and completed targeted checks avoid unrelated build or compatibility matrices.
- `china-commerce-asset-pack`: automatic stage progression, later scope reduction, and existing publication authorization are distinct from unapproved publication. The latter prompt explicitly withholds authorization; it must not penalize a model for recognizing a user's direct authorization.
- `durable-execution-state`: missing host verification capability blocks the external action even when user authorization exists; repeated consent cannot repair missing infrastructure.
- `reference-style-reframe`: textual audits do not generate images, and selected-profile comparisons remain scoped. The existing all-profile case still requires the complete requested comparison.

CI runs saved-answer checks for all nine Skills, including `durable-execution-state`, `reference-style-reframe`, and `juanjuan-illustrations`. Creative cases inspect decisions expressed in text; visual QA remains separate. The new runner unit tests use a fake Codex executable to verify CLI and environment precedence without a live model request.
