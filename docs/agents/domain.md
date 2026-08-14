# Domain docs

This repository uses a single-context domain-document layout.

## Before exploring

- Read the root `CONTEXT.md` when it exists.
- Read ADRs under `docs/adr/` that affect the area being changed.
- If either location is absent, proceed silently. `/domain-modeling` creates domain documents lazily when terms or decisions are resolved.

## Use the glossary

Use the canonical terms defined in `CONTEXT.md` in issues, specifications, tests, and implementation notes. Reconsider invented synonyms; send genuine terminology gaps through `/domain-modeling`.

## Respect decisions

Surface any conflict with an existing ADR explicitly. Do not silently override an accepted decision.
