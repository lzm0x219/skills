# Issue tracker: GitHub

Issues and specs for this repository live in GitHub Issues. Use the `gh` CLI and infer the repository from `git remote -v`.

## Conventions

- Create an issue with `gh issue create --title "..." --body-file <file>`.
- Read an issue and its discussion with `gh issue view <number> --comments`.
- List issues with `gh issue list`, selecting the required state and labels.
- Comment with `gh issue comment <number> --body "..."`.
- Apply or remove labels with `gh issue edit <number> --add-label "..."` or `--remove-label "..."`.
- Close an issue with `gh issue close <number> --comment "..."`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

GitHub shares one number space across issues and pull requests. Resolve an ambiguous number with `gh pr view <number>` and fall back to `gh issue view <number>`.

## Skill operations

- When a skill says to publish to the issue tracker, create a GitHub issue.
- When a skill says to fetch a ticket, read the corresponding GitHub issue and its comments.

## Wayfinding operations

- Represent a wayfinder map as one issue labelled `wayfinder:map`.
- Represent decision tickets as GitHub sub-issues where available, falling back to a task list in the map issue.
- Represent blockers with GitHub issue dependencies where available, falling back to a `Blocked by:` line.
- Claim work by assigning the issue to the current user.
- Resolve work by recording the answer, closing the issue, and updating the map's decisions-so-far.
