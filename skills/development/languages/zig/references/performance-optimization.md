# Zig performance measurement and optimization

Use the target Zig version established in `SKILL.md`.

## Measure before optimizing

- Establish a reproducible performance baseline first, fixing the Zig version, target, optimization mode, inputs, warm-up procedure, execution environment, and sampling method.
- Locate the bottleneck before proposing a change; vary one major factor at a time while retaining correctness tests.
- Repeat measurements under the same conditions and report the distribution or variance rather than comparing only the single fastest result.
- Treat compile time, binary size, memory, throughput, and latency as separate metrics; optimize only the metrics the user cares about and that have been measured.

Claim a performance improvement only when the baseline, bottleneck evidence, post-change measurements, and correctness regression results are all available.
