---
name: mise
description: "Use mise to manage project development tools, versions, environment variables, tasks, lockfiles, CI or IDE integration, and troubleshooting. Applies when adding or maintaining mise.toml, mise.local.toml, .mise/tasks/, and when running mise use, install, exec, run, trust, doctor, and similar work. When exact CLI flags, tool backends, settings, task attributes, or version compatibility matter, consult current official mise documentation first."
---

# mise general workflow

Manage the development environment using the current project's language, package manager, CI, and security conventions. Do not migrate an existing toolchain, rewrite shell configuration, or add global defaults merely to use mise. When the request is unrelated to mise, project tools, environment variables, or tasks, complete the original task directly and do not emit this skill's process or terminology.

## Establish boundaries first

1. Inspect existing `mise.toml`, `mise.local.toml`, `.mise/tasks/`, `mise.lock`, language version files, package managers, CI configuration, and `.gitignore`. Do not assume a particular repository, tool version, shell, CI platform, secret source, or local config file exists.
2. First define the problem to solve: one-off execution, project-level reproducible environment, personal global defaults, interactive shell, CI/IDE, or task orchestration. Prefer project-level, reviewable configuration. Change global configuration or shell rc files only when the user explicitly asks.
3. Before changing anything, confirm configuration scope, supported platforms, tool sources and version policy, and whether `mise.lock` should be committed with the project. Do not treat versions already installed on this machine as the team's compatibility commitment.

## Use current official documentation

1. First read the [official documentation task routing](references/official-documentation-inventory.md), then open the official pages directly related to the current work.
2. When exact CLI flags, tool backends, settings, task attributes, or version compatibility matter, always treat the current official pages as authoritative. Do not infer exact flags, defaults, or support matrices from this skill.
3. Run `node scripts/verify-official-docs-inventory.mjs --check` in this skill directory only when refreshing the routing inventory or claiming that local links remain valid; add `--verify-links` before publishing or after a refresh. From this repository root, use `node skills/development/tools/mise/scripts/verify-official-docs-inventory.mjs --check`.

| Work                                                            | Prefer these official topics                                                                                                             |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Install, activate, shell, IDE, or CI                            | Getting Started, Installing mise, Shims, IDE Integration, Continuous Integration, `mise activate`, `mise doctor`                         |
| Project configuration, config layers, and environment switching | `mise.toml`, Settings, Configuration Environments                                                                                        |
| Tool versions, backends, locking, and supply-chain risk         | Dev Tools, Backends, Registry, `mise.lock`, Security, `mise use`, `mise install`, `mise exec`                                            |
| Environment variables, secrets, hooks, or direnv                | Environment Variables, Secrets, Hooks, direnv, `mise trust`                                                                              |
| Build, test, lint, scripts, and monorepo tasks                  | Task Overview, Task Architecture, TOML/File Tasks, Task Arguments, Task Configuration, Monorepo Tasks, `mise run`, `mise tasks validate` |

Read pages according to the capabilities you actually touch. For example, when adding a CI task with environment variables for a monorepo, also read the configuration, environment, task, lockfile, and CI pages.

## Configuration and security boundaries

- Put team tool versions, tasks, and non-sensitive environment rules in project configuration. Do not quietly write personal paths, machine-specific settings, or plaintext credentials into commit-able files.
- Treat `mise.toml`, environment directives, templates, hooks, and tasks as executable boundaries. Review configuration from others and any files it references first. Without the user's explicit authorization, do not run `mise trust`, do not trust unknown configuration, and do not disable or relax trust restrictions.
- Do not rely on "CI detected" to auto-trust configuration. For uncontrolled configuration such as pull-request branches or automation bots, only resolve versions or update lockfiles with `MISE_SAFE=1` within the range allowed by the current official Security/CI pages. Safe mode disables project environment, hooks, tasks, template execution, and some plugin operations; it is not a substitute for a reviewed normal CI trust policy.
- Do not print secrets in answers, logs, task definitions, commits, or fixtures. When secrets are needed, confirm a safe source and injection method from current official Secrets guidance, and verify actionable errors when secrets are missing.
- Do not treat `mise self-update`, global `mise use`, global settings, shell rc changes, generating or rewriting CI files, downloading/installing untrusted tools, publishing, or deploying as side-effect-free operations. Do not run them without the user's explicit authorization.
- When choosing tool backends, version ranges, lockfile, and checksum policy, follow the project's existing supply-chain strategy. Do not replace an approved source merely because another backend is available.

## Implement and verify

1. Maintain configuration with minimal change: put tools in `[tools]`, and express only environment and task behavior the project already needs. Tasks should have clear names, inputs, dependencies, working directories, failure semantics, and reproducible outputs. Do not disguise interactive local steps as unattended CI tasks.
2. Install or sync tools only within the authorized scope, and confirm commands from the current official pages. Then run real project commands through `mise exec` or `mise run`. Do not claim the toolchain works merely because a config file exists or `mise install` succeeded.
3. If the project uses a lockfile, generate or update it, then review the diff, target platforms, and whether it should be committed. A lockfile can pin resolved versions and verification data at that moment, but it does not replace actual download, run, or cross-platform testing.
4. Run the current project's build, test, or lint for tasks; then run `mise tasks validate` when that capability and the current version apply. For environment issues, compare `mise env` output with the expected process environment and avoid printing sensitive values.
5. Claim that shell, IDE, CI, or target-platform integration works only after verifying it in the actual environment. `mise activate`, shims, and `mise exec` have different applicability boundaries; keep unrun environments as unverified.

## Diagnosis order

1. First confirm which configuration is being read, its scope, and trust state, then check the current mise version and shell/CI entrypoint.
2. Use the current official `mise doctor` and configuration/tool/task inspection commands to locate the problem layer: config discovery, trust, tool resolution and install, environment export, task definition, or host shell/IDE/CI.
3. Reproduce with the smallest command in a mise context, then check actual tool versions, PATH, environment variables, and task exit status. After a fix, rerun the original project command; do not only verify the diagnostic command itself.

## Local resources

- [Official documentation task routing](references/official-documentation-inventory.md): auditable entry points from the official `llms.txt`, sitemap, and current task topics; not an offline copy of the CLI API.
- [Official documentation inventory verifier](scripts/verify-official-docs-inventory.mjs): checks that official pages in the local routing are still listed by the current official index and can verify link reachability.
