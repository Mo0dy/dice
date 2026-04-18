# dice

`dice` is a small language for tabletop dice and probability calculations.

This README is intentionally brief during the rewrite. For now, treat it as the user-facing reference for the currently tested language semantics.

## Values

- `FiniteMeasure`: a finite weighted support value such as `{10, 15}` or `{"fire" @ 2, "ice"}`
- `Distribution`: a normalized probability distribution such as `d20` or `d{10, 15}`
- `SweepValues`: a finite set of input values used to build bracket sweeps such as `[AC:10..20]`
- `Sweep[T]`: zero or more sweep axes whose cells hold values such as `Distribution` or `FiniteMeasure`
- `tuple`: an immutable structured value such as `()` or `(1, "fire")`
- `record`: an immutable keyed structured value such as `(PLAN: "gwm", LEVEL: 11)`
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
- `@` inside the else-branch names the already-evaluated `->` value.
- leading operators inside the else-branch are relative to that `@`, so `| / 2` means `| @ / 2`.
- `[a..b]` creates an unnamed sweep over an inclusive integer range.
- `[a..<b]` creates an unnamed sweep whose upper bound is excluded.
- `[a, b, c]` creates an unnamed sweep over explicit values.
- `[name:a..b]` creates a named sweep over an inclusive integer range.
- `[name:a..<b]` creates a named sweep whose upper bound is excluded.
- `[name:a, b, c]` creates a named sweep over explicit values.
- `()` creates an empty tuple.
- `(a,)` creates a one-element tuple.
- `(a, b, c)` creates a tuple.
- `(KEY: value, ...)` creates a record when each `KEY` is an identifier or integer.
- `f(x): expr` defines a top-level one-line function.
- `f(x):` followed by an indented body defines a multiline function with local assignments and one final expression line.
- `f(a, b=1)` defines defaults, and `f(b=2, a=1)` calls by keyword.
- Function defaults are evaluated against dice globals only.
- `f(a, b)` calls a user-defined function inside an expression.
- `split expr | guard -> expr | ...` binds one shared outcome of `expr`, checks clauses top-to-bottom, and sends only the still-unmatched cases to later clauses.
- `expr ^ n` evaluates `expr` independently `n` times and adds the results.
- `repeat_sum(n, expr)` evaluates `expr` independently `n` times and adds the results.
  `repeat_sum(n, expr)` remains supported as an explicit alias for `expr ^ n`.
- `expr[...]` indexes an existing sweep using coordinate entries such as `PLAN: 11`, filters such as `AC in {12, 16}`, and axis specs such as `"AC"`, `0`, or `("AC", "PLAN")`.
- `sumover(expr, axes?)`, `meanover(expr, axes?)`, `maxover(expr, axes?)`, and `argmaxover(expr, axes?)` reduce sweep axes without changing the meaning of plain distribution helpers such as `mean(expr)`.
- reducer `axes` may be omitted to reduce across all sweep axes, or passed as one axis ref or a tuple such as `"PLAN"`, `0`, or `("PLAN", "LEVEL")`.
- `argmaxover(...)` returns coordinate records such as `(PLAN: "gwm")` or `(PLAN: "gwm", LEVEL: 11)`, and those records can be fed back into `expr[...]`.
- `total(expr)` is shorthand for `sumover(...)` when `expr` has exactly one named sweep axis.
- `r_auto(expr, x="...", y="...")`, `r_dist(expr, x="...", y="...")`, `r_cdf(expr, x="...", y="...")`, and `r_surv(expr, x="...", y="...")` build chart specs.
- `r_compare(("Label", expr), ...)`, `r_diff(("A", expr), ("B", expr), ...)`, and `r_best(expr, ...)` build comparison and strategy chart specs.
- `r_title("...")`, `r_note("...")`, `r_hero(spec)`, and `r_row(spec1, spec2)` build the pending report.
- `render(path=..., format="png", dpi=...)` flushes the pending report to output and resets report state.
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
- tuple and record comparison operators are not supported yet.
- tuple and record field access is not supported yet.
- explicit keep-lists inside `expr[...]` can currently reorder the remaining axes, but they cannot drop still-unfixed axes yet.
- when positional axis refs are used in reducers or `expr[...]`, they refer to the current visible axis order at that point in the expression.

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

Use the `r_*` helpers plus `render(...)` in a program when you want graphs instead of text output.
CLI script execution uses deferred rendering by default: each `render(...)` call flushes one pending report, then `dice.py --file ...` waits for all open figures to close before exiting.

Example rendering program:

```bash
python3 dice.py --file path/to/plot.dice
```

```text
r_title("Hit chance"); r_auto((d20 >= [AC:10..20] -> 5 | 0) $ mean, x="AC"); render()
```

## Functions

User-defined functions use Python-like `:` headers.

- Parameters shadow globals.
- One-line definitions use `name(args): expr`.
- Multiline definitions use indentation, local assignments, and one final expression line.
- Function-local assignments never mutate globals.
- Rebinding a local name is allowed inside the function body.
- A local assignment that shadows a global emits a warning.
- Parameters may have defaults, and calls may use keyword arguments.
- Default expressions are evaluated against globals only.
- Functions may call other functions.
- Forward references work across a program.
- Recursion is not supported.

Examples:

```text
hit(ac): d20 >= ac
damage(ac): hit(ac) -> 5 | 0
crit(ac, dmg): d20 == 20 -> dmg | 0
paladin_smite(ac, bonus=8):
    hit_damage = 1 d 8 + 4
    attack_damage(ac, bonus, hit_damage, 2 d 8 + 4)
split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||
d6 ^ 3
(d6 + 1) ^ 3
d2 ^ 3
sumover([party:1, 2, 3], "party")
meanover(d2 + [bonus:0, 1], "bonus")
([PLAN:1, 2] + [AC:10, 11])["AC", "PLAN"]
total([party:1, 2, 3])
r_title("Hit chance"); r_auto((d20 >= [AC:10..20] -> 5 | 0) $ mean, x="AC"); render()
```

## Split

Use `split` when you want to roll once and make several decisions from that same roll.

Straightforward:

- `split expr as name` means “take one outcome from `expr` and call it `name`”.
- `split expr` binds the shared outcome to `@`.
- Clauses are checked from top to bottom.
- Later clauses only see cases that earlier clauses did not already take.
- `otherwise -> ...` catches whatever is left.
- `||` means “otherwise, return `0`”.

Example:

`split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||`

This is easiest to read as:

- if the roll is `20`, return `10`
- otherwise, if the roll is `10` through `19`, return `5`
- otherwise, return `0`

So the second clause is effectively “`@ + 5 >= 15`, but only for rolls that were not already matched by `@ == 20`”.

Exact:

- Evaluate `expr` once as a distribution and bind each possible outcome to `name`.
- For each bound outcome, evaluate the clauses in order.
- Each guard must be a Bernoulli result with outcomes only in `0` and `1`.
- A guarded clause takes the probability mass where its guard is `1`.
- The remaining probability mass, where the guard is `0`, continues to the next clause.
- `otherwise -> ...` takes all remaining mass.
- If the final fallback is omitted, `split` defaults the remaining mass to `0` and emits a warning.

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

## Creating Reports

The report surface is stateful.

- `r_*` chart helpers build chart specs.
- bare top-level chart specs append themselves to the current pending report in source order.
- layout helpers such as `r_title(...)` and `r_row(...)` mutate that pending report.
- `render(...)` flushes the current report to output and then resets report state.

This means one dice file can create multiple separate report images by calling `render(...)` more than once.

### Chart builders

- `r_auto(expr, x="...", y="...", title="...")` chooses a chart from the result shape.
- `r_dist(expr, x="...", y="...", title="...")` forces an exact distribution / PMF view.
- `r_cdf(expr, x="...", y="...", title="...")` forces a cumulative view.
- `r_surv(expr, x="...", y="...", title="...")` forces a survival view using `P(X > x)`.
- `r_compare(("Label", expr1), ("Other", expr2), x="...", y="...", title="...")` compares multiple labeled expressions.
- `r_diff(("A", expr1), ("B", expr2), x="...", y="...", title="...")` plots a two-series delta.
- `r_best(expr, title="...")` renders a winner map plus winner margin for suitable two-axis scalar sweeps.

### Report layout

- `r_title("...")` sets the report title. Only one title is allowed per report.
- `r_note("...")` appends note text at the bottom of the report.
- `r_hero(spec)` places one chart in the hero slot. Only one hero chart is allowed per report.
- `r_row(spec1, spec2)` places one explicit row with one or two charts.
- `r_wide(spec)` and `r_narrow(spec)` override the automatic width choice for auto-appended charts.

If you do not use `r_row(...)`, auto-appended charts are packed automatically:

- narrow charts are packed two-up
- wide charts take a full row

Axis labels usually come from named sweeps such as `[AC:10..20]`, but you can override them with `x="..."` and `y="..."`.

### Output and render settings

- `render(path=..., format="png", dpi=...)` writes the pending report and resets report state.
- `path` is optional. Without it, dice writes to a temporary PNG path in headless mode.
- `format` currently expects PNG output.
- `dpi` controls raster export density.
- `set_render_mode("blocking")`, `set_render_mode("nonblocking")`, and `set_render_mode("deferred")` control how figures are shown.
- `set_probability_mode("percent")` and `set_probability_mode("raw")` control probability-axis formatting.

Current quick-render planning covers:

- unswept distributions
- one-axis scalar sweeps
- one-axis distribution sweeps
- two-axis scalar heatmaps
- labeled scalar/distribution comparisons
- strategy winner/margin reports from suitable two-axis scalar sweeps

### Examples

Single-chart report:

```dice
r_title("d20"); r_auto(d20, x="Outcome"); render()
```

Comparison report with a hero chart and a full-width delta chart:

```dice
r_title("Hit chance"); r_hero(r_compare(("Normal", ~(d20 >= [AC:10..18])), ("Boosted", ~(d20 + 1 >= [AC:10..18])), x="Armor class", y="Hit chance")); r_wide(r_diff(("Boosted", ~(d20 + 1 >= [AC:10..18])), ("Normal", ~(d20 >= [AC:10..18])), x="Armor class", y="Extra hit chance")); render()
```

Explicit row layout with two distribution panels:

```dice
r_title("Distributions"); r_row(r_dist(d20, x="Outcome", title="d20"), r_cdf(d20, x="Outcome", title="CDF")); render()
```

Two separate reports in one program:

```dice
r_title("First"); r_auto(d20); render(); r_title("Second"); r_auto(d6); render()
```

## Python Integration

You can also keep a persistent dice session from Python:

```python
from dice import D, dice_interpreter, dicefunction
from diceengine import Distribution, FiniteMeasure, Sweep, greaterorequal, rollsingle

session = dice_interpreter()
result = session("d20 >= [AC:10..12] -> 5 | 0")
session.assign("cached", result)
session('r_title("Cached")')
session("r_auto(cached)")
session("render()")

@dicefunction
def add_two(value):
    return value + 2

session.register_function(add_two)

direct = greaterorequal(rollsingle(20), 11)
```

Pass `executor=...` to `dice_interpreter(...)` when you want a non-default backend. Decorate exported Python helpers with `@dicefunction`, then register them with `session.register_function(...)`.

- `@dicefunction` gives Python helpers dice lifting semantics in both direct Python calls and dice calls.
- Untyped parameters receive projected cell values, not whole sweeps.
- Parameters typed as `Distribution` or `FiniteMeasure` are auto-lifted cellwise.
- Parameters typed as `Sweep[...]` receive the full sweep container.
- Python host functions may use ordinary Python defaults and keyword arguments.
- `from dice import D` allows dice-expression defaults for Python functions, for example `def fireball(dc, save_bonus=D("default_save_bonus")): ...`.
- `D("...")` defaults are evaluated against dice globals only during dice-session calls, not function parameters or caller locals.
- Registered functions may return scalars, `FiniteMeasure`, `Distribution`, `Sweep[FiniteMeasure]`, or `Sweep[Distribution]`.

User-facing extension samples live under [samples/python_extensions](/home/felix/_Documents/Projects/dice/samples/python_extensions).

## Comments And Imports

- `# ...` starts a line comment and can also appear after code on the same line.
- `import "helpers"` imports another dice file once when the target is `helpers.dice`.
- `import "helpers.py"` executes a Python file once and registers functions marked with `@dicefunction`.
- Relative imports are resolved from the file that contains the import.
- Absolute paths such as `import "/tmp/helpers"` are supported.
- `std:...` imports such as `import "std:dnd/weapons"` resolve inside dice's packaged standard library.
- Python imports execute trusted local code and require the explicit `.py` suffix.

## Examples

```dice
hit(ac): d20 >= ac; hit(11)
hit(ac): d20 >= ac; damage(ac): hit(ac) -> 5 | 0; damage([10..15])
hit(ac): d20 >= ac; hit([AC:10..15])
crit(ac, dmg): d20 == 20 -> dmg | 0; crit(15, 8)
import "std:dnd/weapons"; longsword_attack(16, 7, 4)
always(): 5; always()
rolln(a, b): a d b; rolln(2, 2)
split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||
d6 ^ 3
(d6 + 1) ^ 3
d2 ^ 3
sumover([party:1, 2, 3], "party")
argmaxover([PLAN:1, 2] + [AC:10, 11], "PLAN")
total([party:1, 2, 3])
r_title("d20"); r_auto(d20); render()
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
d20 < 14 -> 2d10 | / 2
d20 < 14 -> 2d10 | // 2
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
