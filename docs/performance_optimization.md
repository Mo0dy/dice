# Performance Optimization

This note summarizes the current performance findings and applied optimizations
for the exact engine. It is meant as a short handoff document for future
sessions.

## Main Benchmarks Used

Two benchmark families were useful because they stress different parts of the
 engine:

- `benchmarks/hexed_scorching_ray/`
  Heavy exact additive convolution over structured integer damage
  distributions.
- `benchmarks/chaos_bolt_chain/`
  Heavy recursive branching and split accumulation with much more branch churn
  than plain additive convolution.

These benchmarks should be read together. One is not a substitute for the
other.

## Applied Optimizations

### 1. Exact builtins moved onto the `@dicefunction` path

Pure exact builtins were moved toward the decorated path so lifting and caching
can be handled centrally.

Important practical result:

- `@dicefunction(cache=True)` now caches pure exact non-sweep calls through
  Python `lru_cache`

This made persistent reuse practical for exact subproblems.

### 2. `repeat_sum(...)` now uses recursive repeated squaring

`repeat_sum(...)` was rewritten away from linear repeated addition and now
recurses through the cached decorated function itself.

Important consequences:

- repeated exact sum subproblems are reused across the whole execution
- `repeat_sum(8, X)` and `repeat_sum(9, X)` share work
- later identical calls hit the decorator cache directly

The old local `repeat_sum_with(...)` cache was removed from the exact path.

### 3. Exact `roll(...)` currently lowers to `repeat_sum(...)`

The exact `roll(n, s)` path now lowers through:

- `rollsingle(s)`
- `repeat_sum(n, rollsingle(s))`

This keeps the arithmetic path unified, though it is not always the fastest
possible implementation for deterministic `NdS`.

### 4. Dense integer-support additive convolution

The core exact `add(...)` path now has a dense integer-support fast path.

First version:

- only contiguous integer supports

Current version:

- bounded integer support with holes allowed
- missing integers are treated as zero-probability entries
- guarded by a span/density heuristic so very sparse huge ranges still fall back
  to the generic path

Current heuristic in `diceengine.py`:

- dense path only if outcomes are all `int`
- let `span = max - min + 1`
- let `nonzero_count = number of occupied outcomes`
- allow dense path when `span <= max(nonzero_count * 8, 256)`

This widened path matters because many attack-result distributions look like:

- miss spike at `0`
- contiguous positive hit band
- contiguous crit band

These are not contiguous supports, but they are still dense enough to benefit
from array-style convolution.

## Observed Effects

### Hexed Scorching Ray

This benchmark responded strongly to additive optimizations.

Important progression:

- pre-optimization exact sweep was much slower
- after recursive `repeat_sum(...)` and integer add fast paths, the exact sweep
  dropped dramatically
- after widening the dense-support criterion to allow holes, the exact sweep
  dropped again to roughly half a second on the current machine

Most recent exact wall-clock observation:

- `benchmarks/hexed_scorching_ray/exact_dice.py` full exact sweep around
  `0.5s`

Profile conclusion after the widened integer fast path:

- old `_pairwise_numeric(...)` hotspot mostly disappeared for this workload
- main hotspot became `_convolve_dense_integer_add(...)`
- `_canonicalize_weighted_entries(...)` is still present, but much smaller than
  before

### Chaos Bolt Chain

Chaos Bolt exposed a very different hotspot shape.

Important observation:

- additive convolution is not the dominant cost
- the dominant cost is branch handling and repeated canonicalization

The main exact profile path was:

- `Interpreter.visit_Split(...)`
- `FiniteMeasure.__init__(...)`
- `_canonicalize_weighted_entries(...)`
- `_accumulate_distribution_contributions(...)`

This means:

- Chaos Bolt is mainly stressing generic split/branch execution
- not primarily the additive convolution core

That distinction is important when evaluating future optimizations.

## What The Traces Currently Suggest

### For additive exact workloads

Likely next targets:

- more comparison fast paths, especially deterministic-scalar threshold cases
- balanced reduction for additive folds such as `sumover(...)` and `total(...)`
- possibly off-the-shelf direct array convolution for large integer-support
  exact convolutions if integrated carefully

### For branch-heavy exact workloads

Likely next targets:

- delay canonicalization inside `visit_Split(...)`
- accumulate raw weighted branch contributions in dicts or raw buffers first
- canonicalize once at the end instead of once per temporary branch object
- reduce temporary `Sweep` / `FiniteMeasure` churn
- add cheaper handling for deterministic or Bernoulli branch conditions

## FFT / Array Convolution Findings

An experiment was run comparing the current exact dense integer convolution
against:

- `numpy.convolve`
- manual NumPy FFT convolution
- `scipy.signal.convolve`
- `scipy.signal.fftconvolve`

Findings:

- FFT was not attractive for the current benchmark workloads
- off-the-shelf direct array convolution could be much faster on very large
  exact integer convolutions such as `150d100`
- but float64-based array convolution loses tiny tail support, so it behaves as
  a high-precision approximation rather than a strictly exact replacement

Current conclusion:

- skip FFT for now
- array-direct convolution is promising for large integer-support cases, but not
  yet suitable as an exact drop-in path without additional work

## Possible Language Features With Performance Value

The Chaos Bolt profile suggests a possible language/runtime feature seam:

- a `match` / structured decision-tree construct

Why:

- many workloads currently use generic `split` to express exact equality and
  threshold branching
- a structured match-like construct could expose more information to the runtime
- that would allow a more specialized execution path than the current generic
  split accumulation model

This could be a genuine performance feature, not only syntax sugar.

## Practical Guidance For Future Sessions

When profiling:

- use `hexed_scorching_ray` to study arithmetic / convolution behavior
- use `chaos_bolt_chain` to study split / branching behavior

When reading traces:

- if `_pairwise_numeric(...)` dominates, the exact add path still needs work
- if `_canonicalize_weighted_entries(...)` dominates through `visit_Split(...)`,
  the split engine is the real target

When optimizing:

- do not assume one benchmark generalizes to the other
- always check whether the workload is convolution-dominated or split-dominated
