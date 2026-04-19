# Benchmarks

Exploratory performance benchmarks live here instead of under the runtime or
the example library.

Current benchmark workloads:

- `hexed_scorching_ray`
  A deep D&D damage sweep used to compare the exact `dice` runtime against
  Monte Carlo implementations.
- `chaos_bolt_chain`
  A bounded multi-target Chaos Bolt cascade with repeated attack rolls,
  conditional jumps, and deeper roll-dependent stop logic.

## Headline takeaway

For additive combat sweeps like `hexed_scorching_ray`:

- Dice is a lot more accurate and much faster than naive Monte Carlo.
- Dice is in the same ballpark as a more optimized Monte Carlo version while
  also being exact and much easier to write.

For branch-heavy exact workloads like `chaos_bolt_chain`, the exact engine is
still slower than the optimized Monte Carlo path today. That benchmark remains
useful as the current stress test for `split`/decision-tree execution.

## Headline image

The plot below is intended for the README and compares the exact `dice`
distribution against NumPy Monte Carlo at `4,000` and `32,000` samples per
cell.

![Hexed Scorching Ray accuracy comparison](docs/images/hexed_scorching_ray_accuracy.png)

Generated with:

```bash
python3 /home/felix/_Documents/Projects/dice/benchmarks/hexed_scorching_ray/run.py \
  --plot-path /home/felix/_Documents/Projects/dice/docs/images/hexed_scorching_ray_accuracy.png
```

## Current numbers

### Hexed Scorching Ray

Timing scope: full exact sweep across `1,260` cells.

| Backend | Samples / cell | Scope | Time (s) | vs dice | Rep. mean abs err |
| --- | --- | --- | --- | --- | --- |
| dice exact | - | full sweep (1,260 cells) | 0.500 | 1.00x | 0.0000 |
| Naive Python Monte Carlo | 4,000 | full sweep (1,260 cells) | 32.885 | 65.81x | 0.2184 |
| Vectorized NumPy Monte Carlo | 4,000 | full sweep (1,260 cells) | 0.353 | 0.71x | 0.2923 |
| Vectorized NumPy Monte Carlo | 32,000 | full sweep (1,260 cells) | 0.662 | 1.32x | 0.0861 |

### Chaos Bolt Chain

Timing scope: full sweep for the `small` preset (`48` cells).

| Backend | Samples / cell | Scope | Time (s) | vs dice | Rep. mean abs err |
| --- | --- | --- | --- | --- | --- |
| dice exact | - | full sweep (48 cells) | 18.626 | 1.00x | 0.0000 |
| Naive Python Monte Carlo | 4,000 | full sweep (48 cells) | 0.372 | 0.02x | 0.1277 |
| Vectorized NumPy Monte Carlo | 4,000 | full sweep (48 cells) | 0.079 | <0.01x | 0.1298 |
| Vectorized NumPy Monte Carlo | 32,000 | full sweep (48 cells) | 0.114 | <0.01x | 0.0109 |

## Commands

```bash
python3 /home/felix/_Documents/Projects/dice/benchmarks/hexed_scorching_ray/run.py
```

```bash
python3 /home/felix/_Documents/Projects/dice/benchmarks/chaos_bolt_chain/run.py
```

Notes:

- These benchmarks are exploratory and are not part of the shipped module
  surface.
- The NumPy backend still rolls primitive dice directly. It does not use
  precomputed alias tables, PMFs, or other derived stochastic primitives.
- The NumPy backend can split each state's trial count evenly across worker
  processes with `--numpy-processes N`.
- The Chaos Bolt runner now benchmarks preset-based full sweeps generated from
  Python. Use `--preset medium` or `--preset large` when you want to push the
  workload further, but expect exact full-sweep cost to grow quickly on the
  branch-heavy presets.
