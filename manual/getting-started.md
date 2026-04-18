# Getting started

## Intention

`dice` is meant to make common tabletop probability work easy to read without giving up exact semantics.

You can start with a few ideas:

- `d20` means one twenty-sided die
- `2d6` means roll two six-sided dice and add them
- comparisons such as `d20 >= 15` produce success and failure outcomes
- `-> ... | ...` turns a success check into a result distribution
- sweeps such as `[AC:10..20]` let you study a changing input across many values

The language stays readable because most expressions look close to how people already talk about attacks, saves, damage, and parameter studies at the table.

## Exact semantics

The parser treats programs as newline- or semicolon-separated statements in `diceparser.py`, and the runtime evaluates them through `interpreter.py` and `diceengine.py`.

Important exact points:

- `d20` is a normalized probability distribution, not a sampled number.
- `2d6` is not the same thing as `2 * d6`. The first rolls twice and adds independent results. The second doubles one roll's outcome.
- `d20 >= 15` is a Bernoulli distribution over `1` and `0`.
- `d20 >= 15 -> 8 | 0` branches on that Bernoulli result.
- `~expr` and `mean(expr)` turn a numeric distribution into its expectation as a deterministic result.

> Pitfall: independence matters. `2d6` means two independent rolls. `d6 + d6` also means two independent rolls. `2 * d6` does not.

## Examples

Single die:

```dice
d20
```

Sum of dice:

```dice
2d6
```

Simple hit chance:

```dice
d20 >= 15
```

Hit for fixed damage:

```dice
d20 >= 15 -> 8 | 0
```

Expected damage:

```dice
(d20 >= 15 -> 8 | 0) $ mean
```

Damage across armor classes:

```dice
(d20 + 7 >= [AC:10..20] -> 1 d 8 + 4 | 0) $ mean
```

Shared helper functions:

```dice
hit(ac, bonus=7): d20 + bonus >= ac
damage(ac, bonus=7): hit(ac, bonus=bonus) -> 1 d 8 + 4 | 0
damage([AC:10..20]) $ mean
```
