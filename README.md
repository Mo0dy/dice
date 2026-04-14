# dice

`dice` is a small language for tabletop dice and probability calculations.

This README is intentionally brief during the rewrite. For now, treat it as the user-facing reference for the currently tested language semantics.

## Values

- `int`: plain integers
- `Distrib`: probability distributions such as a d20 roll
- `ResultList`: target-to-value tables, commonly used for hit chance or resolved damage
- `list`: integer lists and ranges

## Semantics

- `d20` rolls one die and returns a distribution.
- `2d6` rolls multiple dice and sums them.
- `>=`, `<=`, `<`, `>`, `==` compare values or distributions.
- `->` resolves a `ResultList` against damage or another distribution.
- `|` adds an else-branch to `->`.
- `|/` is shorthand for “else, use half damage”.
- `[a:b]` creates an inclusive integer range.
- `[a, b, c]` creates an explicit integer list.
- `expr[index]` filters a distribution by one value or a list/range of values.
- `+`, `-`, `*`, `/` work on integers and the language collection types.
- `d+20` and `d-20` mean advantage and disadvantage.
- `3d20h1` and `3d20l1` mean roll many dice and keep the highest or lowest subset.
- `!expr` returns the total probability of a distribution subset.
- `~expr` returns the average of a distribution.
- `( ... )` groups expressions.

## Examples

```dice
d20
2d6
d20 >= 11
[5:7]
d20 == [5:7]
d20 >= [5,11]
d20 >= 11 -> 5
d20 >= 11 -> 2d6
d20 >= 11 -> 10 | 5
d20 < 14 -> 2d10 |/
d20[19:20]
d20[20] >= 14
d20[20] >= 14 -> 10
1 + 1
3 / 2
d2 + d2
[1:2] + 1
d+20
!d20[19:20]
~2d6
d-20
3d20h1
3d20l1
```

## Development Note

The examples above are executed by the test suite. If you change syntax or semantics, update the examples and the runtime together.
