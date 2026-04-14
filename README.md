# dice

`dice` is a small language for tabletop dice and probability calculations.

This README is intentionally brief during the rewrite. For now, treat it as the user-facing reference for the currently tested language semantics.

## Values

- `Distrib`: one probability distribution such as a d20 roll
- `Distributions`: one or more probability distributions indexed by zero or more sweep axes
- `Sweep`: a finite set of input values, usually created with bracket syntax
- symbolic outcomes such as `true` and `false`

## Semantics

- `d20` rolls one die and returns a probability distribution.
- `2d6` rolls multiple dice and sums them.
- `>=`, `<=`, `<`, `>`, `==` return boolean distributions over `true` and `false`.
- `->` applies the `true` branch of a boolean distribution to another distribution.
- `|` adds an else-branch to `->`.
- `|/` is shorthand for “else, use half damage”.
- `[a:b]` creates an unnamed sweep over an inclusive integer range.
- `[a, b, c]` creates an unnamed sweep over explicit values.
- `expr[index]` filters a distribution by one value or sweep of values.
- `+`, `-`, `*`, `/` combine numeric distributions.
- `d+20` and `d-20` mean advantage and disadvantage.
- `3d20h1` and `3d20l1` mean roll many dice and keep the highest or lowest subset.
- `!expr` returns total probability mass as a degenerate distribution.
- `~expr` returns expectation as a degenerate distribution.
- `( ... )` groups expressions.

## Running Dice

The CLI has three modes:

- REPL: `python3 dice.py interactive`
- Direct one-off evaluation: `python3 dice.py execute "d20 >= 11 -> 5"`
- Run a dice program from a file: `python3 dice.py file path/to/program.dice`

The `file` mode parses a dice program, not Markdown or plain notes. Multi-line programs are separated by newlines or `;`.

Useful flags:

- `-r N` rounds numeric output, for example `python3 dice.py -r 2 execute "d20 >= 11"`
- `-g` prints a grep-friendly single-line result
- `-v` prints the input together with the result
- `-p` shows the result with `viewer.do(...)` after `execute`

## Output Modes

There are a few different ways to read the result depending on what you want:

- Raw distribution output:
  `d20` or `2d6` returns a probability distribution.
- Boolean distributions:
  `d20 >= 11` returns a distribution over `true` and `false`.
- Swept distributions:
  `d20 >= [5:10]` returns one boolean distribution for each sweep value.
- Branched distributions:
  `d20 >= 11 -> 5 | 0` returns a weighted outcome distribution.
- Scalar summaries:
  `~(d20 >= 11 -> 5 | 0)` returns a degenerate distribution containing the expected value and `!d20[19:20]` returns probability mass for each selected branch.
- Plots through Matplotlib:
  use `label`, `xlabel`, `ylabel`, `plot`, and `show` in a multi-statement program when you want a graph.

Example plotting program:

```bash
python3 dice.py file path/to/plot.dice
```

```text
xlabel "AC"
ylabel "chance"
label "attack"
plot d20 >= [10:20]
show
```

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
