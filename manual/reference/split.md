# Split

## Intention

Use `split` when one roll should be shared across several decisions.

This matters whenever a later check should reuse the same outcome instead of rolling again. Critical-hit logic is the most common tabletop example.

If you only need a yes/no branch, `condition -> hit | miss` is simpler. If you need shared-roll branching, use `split`.

## Exact semantics

`split` is parsed explicitly in `diceparser.py` and evaluated in `interpreter.py`.

The runtime model is:

- evaluate the `split` value once as a distribution
- bind each possible outcome to the split name
- test clauses from top to bottom
- send matched probability mass to the clause result
- leave unmatched mass available for later clauses
- use `otherwise` or `||` for the final fallback

Surface rules:

- `split expr as name` gives the shared outcome an explicit name
- `split expr` binds the shared outcome to `@`
- `| guard -> expr` adds a guarded clause
- `| otherwise -> expr` takes the remaining cases
- `||` is shorthand for `| otherwise -> 0`

Guard rules:

- split guards must evaluate to Bernoulli `0`/`1` outcomes
- when you use an explicit binding name, relative guard sugar is not allowed
- anonymous `split` may use relative forms such as `| == 20 -> ...` and `| + 7 >= 16 -> ...`

If you omit a final fallback, the runtime appends an implicit `0` branch and emits a warning.

> Pitfall: later clauses only see the cases that were not already matched. They do not re-check the full original distribution.

> Pitfall: `split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||` does not mean “if d20 + 5 >= 15”. The second clause only sees non-20 results.

## Examples

Anonymous shared roll:

```dice
split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||
```

Explicit binding:

```dice
split d20 as roll | roll == 20 -> 10 | roll + 5 >= 15 -> 5 ||
```

Shared-roll weapon logic:

```dice
split d20 | == 20 -> 2 d 8 + 4 | + 7 >= 16 -> 1 d 8 + 4 ||
```

Multiline helper built from split:

```dice
longsword_attack(ac, bonus=7, mod=4):
    split d20 | == 20 -> 2 d 8 + mod | + bonus >= ac -> 1 d 8 + mod ||
longsword_attack([AC:10..18]) $ mean
```
