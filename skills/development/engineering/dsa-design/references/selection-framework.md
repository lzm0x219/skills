# Selection framework

Use this reference when generating candidates from operation patterns and constraints. It is a starting point, not an automatic answer.

## Operation patterns

| Need                                    | Prefer first                                           | Consider with strong justification                                                    |
| --------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Positional access over fixed small data | Array or tuple                                         | Precomputed table or bitset                                                           |
| Compile-time fixed key set              | Record, struct, or enum-indexed array                  | Map when the key set must change dynamically                                          |
| Lookup by stable key                    | Hash map                                               | Ordered map or database index                                                         |
| Membership and uniqueness               | Set                                                    | Bitset for a small dense universe                                                     |
| Last-in first-out processing            | Stack or array tail                                    | Segmented stack                                                                       |
| First-in first-out processing           | Queue or deque                                         | Bounded ring buffer                                                                   |
| Insert and delete at both ends          | Deque                                                  | Ring buffer                                                                           |
| Preserve insertion order                | Array plus map                                         | Ordered map                                                                           |
| Ordered traversal or range queries      | Sorted array or database index                         | Balanced tree or B-tree                                                               |
| Repeated min or max extraction          | Heap                                                   | Balanced tree or bucket queue                                                         |
| Frequent priority updates or cancel     | Heap plus key map                                      | Indexed heap or balanced tree                                                         |
| Top-K retrieval                         | Heap of size K                                         | Quickselect, bucketing, or database aggregation                                       |
| Prefix search                           | Sorted array                                           | Trie or database text index                                                           |
| Fixed dense relations                   | Matrix or precomputed table                            | Bitset rows                                                                           |
| Sparse dynamic relations                | Adjacency list                                         | Specialized graph index                                                               |
| Dependency ordering                     | DAG plus topological sort                              | Incremental dependency maintenance                                                    |
| Dynamic connectivity                    | Graph traversal                                        | Union-find when edges are not deleted                                                 |
| Shortest paths                          | BFS for unit weight; Dijkstra for non-negative weights | A* with a correctness-preserving heuristic; specialized algorithms for negative edges |
| Overlapping intervals                   | Sorted endpoints                                       | Interval tree or sweep line                                                           |
| Repeated pure computation               | Recompute directly                                     | Memoization or bounded cache                                                          |
| Repeated aggregate updates              | Full recompute baseline                                | Incremental aggregates or materialized views                                          |
| Small one-off filtering                 | Linear scan                                            | Index only with evidence of repeated queries                                          |
| Data larger than memory                 | Single-pass streaming                                  | External sort, chunked merge, or database execution                                   |
| Approximate membership                  | Exact set                                              | Bloom filter when false positives are acceptable                                      |
| Approximate cardinality                 | Exact set                                              | HyperLogLog when error is acceptable                                                  |
| Spatial range or nearest neighbor       | Linear scan or database spatial index                  | R-tree, k-d tree, or grid index                                                       |

## Algorithm patterns

- Use direct indexing and modular arithmetic for fixed cyclic domains.
- Use lookup tables for finite, stable rule maps.
- Use sorting when one preprocessing sort simplifies many later operations.
- Use two pointers or a sliding window only when order and monotonic movement preserve correctness.
- Use binary search only when the searched relation is ordered and can stay ordered.
- Before graph algorithms, explicitly model nodes, edges, direction, weights, and update behavior.
- Use dynamic programming only when you can prove overlapping subproblems and a reusable state definition.
- Use greedy algorithms only when you can argue the local-optimality property.
- Use caching only with stable keys, an acceptable invalidation policy, bounded memory, and a credible reuse rate.

## Non-asymptotic checks

Compare:

- Constant factors and real maximum scale;
- Memory layout, locality, allocation, and garbage collection;
- Database query counts, disk access, network round trips, and serialization;
- Mutability and synchronization cost;
- Lock contention, memory-ordering requirements of lock-free structures, and backpressure;
- Persistence and serialization;
- Cache keys, capacity, eviction, invalidation, and pollution risk;
- Standard-library and database support;
- Determinism and iteration order;
- Observability and explainability;
- Implementation, testing, and migration cost.

## Over-engineering signals

Prefer the baseline when:

- The dataset is fixed or small;
- Operation frequency is low;
- The database already provides the needed index;
- There is no measurable constraint behind a specialized structure;
- The design targets only vague future growth;
- The data structure leaks into many caller interfaces;
- Maintaining invariants costs more than the operations they accelerate.

## Adversarial-input checks

- Do not rely only on average-case hash complexity; check runtime collision defenses and worst-case behavior.
- Bound resources for user-controlled key counts, queue lengths, recursion depth, cache entries, and intermediate results.
- Identify expensive paths an attacker can amplify through input size, structure, or distribution; especially avoid superlinear or exponential work without a demand or lower-bound justification, and without input or resource bounds.
- `O(n log n)` algorithms with clear functional need or complexity lower bounds, such as sorting, can be reasonable; still assess resource risk against maximum input, time, memory, and concurrency limits.
- For approximate structures, state the concrete error mode (false positives, false negatives, or estimation bias), error bounds, and the impact of attacker-controlled distributions.
- For streaming and concurrent structures, state backpressure, drop, blocking, and overload policies.
