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
- `[name:a:b]` creates a named sweep over an inclusive integer range.
- `[name:a, b, c]` creates a named sweep over explicit values.
- `expr[index]` filters a distribution by one value or sweep of values.
- `f(x) = expr` defines a top-level one-line function.
- `f(a, b)` calls a user-defined function inside an expression.
- `match expr as name | guard = expr | ... | otherwise = expr` reuses one shared value across guarded branches.
- `repeat_sum(n, expr)` evaluates `expr` independently `n` times and adds the results.
- `sumover("axis", expr)` adds results across one named sweep axis and preserves the others.
- `total(expr)` is shorthand for `sumover(...)` when `expr` has exactly one named sweep axis.
- `render(expr)` renders one result with smart defaults.
- `render(expr1, "label1", expr2, "label2")` compares multiple compatible results.
- `expr $ f` passes `expr` as the first argument to `f`.
- `expr $ f(a, b)` passes `expr` as the first argument to `f(expr, a, b)`.
- `import "path/to/file.dice"` loads another dice file once. Relative paths resolve from the importing file, absolute paths resolve from the filesystem root, and `std:...` resolves from dice's packaged standard library.
- `+`, `-`, `*`, `/` combine numeric distributions.
- `d+20` and `d-20` mean advantage and disadvantage.
- `3d20h1` and `3d20l1` mean roll many dice and keep the highest or lowest subset.
- `!expr` samples one outcome and returns it as a degenerate distribution.
- `~expr` returns expectation as a degenerate distribution.
- `mean(expr)`, `sample(expr)`, and `mass(expr)` are explicit summary helpers.
- `var(expr)` and `std(expr)` return variance and standard deviation as degenerate distributions.
- operator-backed semantics are also available as functions such as `add(...)`, `roll(...)`, `greaterorequal(...)`, and `reselse(...)`.
- `( ... )` groups expressions.

## Running Dice

The CLI has three modes:

- REPL: `python3 dice.py --interactive`
- Direct one-off evaluation: `python3 dice.py "d20 >= 11 -> 5"`
- Run a dice program from a file: `python3 dice.py --file path/to/program.dice`

The `--file` mode parses a dice program, not Markdown or plain notes. Multi-line programs are separated by newlines or `;`.
Use `import "relative/path.dice"` inside files when you want to share helpers across programs. Use `import "/absolute/path/to/file.dice"` for explicit filesystem imports and `import "std:dnd/weapons.dice"` for packaged helpers.

Useful flags:

- `-R N` or `--round N` rounds displayed numeric output. The CLI defaults to `-R 2`.
- Rounded values that land exactly on an integer display without trailing decimal zeros.
- `--json` prints structured JSON objects for tool-facing integrations.
- `-v` prints the input together with the result

The interactive shell also supports a few lightweight host commands before parsing dice source:

- `$ set_round N` changes the REPL display rounding for later commands
- `Ctrl-P` / `Ctrl-N` navigate command history on terminals with `readline` support
- command history is persisted between sessions when the local state directory is writable

## Output Modes

There are two main CLI output modes:

- default text mode for humans
- `--json` for tools and scripts

Default text mode prettifies common result shapes:

- deterministic distributions collapse to one displayed value
- unswept distributions print as `value: probability` lines
- one-axis scalar sweeps print one value per line with the axis name shown at most once
- one-axis full distributions print as tables with outcomes on rows and sweep values on columns
- two-axis scalar sweeps print as tables with a compact corner label such as `AC/BONUS`
- unnamed axes stay blank in table headers instead of using fallback labels

Examples:

```text
false: 0.50
true: 0.50
```

```text
/AC
10: 2.75
11: 2.50
12: 2.25
```

```text
  /AC    10    11    12
false  0.45  0.50  0.55
 true  0.55  0.50  0.45
```

```text
AC/BONUS   1   2
      10  11  12
      11  12  13
```

Use `render(...)` in a program when you want a graph instead of text output.

Example rendering program:

```bash
python3 dice.py --file path/to/plot.dice
```

```text
render(d20 >= [AC:10:20] -> 5 | 0 $ mean)
```

## Functions

User-defined functions are one-line top-level definitions.

- Parameters shadow globals.
- Functions may call other functions.
- Forward references work across a program.
- Recursion is not supported.

Examples:

```text
hit(ac) = d20 >= ac
damage(ac) = hit(ac) -> 5 | 0
crit(ac, dmg) = d20 == 20 -> dmg | 0
match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0
repeat_sum(3, d2)
sumover("party", [party:1, 2, 3])
total([party:1, 2, 3])
render(d20 >= [AC:10:20] -> 5 | 0 $ mean)
```

## Whitespace

Compact dice forms still work for literal-style expressions:

- `d20`
- `2d6`
- `3d20h1`
- `3d20l1`

When identifiers are involved, write dice operators with spaces so they remain separate tokens:

- `count d sides`
- `d sides`
- `count d sides h keep`
- `count d sides l keep`

Compact names like `adb` or `ad20` stay ordinary identifiers. Strings also preserve internal spaces now, for example `"fire bolt"`.

## Rendering

- `render(expr)` renders one expression result immediately.
- `render(expr1, "a", expr2, "b")` compares multiple compatible results on one chart.
- Axis labels come from named sweeps like `[AC:10:20]`.
- Unnamed sweeps still render, but use fallback axis labels.
- Supported quick-render shapes are:
  unswept distributions, one-sweep scalar results, one-sweep full distributions, and two-sweep scalar results.

## Python Integration

You can also keep a persistent dice session from Python:

```python
from dice import dice_interpreter
from diceengine import greaterorequal, rollsingle

session = dice_interpreter()
result = session("d20 >= [AC:10:12] -> 5 | 0")
session.assign("cached", result)
session("render(cached)")

direct = greaterorequal(rollsingle(20), 11)
```

Pass `executor=...` to `dice_interpreter(...)` when you want a non-default backend. Register Python functions with `session.register_function(...)`. Registered functions receive eagerly evaluated runtime values and may return `int`, `float`, `str`, `Distrib`, `Distributions`, or `Sweep`. Use `@lift_sweeps` when you want a Python function to operate pointwise across sweep axes.

## Comments And Imports

- `// ...` starts a line comment and can also appear after code on the same line.
- `import "helpers.dice"` imports another dice file once.
- Relative imports are resolved from the file that contains the import.
- Absolute paths such as `import "/tmp/helpers.dice"` are supported.
- `std:...` imports such as `import "std:dnd/weapons.dice"` resolve inside dice's packaged standard library.

## Examples

```dice
hit(ac) = d20 >= ac; hit(11)
hit(ac) = d20 >= ac; damage(ac) = hit(ac) -> 5 | 0; damage([10:15])
hit(ac) = d20 >= ac; hit([AC:10:15])
crit(ac, dmg) = d20 == 20 -> dmg | 0; crit(15, 8)
import "std:dnd/weapons.dice"; crit_longsword(16, 7, 4)
always() = 5; always()
rolln(a, b) = a d b; rolln(2, 2)
match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0
repeat_sum(3, d2)
sumover("party", [party:1, 2, 3])
total([party:1, 2, 3])
render(d20)
add(1, 1)
greaterorequal(d20, 11)
rollhigh(3, 20, 1)
d20 >= 11 $ reselse(5, 0)
d20
2d6
d20 >= 11
[5:7]
[AC:5:7]
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
mass(d20[19:20])
~2d6
d20 >= 11 -> 5 | 0 $ mean
d20 $ sample
d2 $ var
d2 $ std
d-20
3d20h1
3d20l1
```

## Development Note

The examples above are executed by the test suite. If you change syntax or semantics, update the examples and the runtime together.
