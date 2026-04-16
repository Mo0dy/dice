# dice

`dice` is a small language for tabletop dice and probability calculations.

This README is intentionally brief during the rewrite. For now, treat it as the user-facing reference for the currently tested language semantics.

## Values

- `FiniteMeasure`: a finite weighted support value such as `{10, 15}` or `{"fire" @ 2, "ice"}`
- `Distribution`: a normalized probability distribution such as `d20` or `d{10, 15}`
- `SweepValues`: a finite set of input values used to build bracket sweeps such as `[AC:10..20]`
- `Sweep[T]`: zero or more sweep axes whose cells hold values such as `Distribution` or `FiniteMeasure`
- numeric Bernoulli outcomes such as `0` and `1`

## Semantics

- `d20` rolls one die and returns a probability distribution.
- `2d6` rolls multiple dice and sums them.
- `{a, b, c}` creates a finite weighted measure with unit weights by default.
- `{value @ weight, ...}` creates a weighted measure with explicit relative weights.
- `d{...}` normalizes a finite measure into a distribution.
- `>=`, `<=`, `<`, `>`, `==` return Bernoulli distributions over `1` and `0`.
- `in` checks support membership against a finite measure or domain.
- `->` applies the `1` branch of a Bernoulli distribution to another distribution.
- `|` adds an else-branch to `->`.
- `|/` is shorthand for “else, use half damage”.
- `|//` is shorthand for “else, use half damage rounded down”.
- `[a..b]` creates an unnamed sweep over an inclusive integer range.
- `[a..<b]` creates an unnamed sweep whose upper bound is excluded.
- `[a, b, c]` creates an unnamed sweep over explicit values.
- `[name:a..b]` creates a named sweep over an inclusive integer range.
- `[name:a..<b]` creates a named sweep whose upper bound is excluded.
- `[name:a, b, c]` creates a named sweep over explicit values.
- `f(x) = expr` defines a top-level one-line function.
- `f(a, b)` calls a user-defined function inside an expression.
- `match expr as name | guard = expr | ... | otherwise = expr` binds one shared outcome of `expr`, checks clauses top-to-bottom, and sends only the still-unmatched cases to later clauses.
- `repeat_sum(n, expr)` evaluates `expr` independently `n` times and adds the results.
- `sumover("axis", expr)` adds results across one named sweep axis and preserves the others.
- `total(expr)` is shorthand for `sumover(...)` when `expr` has exactly one named sweep axis.
- `render(expr)` renders one result with smart defaults.
- `render(expr1, "label1", expr2, "label2")` compares multiple compatible results.
- `expr $ f` passes `expr` as the first argument to `f`.
- `expr $ f(a, b)` passes `expr` as the first argument to `f(expr, a, b)`.
- `import "path/to/file"` loads another dice file once. Relative paths resolve from the importing file, absolute paths resolve from the filesystem root, and `std:...` resolves from dice's packaged standard library. When the target is a `.dice` file, the extension is optional.
- `+`, `-`, `*`, `/`, and `//` combine numeric distributions.
- `d+20` and `d-20` mean advantage and disadvantage.
- `3d20h1` and `3d20l1` mean roll many dice and keep the highest or lowest subset.
- `!expr` samples one outcome and returns it as a degenerate distribution.
- `~expr` returns expectation as a degenerate distribution.
- `mean(expr)` and `sample(expr)` are explicit summary helpers.
- `var(expr)` and `std(expr)` return variance and standard deviation as degenerate distributions.
- `cum(expr)` returns the cumulative form of a numeric distribution using `P(X <= x)` at each outcome.
- `surv(expr)` returns the survival form of a numeric distribution using `P(X > x)` at each outcome.
- `type(expr)` returns the outer runtime shape as a string such as `Sweep[Distribution]`.
- `shape(expr)` returns the sweep axes as a string such as `[AC: (10, 11, 12)]`.
- operator-backed semantics are also available as functions such as `add(...)`, `roll(...)`, `greaterorequal(...)`, and `reselse(...)`.
- `( ... )` groups expressions.

## Running Dice

The CLI has three modes:

- REPL: `python3 dice.py --interactive`
- Direct one-off evaluation: `python3 dice.py "d20 >= 11 -> 5"`
- Run a dice program from a file: `python3 dice.py --file path/to/program.dice`

The `--file` mode parses a dice program, not Markdown or plain notes. Multi-line programs are separated by newlines or `;`.
Use `import "relative/path"` inside files when you want to share helpers across programs. Use `import "/absolute/path/to/file"` for explicit filesystem imports and `import "std:dnd/weapons"` for packaged helpers.

Useful flags:

- `-R N` or `--round N` rounds displayed numeric output. The CLI defaults to `-R 2`.
- Probabilities in default text output are shown as percentages.
- Rounded values that land exactly on an integer display without trailing decimal zeros.
- `--json` prints structured JSON objects for tool-facing integrations.
- `-v` prints the input together with the result

The interactive shell also supports a few lightweight host commands before parsing dice source:

- `$ set_round N` changes the REPL display rounding for later commands
- `$ set_render_mode MODE` sets render behavior for later plots. Use `blocking`, `nonblocking`, or `deferred`.
- `$ set_probability_mode MODE` sets probability display style for later output. Use `percent` or `raw`.
- `Ctrl-P` / `Ctrl-N` navigate command history on terminals with `readline` support
- `Tab` completes visible identifiers, function names, and import paths on terminals with `readline` support
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
- text-mode probabilities default to percentages; JSON probabilities default to raw probability mass

Examples:

```text
  0: 50%
  1: 50%
(E): 0.50
```

```text
/AC
10: 2.75
11: 2.50
12: 2.25
```

```text
/AC    10    11    12
  0   45%   50%   55%
  1   55%   50%   45%
(E)  0.55  0.50  0.45
```

```text
AC/BONUS   1   2
      10  11  12
      11  12  13
```

Use `render(...)` in a program when you want a graph instead of text output.
CLI script execution uses deferred rendering by default: each `render(...)` call opens a figure without blocking, then `dice.py --file ...` waits for all open figures to close before exiting.

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

## Match

Use `match` when you want to roll once and make several decisions from that same roll.

Straightforward:

- `match expr as name` means “take one outcome from `expr` and call it `name`”.
- Clauses are checked from top to bottom.
- Later clauses only see cases that earlier clauses did not already take.
- `otherwise` catches whatever is left.

Example:

`match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0`

This is easiest to read as:

- if the roll is `20`, return `10`
- otherwise, if the roll is `10` through `19`, return `5`
- otherwise, return `0`

So the second clause is effectively “`roll + 5 >= 15`, but only for rolls that were not already matched by `roll == 20`”.

Exact:

- Evaluate `expr` once as a distribution and bind each possible outcome to `name`.
- For each bound outcome, evaluate the clauses in order.
- Each guard must be a Bernoulli result with outcomes only in `0` and `1`.
- A guarded clause takes the probability mass where its guard is `1`.
- The remaining probability mass, where the guard is `0`, continues to the next clause.
- `otherwise` takes all remaining mass.
- If no clause covers some remaining mass, `match` raises an error instead of silently dropping cases.

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
- `render(expr, "axis label", "title")` renders one expression, overrides the x-axis label, and sets the figure title.
- `render(expr1, "a", expr2, "b")` compares multiple compatible results on one chart.
- `render(expr1, "a", expr2, "b", "axis label", "title")` compares multiple results, overrides the x-axis label, and sets the figure title.
- `set_render_mode("blocking")`, `set_render_mode("nonblocking")`, and `set_render_mode("deferred")` switch render behavior inside dice programs.
- `set_probability_mode("percent")` and `set_probability_mode("raw")` switch probability display style inside dice programs.
- Axis labels come from named sweeps like `[AC:10..20]`.
- Unnamed sweeps still render, but use fallback axis labels.
- Comparison renders align one-sweep results by their sweep values; matching names help with labels but are not required.
- render probability displays default to percentages.
- Supported quick-render shapes are:
  unswept distributions, one-sweep scalar results, one-sweep full distributions, and two-sweep scalar results.

## Python Integration

You can also keep a persistent dice session from Python:

```python
from dice import dice_interpreter
from diceengine import Distribution, FiniteMeasure, Sweep, greaterorequal, rollsingle

session = dice_interpreter()
result = session("d20 >= [AC:10:12] -> 5 | 0")
session.assign("cached", result)
session("render(cached)")

direct = greaterorequal(rollsingle(20), 11)
```

Pass `executor=...` to `dice_interpreter(...)` when you want a non-default backend. Register Python functions with `session.register_function(...)`.

- Untyped Python functions receive projected cell values, not whole sweeps.
- Parameters typed as `Distribution` or `FiniteMeasure` are auto-lifted cellwise.
- Parameters typed as `Sweep[...]` receive the full sweep container.
- Registered functions may return scalars, `FiniteMeasure`, `Distribution`, `Sweep[FiniteMeasure]`, or `Sweep[Distribution]`.

User-facing extension samples live under [samples/python_extensions](/home/felix/_Documents/Projects/dice/samples/python_extensions).

## Comments And Imports

- `# ...` starts a line comment and can also appear after code on the same line.
- `import "helpers"` imports another dice file once when the target is `helpers.dice`.
- Relative imports are resolved from the file that contains the import.
- Absolute paths such as `import "/tmp/helpers"` are supported.
- `std:...` imports such as `import "std:dnd/weapons"` resolve inside dice's packaged standard library.

## Examples

```dice
hit(ac) = d20 >= ac; hit(11)
hit(ac) = d20 >= ac; damage(ac) = hit(ac) -> 5 | 0; damage([10..15])
hit(ac) = d20 >= ac; hit([AC:10..15])
crit(ac, dmg) = d20 == 20 -> dmg | 0; crit(15, 8)
import "std:dnd/weapons"; crit_longsword(16, 7, 4)
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
[5..7]
[AC:5..7]
d20 == [5..7]
d20 >= [5,11]
d20 >= 11 -> 5
d20 >= 11 -> 2d6
d20 >= 11 -> 10 | 5
d20 < 14 -> 2d10 |/
d20 < 14 -> 2d10 |//
{10, 15}
d{10, 15}
d20 >= 19
d20 == 20
d20 in {1, 20}
1 + 1
3 / 2
3 // 2
d2 + d2
[1..2] + 1
d+20
d{d6, d8}
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
