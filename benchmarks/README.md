# Benchmarks

Exploratory performance benchmarks live here instead of under the runtime or
the example library.

Current benchmark workloads:

- `hexed_scorching_ray`
  A deep D&D damage sweep used to compare the exact `dice` runtime against
  Monte Carlo implementations.

Recommended entry point:

```bash
python3 /home/felix/_Documents/Projects/dice/benchmarks/hexed_scorching_ray/run.py --backend numpy --sample-counts 4000 16000
```

Notes:

- These benchmarks are intentionally exploratory and are not part of the
  shipped module surface.
- The NumPy backend still rolls primitive dice directly. It does not use
  precomputed alias tables, PMFs, or other derived stochastic primitives.
