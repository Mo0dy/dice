# Python Extension Samples

These examples are part of the executable sample library and are covered by JSON snapshot regressions.

Each sample exposes a `build_result()` function that returns a dice runtime value. The regression harness loads the file, calls `build_result()`, and snapshots the serialized result.

Included examples:

- `untyped_cellwise.py`: `@dicefunction` lifts untyped parameters over projected cell values
- `typed_distribution.py`: `@dicefunction` with `Distribution` parameters auto-lifts cellwise
- `typed_sweep.py`: `@dicefunction` with `Sweep[...]` parameters receives the full sweep container
- `weighted_measure.py`: Python helpers can return `FiniteMeasure`, which is normalized through `d ...`
