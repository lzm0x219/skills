---
name: dsa-design
description: Use when software design, implementation, review, or performance and resource questions include a material data structure or algorithm choice. Starting from a simple baseline, compare complexity and trade-offs against the real data shape, operation patterns, scale, constraints, language, and runtime, then recommend. May trigger implicitly for CRUD, indexing, caching, sorting, dependencies, concurrency, or resource bounds that affect correctness, performance, or resource use; do not use for pure prose, formatting, documentation edits, or mechanical changes with no material DSA choice.
---

# DSA Design

Fit data structures and algorithms to the current need. Do not optimize for imagined future requirements.

## Run the applicability gate first

Before analysis or applying the output format, decide whether the request includes a data representation, index, traversal, sort, schedule, dependency, or algorithm choice that materially affects correctness, complexity, performance, or resource use. Explicit mention of or a request to use this skill only means this check is required; it does not prove the request has a material DSA decision.

If the gate fails, stop the rest of this skill immediately:

- For pure prose, formatting, or documentation edits, complete the request directly. Do not mention this skill, DSA, data structures, algorithms, or complexity, and do not emit a rationale block.
- For standard CRUD where the existing representation is already fixed, the scale is small and fixed, and there are no new performance or resource constraints, reuse the existing representation. Briefly note complexity in ordinary prose only when it helps implementation review. Do not emit a "DSA choice", candidate options, or selection questions.

Continue only after you confirm a material DSA trade-off exists.

## Establish decision context

Before proposing a design, inspect the user need, applicable repository instructions, existing code, configuration, dependencies, data model, and runtime. Discover facts available in the environment; do not ask the user for them.

Determine:

- Domain rules and invariants;
- Data shape, cardinality, and credible growth expectations;
- Read, write, update, delete, traverse, sort, group, range, priority, dependency, and relationship operations;
- Operation frequency and read/write ratio;
- Correctness, latency, throughput, memory, durability, concurrency, determinism, explainability, and replay requirements;
- Database query counts, disk I/O, network round trips, serialization, lock contention, cache invalidation, and data migration cost;
- Whether inputs are untrusted, plus risks of worst-case degradation, CPU or memory exhaustion, hash collisions, and cache pollution;
- Language, runtime, standard library, database, and existing project capabilities.

Ask one short question only when a missing fact would materially change the choice. Otherwise continue with conservative, clearly stated assumptions.

## Start from the simplest baseline

First choose the simplest representation and algorithm that satisfies current constraints. Prefer arrays, maps, sets, tuples, linear scans, standard-library collections, and database-native indexes before specialized structures.

Do not introduce graphs, heaps, trees, tries, bitsets, caches, dynamic programming, incremental computation, custom implementations, or third-party dependencies unless they solve a real constraint better than the baseline.

When the operation pattern does not immediately determine candidates, read [selection-framework.md](references/selection-framework.md).

## Produce viable options

For material decisions, provide two or three non-dominated viable options. Do not pad the list.

For each option, state:

- Data representation and algorithm;
- Complexity of key operations, including average, worst-case, or amortized complexity where relevant;
- Memory, constant factors, I/O, network, and synchronization costs;
- Invariants and failure modes;
- Implementation, maintenance, and migration cost;
- Worst-case behavior and resource bounds under untrusted or adversarial input;
- Compatibility with the current language, runtime, database, and project;
- Conditions under which that option becomes the better choice.

For simple decisions, briefly state the chosen structure or algorithm, the main reason, and the key complexity. Stay within those three items unless the user asks for more detail, and do not attach full code.

When judging whether a decision is simple or material, read [worked-examples.md](references/worked-examples.md).

## Make a recommendation

Recommend one option with this priority order:

1. Preserve correctness and domain invariants.
2. Keep acceptable worst-case behavior and bounded resource use for untrusted input.
3. Satisfy current latency, throughput, scale, memory, I/O, and network constraints.
4. Among options that meet the constraints, choose the simplest, most maintainable design.
5. Accept extra complexity only when there is a measured bottleneck or a clearly credible growth expectation.
6. When asymptotic complexity is similar, compare constant costs, locality, allocation, concurrency, explainability, and runtime behavior.

Explain why the recommended option fits the current need, and under what conditions another option would overtake it.

## Control material decisions

Wait for the user to choose before implementing only when all of the following hold:

- The user has not clearly authorized the agent to make that decision;
- The candidates would materially change a public interface, irreversible persistence or migration, a critical dependency, or product semantics.

If the user has delegated the choice, or the choice is an internal implementation detail and reversible, state the assumptions and recommendation and continue. Modify code or files only when the original request already authorized implementation.

Respect the user's choice. If that choice cannot preserve correctness or meet explicit constraints, explain the conflict before continuing.

## Implement and verify

Implement only when the user explicitly asks for code to be written or changed. If the user only asked for design, options, comparison, or review, do not emit an executable implementation; when necessary, provide only pseudocode, type signatures, or interface sketches.

Do not treat "do not modify files" as authorization to write a full implementation in the reply. When feasible, encapsulate the chosen data structure behind a small, stable module interface.

For non-trivial algorithms, give a correctness argument sufficient for review:

- State preconditions and postconditions;
- State loop, recursion, state, or data-structure invariants;
- Explain why the algorithm terminates;
- For greedy algorithms, explain why local choices do not break global optimality;
- For dynamic programming, state state, transition, base cases, and computation order;
- For graph algorithms, state node, edge, direction, weight, and reachability semantics.

Verify:

- Observable behavior and domain invariants;
- Applicable empty, minimum, maximum, duplicate, missing, cycle, overflow, and invalid-input cases;
- Time, memory, and cache behavior under untrusted, extreme, and adversarial input;
- Whether complexity claims match the actual implementation;
- Whether database query counts, I/O, network round trips, lock contention, and cache invalidation match the cost model;
- Performance only when it affected the choice, using representative load and a baseline option.

If evidence overturns the original recommendation, reopen the decision instead of defending the original option.

## Record durable decisions selectively

Keep ordinary choices in the implementation or current design notes. Suggest creating an ADR or project design document only when the choice is hard to reverse, truly involved trade-offs, and would surprise future maintainers without context.

## Collaborate with other skills

When available and directly relevant to the task, use `domain-modeling` for domain terms and invariants, `codebase-design` for module interfaces and seams, `prototype` for design questions that must be run to decide, and `tdd` to implement and verify behavior. When they are unavailable, complete the current task directly; do not invent capabilities or results. Do not copy those full workflows into this skill.

## Output format

When a material DSA choice exists, use this for simple decisions:

```text
DSA choice: <data structure or algorithm>
Reason: <why this is enough for the current need>
Complexity: <key operations>
```

For material decisions:

```text
Current needs and assumptions
Core operations and constraints
Two or three viable options
Option comparison and trade-offs
Recommendation and rationale
Conditions under which another option overtakes the recommendation
Items needing a user decision (only if any)
Correctness argument
Invariants, edge cases, resource risks, and verification plan
```

When there is no material DSA choice, do not use the formats above; answer the user request directly. Never let the output template override the applicability gate at the top.
