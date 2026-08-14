# Verify and report

Read this reference only after the selected adapter has returned or apply has been skipped. Use the selected stack reference as the source of stack-specific completion gates.

## Interpret status

- `blocked`: a conflict prevented apply; report the unresolved decision and confirm whether external commands ran.
- `planned`: the user requested planning only or the resolved shape has no packaged adapter.
- `partial`: writing began and an initializer, install, lock, hook, or quality command failed; retain the target and exact failed command.
- `completed`: the selected adapter, installed hook, stack completion gates, and `mise run ci` all passed.

## Check common evidence

Verify the adapter report against the target rather than trusting its status alone:

- Exact managed versions and lockfiles agree with recognized project constraints;
- Public mise tasks and the serial `ci` entry are present and execute real commands;
- Lefthook installs the ordered partial-stage guard, staged formatter and restage, lint, and quick check without full test or build;
- The Ubuntu workflow uses immutable action SHAs and calls `mise run ci` once;
- `.github/renovate.json` extends the recommended preset without automerge and explicitly disables lockfile maintenance;
- New mode creates no Git commit; existing mode preserves every file promised by the selected reference;
- Cache and build artifacts remain untracked, while expected side effects are reported accurately.

On `partial`, preserve evidence, report recovery, and leave cleanup to the user. On `blocked`, distinguish inspection from execution. A failed or unrun gate cannot produce `completed`.

## Return the result

```text
Status: completed | partial | planned | blocked
Target: <absolute path>
Mode: new | existing
Stack: Zig | Rust | TypeScript/Node.js | Python | Go | unresolved
Shape: library | CLI/application | unresolved
Versions: <value, precedence branch, evidence>

Changes:
- created: <paths, or none>
- modified: <paths, or none>
- preserved: <paths, or none>

Conflicts:
- <decision needed, or none>

Verification:
- <command> — <passed|failed|not run>

Failed command:
- <exact argv, or none>

Next step:
- <recovery command, adapter boundary, or none>
```

Finish only when every field is supported by the adapter report, target inspection, or an explicit `not run` value.
