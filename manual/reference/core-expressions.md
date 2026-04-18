# Core expressions

## Intention

The core expression layer covers the things people reach for first:

- rolling dice
- combining them with arithmetic
- checking success or failure
- turning success into damage or some other result
- repeating an expression independently
- summarizing a distribution

This is the part of the language that should feel closest to tabletop reasoning.

## Exact semantics

The parser handles these operators in `diceparser.py`, while the exact math lives in `diceengine.py`.

Important rules:

- `d20` rolls one die and returns a distribution.
- `2d6` rolls twice and sums the outcomes.
- `3d20h1` and `3d20l1` roll many dice and keep the highest or lowest subset.
- `d+20` and `d-20` are advantage and disadvantage forms.
- `+`, `-`, `*`, `/`, and `//` lift over numeric distributions.
- `>=`, `<=`, `<`, `>`, and `==` return Bernoulli `0`/`1` distributions.
- `in` checks membership against a finite measure or domain.
- `success -> hit | miss` branches on the `1` and `0` outcomes of a Bernoulli distribution.
- `@` inside an else branch refers to the already evaluated branch result.
- A leading operator in the else branch is relative to that `@`, so `| / 2` means `| @ / 2`.
- `expr ^ n` repeats `expr` independently `n` times and sums the results.
- `repeat_sum(n, expr)` is the explicit callable form of the same operation.
- `~expr` and `mean(expr)` return expectation as a deterministic value.
- `sample(expr)` samples one outcome and returns it as a deterministic distribution.
- `var(expr)`, `std(expr)`, `cum(expr)`, and `surv(expr)` provide common summaries and transformed views.
- `expr $ f` pipes the left value into the first argument of `f`.

> Pitfall: `d6 ^ 2` means two independent evaluations added together. It is not exponentiation.

> Pitfall: `d20 < 14 -> 2d10 | / 2` halves the hit branch result. The `| / 2` form is shorthand for `| @ / 2`.

## Examples

Arithmetic over distributions:

```dice
d8 + 3
```

Advantage and keep-high:

```dice
d+20
```

```dice
3d20h1
```

Membership versus threshold checks:

```dice
d20 in {1, 20}
```

```dice
d20 >= 15
```

Branching damage:

```dice
d20 + 7 >= 15 -> 2 d 6 + 4 | 0
```

Relative else branch:

```dice
d20 < 14 -> 2d10 | / 2
```

Independent repetition:

```dice
d6 ^ 3
```

Expectation:

```dice
(d20 + 7 >= 15 -> 2 d 6 + 4 | 0) $ mean
```

Cumulative and survival views:

```dice
cum(d20)
```

```dice
surv(d20)
```
