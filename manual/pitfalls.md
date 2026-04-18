# Pitfalls

This page collects the language mistakes that are easy to make even when the syntax looks readable.

The recurring theme is that `dice` is exact and distribution-first. Expressions that look similar can still mean different stochastic processes.

## Independence versus arithmetic reuse

- `2d6` means two independent rolls added together.
- `d6 + d6` also means two independent rolls added together.
- `2 * d6` means one roll doubled.

Examples:

```dice
2d6
```

```dice
2 * d6
```

## Branching versus shared-roll branching

- `d20 >= 15 -> 8 | 0` is a simple Bernoulli branch.
- `split d20 | == 20 -> 16 | + 7 >= 15 -> 8 ||` shares one roll across several clauses.

Examples:

```dice
d20 >= 15 -> 8 | 0
```

```dice
split d20 | == 20 -> 16 | + 7 >= 15 -> 8 ||
```

## Membership versus thresholds

- use `==` for exact singleton checks such as `d20 == 20`
- use ordinary comparisons for contiguous thresholds such as `d20 >= 15`
- use `in` for genuine support membership such as `d20 in {1, 20}`

Examples:

```dice
d20 == 20
```

```dice
d20 >= 15
```

```dice
d20 in {1, 20}
```

## Positional sweep refs after reordering

Positional axis refs are evaluated against the current visible axis order, not the original order.

Example:

```dice
(([PLAN:1, 2] + [AC:10, 11])["AC", "PLAN"])[0: 10]
```

## Structured values are data, not comparison targets

Tuples and records can be stored and moved around, but tuple and record comparison and membership are not supported yet.

Examples:

```dice
(PLAN: "gwm", LEVEL: 11)
```

```dice
d{(1,), (2,)}
```
