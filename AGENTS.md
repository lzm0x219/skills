# Repository Guidelines

This repository contains portable Agent Skills plus the checks that keep their metadata, documentation, and behavior contracts consistent.

## Project structure and module organization

- `skills/<category>/<skill-name>/` contains each skill. Keep the portable entrypoint in `SKILL.md`; place task-specific detail in `references/`, deterministic helpers in `scripts/`, and optional Codex metadata in `agents/openai.yaml`.
- `evals/<skill-name>.behavior.json` defines source assertions and behavior scenarios. Matching fixed answers belong in `evals/fixtures/<skill-name>/`.
- `scripts/` contains the Python validators and behavior runner. `tests/` covers those tools with standard-library unit tests.
- `docs/` explains evaluation design, while `.github/workflows/validate.yml` records the required continuous integration checks.

## Build, test, and development commands

There is no build step. Run these offline checks before submitting changes:

```sh
oxfmt .
oxfmt --check .
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_behavior_evals.py \
  --skill dsa-design --answers evals/fixtures/dsa-design
```

`oxfmt .` formats supported files with Oxc; `oxfmt --check .` verifies formatting without writing. Replace `dsa-design` with the skill you changed. Running the behavior command without `--answers` invokes an authenticated Codex service. Use the skill-specific Node.js inventory scripts documented in `README.md` only when refreshing official-document coverage.

## Coding style and naming conventions

Use four-space indentation, `snake_case` functions and variables, and `PascalCase` test classes in Python. Prefer the standard library and type hints already used by nearby code. Name skill directories with lowercase kebab-case, such as `napi-rs`, and keep evaluation files aligned with that name. Markdown headings should be descriptive and sentence-cased. Format supported files with Oxc, follow adjacent Python style, and let validation enforce structural rules.

## Testing guidelines

Tests use `unittest`. Name files `test_*.py` and methods `test_*`. Add or update unit tests when validator or runner behavior changes. Skill changes should update their behavior contract and fixtures when observable expectations change. Fixed-answer tests validate the runner, not current model quality.

## Commit and pull request guidelines

Recent history favors concise Conventional Commit-style subjects, including `docs:`, `feat:`, and scoped forms such as `test(validation):`. Use an imperative summary and keep each commit focused.

Pull requests should explain the affected skill or tool, user-visible behavior, and validation commands run. Link related issues and call out network-backed or live-model checks separately. Include screenshots only when a change affects rendered UI.

## Agent skills

### Issue tracker

Issues and specs are tracked in this repository's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use the single-context domain layout. See `docs/agents/domain.md`.
