# Worked examples

Use these examples to calibrate output depth. Do not copy the choices before rechecking the current need.

## Small CRUD lookup

Need: store about ten configuration records and fetch them by ID.

Analysis:

- A linear array is simplest. Lookup is `O(n)`, but `n` is small with a clear upper bound.
- When the key set is fixed at compile time and every key must exist, prefer a record, struct, or enum-indexed array.
- When the key set or entries must grow and shrink at runtime, a hash map provides expected `O(1)` lookup.
- Trees or custom indexes are not worth considering as candidates.

Output: keep it short. Choose among array, record/struct, and map based on whether keys are fixed and entries are dynamic. Do not pause implementation for this internal choice; if the user did not explicitly ask for code, do not attach a full implementation.

## Zi Wei Dou Shu charting engine

Need: design a charting engine with twelve palaces, placement rules, rule dependencies, multiple schools, and explainable results.

Viable candidates:

1. Represent the fixed twelve-palace cycle with length-12 arrays and modular arithmetic, precomputing stable palace relationships.
2. Add bitset rows when relational set operations are frequent and the language supports efficient bit operations.
3. Use a general graph only when relations become dynamic, user-defined, or need general graph traversal.

For rule execution, compare a "rule registry plus direct ordering" with a "dependency DAG plus topological sort". Recommend a DAG only when real rule dependencies require ordering or cycle detection.

Treat explainability as part of correctness: return or record the rule, inputs, and rationale for every derived result. Treat school differences as interface decisions and wait for user confirmation before implementing.

## Dynamic task scheduler

Need: support insert, priority update, cancel, and extract-highest-priority task.

Viable candidates:

1. Binary heap plus key-to-position map: extract-max and updates are efficient, but the position-map invariant raises implementation cost.
2. Balanced ordered map keyed by priority and sequence: when the language provides one, ordered updates can complete in `O(log n)`.
3. Sorted array: good for small, read-heavy workloads; insert and cancel remain `O(n)`.

Recommend based on real scale, update frequency, cancel frequency, stable-ordering requirements, and standard-library support. Because candidates change invariants and maintenance cost, present options and wait for the user to choose.

## Top-K over an untrusted event stream

Need: continuously receive events from a public interface and track the most frequent K keys; keys are user-controlled and the number of unique keys may be large.

Viable candidates:

1. Exact hash-map counts, sorted at the end: exact and simple, but memory grows with unique keys.
2. Exact hash-map counts plus a heap of size K: reduces final sort cost, but still does not bound the count table's memory.
3. Count-Min Sketch plus a Top-K candidate set: memory-bounded and streaming-friendly, but results have quantifiable error.

Before recommending, determine whether exact results are required, the maximum unique-key count, memory budget, and event rate. Regardless of option, consider hash-collision defenses, key-length limits, resource quotas, and overload policy. If exactness versus bounded memory implies different interface semantics, wait for the user to choose first.
