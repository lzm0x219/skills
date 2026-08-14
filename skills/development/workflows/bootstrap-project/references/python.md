# Python bootstrap adapter

Use the Python adapter for one packaged Python project that is either a library or CLI/application. New mode accepts only an absent or empty target. Existing mode accepts only the exact root of a Git repository with repository-local `.git` metadata.

## Resolve versions and shape

Use the standard version priority: explicit user choice, then an exact existing project constraint, then the current stable release verified from the responsible official source on the execution date. The packaged baseline was verified on 2026-08-14 with Python `3.14.7`, uv `0.12.4`, uv build backend `0.12.4`, build `1.5.0`, mypy `2.3.0`, pytest `9.1.1`, Ruff `0.16.3`, Lefthook `2.1.10`, and mise `2026.8.5`; treat these values as dated evidence. Do not select build `1.5.1`, which PyPI has yanked.

New mode requires an exact version for every listed tool and dependency, a valid normalized Python distribution name, and `library` or `cli`. Existing mode derives its name and shape from PEP 621 metadata and a recognized `src` layout. Its exact Python version comes from `.python-version` and must satisfy `project.requires-python`; explicit arguments must agree with existing exact pins.

## Run the adapter

Use a fresh report path outside the target:

```sh
python3 <skill-directory>/scripts/bootstrap_python.py \
  --target <absolute-target> \
  --mode <new|existing> \
  --shape <library|cli> \
  --name <distribution-name> \
  --python-version <x.y.z> \
  --uv-version <x.y.z> \
  --build-version <x.y.z> \
  --mypy-version <x.y.z> \
  --pytest-version <x.y.z> \
  --ruff-version <x.y.z> \
  --lefthook-version <x.y.z> \
  --report <absolute-report-path>
```

For existing mode, omit `--name`. Dependency version arguments may be omitted only when the same exact versions already exist in the recognized `pyproject.toml`. `--shape` is optional but must agree when supplied.

New mode initializes Git without a commit, installs the exact mise tools, invokes official `uv init --lib` or packaged `uv init --app`, validates its known output boundary, replaces only those generated files with the selected minimal templates, locks and syncs exact dependencies, installs Lefthook, and runs `mise run ci`. The exact patch-level Python pin belongs to mise and `.python-version`, even when uv's default initializer would write only a minor version.

Existing mode never runs `uv init` and never rewrites `pyproject.toml`, `uv.lock`, `.python-version`, sources, tests, or README. It accepts only PEP 621 metadata with the recognized uv build backend, exact development dependency pins, Ruff, strict mypy, pytest configuration, a current locked uv environment, and a library or thin-CLI `src` layout. Poetry, PDM, Pipenv, asdf, Husky, pre-commit, legacy setup files, nested projects, custom hooks, and unknown baseline destinations are blocking conflicts.

## Generated quality baseline

- `install`: `uv sync --locked --all-groups`;
- `format` and `format-check`: Ruff format, with check mode read-only;
- `lint`: Ruff check with no cache;
- `check`: strict mypy over `src` and `tests`, with its cache disabled;
- `test`: pytest with its cache provider disabled;
- `build`: `python -m build --installer=uv` through the locked uv environment;
- serial `ci`: locked sync, format-check, lint, check, test, then build;
- pre-commit: `piped: true` enforces stop-on-failure order across the partial-stage guard, staged Ruff formatter and explicit restage of only those files, whole-project Ruff lint, then mypy. Full pytest and build remain outside the hook. The version-locked installer validates Lefthook's generated hook, adds the official `--no-stage-fixed` run flag, and scopes `MISE_TRUSTED_CONFIG_PATHS` to this hook process without persisting global trust, while the formatter helper reads NUL-delimited Python paths directly from the Git index;
- Ubuntu CI through the same `mise run ci` entry, immutable action SHAs, and Renovate coverage for mise, PEP 621, uv lock artifacts, and Actions. Lockfile maintenance remains explicitly disabled.

A new library includes `py.typed`. A new CLI keeps printing and argument handling in thin `src/<module>/cli.py` code and places tested behavior in `core.py`.

## Failure semantics

`blocked` means a target, package boundary, version, VCS, manager, hook, shape, metadata, lockfile, or destination conflict prevented apply. `partial` means a known write or external command failed; retain the report, exact failed command, and partial changes. `completed` requires an installed hook, exact mise and uv lockfiles, a successful full gate, and—for new mode—an empty Git history.
