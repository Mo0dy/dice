# Functions and imports

## Intention

Functions let you name repeated logic once and reuse it across calculations.

Imports let you split helpers across files and reuse packaged standard-library code such as the DnD helpers in `stdlib/`.

Together, these are the main tools for moving from one-off expressions to reusable analysis programs.

## Exact semantics

Function parsing and statement structure live in `diceparser.py`. Function registration, scope handling, dice-file imports, and Python-file imports live in `interpreter.py`.

Important rules:

- `f(x): expr` defines a one-line top-level function.
- An indented body defines a multiline function with local assignments and one final expression line.
- Parameters may have defaults.
- Calls may use keywords.
- Default expressions are evaluated against dice globals only.
- Parameters shadow globals inside the function body.
- Function-local assignments do not mutate globals.
- Forward references across a program work.
- Recursion is not supported.
- `# ...` starts a line comment and also works after code on the same line.
- `import "helpers"` loads `helpers.dice` once.
- `import "helpers.py"` executes a trusted Python file once and registers `@dicefunction` exports.
- Relative imports resolve from the importing file.
- `import "std:..."` resolves under the packaged standard library.

> Pitfall: Python imports are explicit and trusted. They are not a hidden preprocessor step.

## Examples

One-line functions:

```dice
hit(ac, bonus=7): d20 + bonus >= ac
damage(ac, bonus=7): hit(ac, bonus=bonus) -> 1 d 8 + 4 | 0
damage(15)
```

Multiline function:

```dice
paladin_smite(ac, bonus=8):
    hit_damage = 1 d 8 + 4
    crit_damage = 2 d 8 + 4 + ((d8 ^ 2) ^ 2)
    split d20 as roll | roll == 20 -> crit_damage | roll + bonus >= ac -> hit_damage ||
paladin_smite(17)
```

Keyword arguments:

```dice
hit(ac, bonus=7): d20 + bonus >= ac
hit(ac=15, bonus=9)
```

Comments:

```dice
hit(ac, bonus=7): d20 + bonus >= ac # attack roll
hit(15)
```

Packaged stdlib import:

```dice
import "std:dnd/weapons"
longsword_attack(16, 7, 4)
```
