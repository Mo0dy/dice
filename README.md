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
- `f(x) = expr` defines a top-level one-line function.
- `f(a, b)` calls a user-defined function inside an expression.
- `match expr as name | guard = expr | ... | otherwise = expr` reuses one shared value across guarded branches.
- `import "path/to/file.dice"` loads another dice file once, relative to the current file.
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
Use `import "relative/path.dice"` inside files when you want to share helpers across programs.

Useful flags:

- `-r N` rounds numeric output, for example `python3 dice.py -r 2 execute "d20 >= 11"`
- `-g` prints a grep-friendly single-line result
- `-v` prints the input together with the result
- `-p` shows the result with `viewer.do(...)` after `execute`
- `--direct` uses the direct sampling backend instead of the exact probability engine
- `--seed N` sets the RNG seed for `--direct`

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
- Direct sampled execution:
  `python3 dice.py --direct --seed 123 execute "4d6h3"` executes one sampled run through the same language semantics.
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

## Comments And Imports

- `// ...` starts a line comment and can also appear after code on the same line.
- `import "helpers.dice"` imports another dice file once.
- Imports are resolved relative to the file that contains the import.
- Imports are meant for reusable helpers and sample libraries, not for reviving the old macro/preprocessor layer.

## Examples

```dice
hit(ac) = d20 >= ac; hit(11)
hit(ac) = d20 >= ac; damage(ac) = hit(ac) -> 5 | 0; damage([10:15])
crit(ac, dmg) = d20 == 20 -> dmg | 0; crit(15, 8)
always() = 5; always()
rolln(a, b) = a d b; rolln(2, 2)
match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0
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
