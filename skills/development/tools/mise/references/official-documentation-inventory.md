# mise official documentation task-routing inventory

> Snapshot: 2026-07-29 (Asia/Shanghai). This file is an official page directory for task routing and link-integrity checks, not an offline copy of the mise CLI API. When implementing, still open the official pages for the capabilities involved to confirm current version details.

## Authoritative entry points and usage bounds

- Official machine-readable directory: [llms.txt](https://mise.jdx.dev/llms.txt). It lists current documentation entry points under Guides, Configuration, Dev Tools, Environments, Tasks, Plugins, Advanced, and CLI Reference.
- Official site index: [sitemap.xml](https://mise.jdx.dev/sitemap.xml). Together with `llms.txt`, it is used to discover moved, deleted, or new pages.
- This inventory selects topic pages needed for day-to-day project configuration; it does not claim a full copy of the official site. Exact commands, settings, backends, templates, platform support, and security behavior must still come from the live pages.
- Running `node scripts/verify-official-docs-inventory.mjs --check` in this skill directory verifies that topic URLs in this inventory still appear in the current official `llms.txt` or sitemap. From this repository root, use `node skills/development/tools/mise/scripts/verify-official-docs-inventory.mjs --check`. `--verify-links` additionally requests each recorded page. A passing check only proves link and index state; it does not prove a configuration works on any machine, shell, IDE, CI, or tool backend.

## 1. Install, activate, IDE, and CI

Use these pages to decide install methods and loading strategies for interactive shells and non-interactive environments. Do not hard-code one platform's install steps, PATH, or shell hooks into generic configuration.

- [Getting Started](https://mise.jdx.dev/getting-started.html) — Overview of install, one-off execution, tools, tasks, trust, and environment variables.
- [Installing mise](https://mise.jdx.dev/installing-mise.html) — Choose install methods by OS and package manager.
- [Shims](https://mise.jdx.dev/dev-tools/shims.html) — Compare shell activation, shims, and capability boundaries across run environments.
- [IDE Integration](https://mise.jdx.dev/ide-integration.html) — Ways to load mise tools and environment in an IDE.
- [Continuous Integration](https://mise.jdx.dev/continuous-integration.html) — How to provide project tools in CI; for uncontrolled pull-request configuration, follow the current page and restrict execution with `MISE_SAFE=1`.
- [`mise activate`](https://mise.jdx.dev/cli/activate.html) — Initialize the current shell session.
- [`mise doctor`](https://mise.jdx.dev/cli/doctor.html) — Check install and common configuration problems.

## 2. Configuration, environments, and trust boundaries

These pages determine project config discovery, layering, environment injection, and potential code-execution scope. For configuration, hooks, templates, or secrets of unclear origin, review before trust.

- [`mise.toml`](https://mise.jdx.dev/configuration.html) — Config files, tools, environment, and other project-level options.
- [Settings](https://mise.jdx.dev/configuration/settings.html) — Current settings keys, scopes, and entry points.
- [Configuration Environments](https://mise.jdx.dev/configuration/environments.html) — How to organize different environment configs in the same directory.
- [Environment Variables](https://mise.jdx.dev/environments/) — Load and export environment variables with the project directory.
- [Secrets](https://mise.jdx.dev/environments/secrets/) — Supported practices and bounds for sensitive environment variables.
- [Hooks](https://mise.jdx.dev/hooks.html) — Hooks during activate sessions and their execution prerequisites.
- [direnv](https://mise.jdx.dev/direnv.html) — Environment-management bounds when used with direnv.
- [`mise trust`](https://mise.jdx.dev/cli/trust.html) — Current behavior and scope of trusting config files.
- [`mise env`](https://mise.jdx.dev/cli/env.html) — Export mise environment variables for one-off use.

## 3. Tools, backends, locking, and supply chain

Tool sources, version resolution, lockfiles, and verification data are time-sensitive facts. Open the corresponding pages in this group when selecting or upgrading backends, changing lockfile policy, supporting multiple platforms, or handling GitHub rate limits.

- [Dev Tools Overview](https://mise.jdx.dev/dev-tools/) — Overview of installing project tools, switching versions, and auto-activation.
- [Backends](https://mise.jdx.dev/dev-tools/backends/) — Package ecosystems/backends that can provide tools and their install bounds.
- [Registry](https://mise.jdx.dev/registry.html) — Current registry of default tool aliases.
- [`mise.lock` Lockfile](https://mise.jdx.dev/dev-tools/mise-lock.html) — Lockfile generation, exact versions, checksums, and reproducibility bounds.
- [Security](https://mise.jdx.dev/security.html) — Supply-chain controls available for different backends and their coverage limits, plus using `MISE_SAFE=1` to bound code execution for uncontrolled project configuration.
- [`mise use`](https://mise.jdx.dev/cli/use.html) — Install tools and write them into `mise.toml`.
- [`mise install`](https://mise.jdx.dev/cli/install.html) — Install specified tool versions.
- [`mise exec`](https://mise.jdx.dev/cli/exec.html) — Run a command in a specified tool context.
- [`mise ls`](https://mise.jdx.dev/cli/ls.html) — List installed and activated tool versions.
- [`mise lock`](https://mise.jdx.dev/cli/lock.html) — Update lockfile URLs and checksums for specified platforms.

## 4. Tasks, task files, and monorepos

Tasks are project execution interfaces, not simple command aliases. When changing tasks, also review dependencies, arguments, working directories, environment, exit semantics, and CI executability.

- [Task Overview](https://mise.jdx.dev/tasks/) — Define and run project build, test, lint, deploy, and other tasks.
- [Task Architecture](https://mise.jdx.dev/tasks/architecture.html) — Discovery, dependency, and execution model for tasks.
- [Running Tasks](https://mise.jdx.dev/tasks/running-tasks.html) — List, select, and run tasks.
- [TOML Tasks](https://mise.jdx.dev/tasks/toml-tasks.html) — Define simple and detailed tasks in `mise.toml`.
- [File Tasks](https://mise.jdx.dev/tasks/file-tasks.html) — Directories and conventions for defining tasks as standalone scripts.
- [Task Arguments](https://mise.jdx.dev/tasks/task-arguments.html) — Supported forms and recommended ways to pass task arguments.
- [Task Configuration](https://mise.jdx.dev/tasks/task-configuration.html) — Full task configuration attributes.
- [Task Templates](https://mise.jdx.dev/tasks/templates.html) — Reuse task definitions and templates.
- [Monorepo Tasks](https://mise.jdx.dev/tasks/monorepo.html) — Organize tasks across projects/target paths.
- [Sandboxing](https://mise.jdx.dev/sandboxing.html) — Process isolation controls for `mise exec` and `mise run`.
- [`mise run`](https://mise.jdx.dev/cli/run.html) — Run one or more tasks.
- [`mise tasks validate`](https://mise.jdx.dev/cli/tasks/validate.html) — Check tasks for common errors and problems.

## Refresh rules

- When `--check` reports missing URLs, the official site adds topics, or a task needs capabilities not covered here, rediscover pages from the official `llms.txt` and sitemap. Keep canonical HTTPS URLs and extend by the task routing above instead of copying the whole site into the skill.
- Version changes, migration, plugin development, bootstrap, OCI, MCP, package plugins, templates, specific backends, or platform compatibility are official pages opened on demand. Absence from this inventory does not mean those capabilities do not exist.
- Do not treat this inventory or a successful link check as evidence that configuration is runnable, secrets are safe, the supply chain is trusted, or multi-platform support works. Those conclusions still need actual verification in the relevant environments.
