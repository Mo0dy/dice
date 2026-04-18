# dice language manual

This is the canonical user-facing language manual for `dice`.

Use `README.md` for the shortest possible GitHub-facing introduction. Use this manual when you want the fuller language model, exact semantics, and tested examples in one place.

The manual is written against the current implementation, not against an older design document. The main source files behind this manual are:

- `lexer.py` for tokens and basic surface syntax
- `diceparser.py` for grammar and parse rules
- `interpreter.py` for statement execution and imports
- `diceengine.py` for runtime values and exact semantics
- `viewer.py` for report planning and rendering

## How to read this manual

Each language page follows the same structure:

1. intention first
2. exact semantics second
3. executable examples last

That split is deliberate. The practical model should be easy to understand even when the exact probabilistic details are not what you need right now.

## Start here

- [Getting Started](getting-started.md) for the shortest path to useful tabletop calculations
- [Values And Types](reference/values-and-types.md) for what the language evaluates to
- [Core Expressions](reference/core-expressions.md) for dice, arithmetic, branching, and summaries
- [Sweeps And Reducers](reference/sweeps-and-reducers.md) for parameter studies
- [Split](reference/split.md) for shared-roll branching
- [Reports](reference/reports.md) for charts and exported report images
- [Python Integration](reference/python-integration.md) for extending the language from Python

## Example

```dice
d20 >= 15 -> 8 | 0
```

That means: roll a `d20`, deal `8` on success, otherwise deal `0`.

## Relationship to the docs site

`manual/` is the source directory for the MkDocs site configured in `mkdocs.yml`. The planned publish target is GitHub Pages.
