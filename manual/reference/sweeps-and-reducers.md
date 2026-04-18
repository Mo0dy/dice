# Sweeps and reducers

## Intention

Sweeps are the parameter-study surface of the language.

Use them when you want to ask questions like:

- what happens across armor classes
- which plan is best at each level
- what the best choice is after reducing over one axis but keeping another

This is one of the most useful differences between `dice` and a hand-worked spreadsheet.

## Exact semantics

Sweep construction is parsed in `diceparser.py`. The sweep container, indexing rules, reducer semantics, and coordinate-record behavior live in `diceengine.py`.

Important rules:

- `[a..b]` is an inclusive integer sweep.
- `[a..<b]` excludes the upper bound.
- `[name:a, b, c]` builds a named explicit sweep.
- Arithmetic and most operators lift over sweeps cellwise.
- `expr[...]` indexes an existing sweep.
- Indexing clauses can:
  - fix coordinates such as `[PLAN: "gwm"]`
  - filter domains such as `[AC in {12, 16}]`
  - reorder remaining axes such as `["AC", "PLAN"]`
  - use positional axis refs such as `[1, 0]`
  - use coordinate records returned by `argmaxover(...)`
- `sumover(expr, axes?)`, `meanover(expr, axes?)`, `maxover(expr, axes?)`, and `argmaxover(expr, axes?)` reduce sweep axes.
- If reducer `axes` is omitted, all sweep axes are reduced.
- `total(expr)` is shorthand for `sumover(...)` when there is exactly one named axis.

Current caveats from the runtime and tests:

- positional axis refs refer to the current visible axis order at that point in the expression
- explicit keep lists can reorder remaining axes, but they cannot drop still-unfixed axes yet

> Pitfall: positional refs become easier to misuse after a reorder. Named refs are usually safer.

## Examples

Named sweep:

```dice
d20 + 7 >= [AC:10..15]
```

Two-axis study:

```dice
~([PLAN:1, 2] + [AC:10, 11])
```

Fix one axis:

```dice
([PLAN:1, 2] + [AC:10, 11])[PLAN: 1]
```

Reorder remaining axes:

```dice
([PLAN:1, 2] + [AC:10, 11])["AC", "PLAN"]
```

Filter an axis:

```dice
([PLAN:1, 2] + [AC:10, 11, 12])[AC in {10, 12}]
```

Reduce one axis:

```dice
sumover([PLAN:1, 2] + [AC:10, 11], "PLAN")
```

Average across one axis:

```dice
meanover(d2 + [bonus:0, 1], "bonus")
```

Return winning coordinates:

```dice
argmaxover([PLAN:1, 2] + [AC:10, 11], "PLAN")
```

Use winning coordinates to gather values back out:

```dice
study = [PLAN:1, 2] + [LEVEL:10, 20] + [AC:100, 200]
best = argmaxover(study, ("PLAN", "LEVEL"))
study[best]
```
