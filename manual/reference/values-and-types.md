# Values and types

## Intention

`dice` works with a small set of runtime shapes:

- exact distributions such as `d20`
- finite weighted supports such as `{10, 15}` or `{"fire" @ 2, "ice"}`
- sweeps such as `[AC:10..20]`
- structured values such as tuples and records

Most user code does not need to think in terms of implementation classes, but it helps to know what kind of value an expression produces.

## Exact semantics

These runtime shapes are implemented in `diceengine.py`.

- `FiniteMeasure` is a finite weighted support. Weights are relative and do not need to sum to `1`.
- `Distribution` is a normalized probability distribution.
- `Sweep[T]` is a collection of cells indexed by one or more sweep axes.
- `tuple` values are immutable ordered structures.
- `record` values are immutable keyed structures.

Useful exact rules:

- `{a, b, c}` creates a finite measure with unit weights.
- `{value @ weight, ...}` attaches explicit relative weights.
- `d{...}` normalizes a finite measure into a distribution.
- `[a..b]`, `[a..<b]`, and `[a, b, c]` create unnamed sweeps.
- `[name:...]` creates a named sweep.
- `()` is the empty tuple.
- `(1,)` is a one-element tuple.
- `(PLAN: "gwm", LEVEL: 11)` is a record.

Current limitations from `diceengine.py` and the tuple/record tests:

- tuple and record comparisons are not supported yet
- tuple and record membership tests with `in` are not supported yet
- tuple and record field access is not supported yet

## Examples

Finite measure:

```dice
{10, 15, 20}
```

Weighted finite measure:

```dice
{"fire" @ 2, "ice"}
```

Distribution from a measure:

```dice
d{10, 15}
```

Named sweep:

```dice
[AC:10..12]
```

Tuple and record values:

```dice
(1, "fire")
```

```dice
(PLAN: "gwm", LEVEL: 11)
```

Inspect the outer runtime type:

```dice
type(d20 >= [AC:10..12])
```

Inspect sweep shape:

```dice
shape(d20 >= [AC:10..12])
```
