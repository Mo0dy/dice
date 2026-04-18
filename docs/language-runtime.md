# Language And Runtime

## What The Language Models

The language is built around tabletop dice math:

- rolling dice distributions such as `d20` or `2d6`
- comparisons such as `d20 >= 15`
- branching weighted outcome distributions such as `d20 >= 15 -> 2d6 + 3 | 0`
- sweep-driven calculations such as `[14..20]`
- advantage/disadvantage and pick-high/pick-low forms
- optional plotting commands for graph output

## Language Surfaces In The Repository

- `README.md`
  Current brief user-facing quickstart and tested short reference.
- `manual/`
  Canonical user-facing language manual and MkDocs source.
- `examples/`
  Canonical user-facing example library, split into basic language, D&D, and Python-extension examples.
- `scripts/*.txt`
  Small practical programs using defines, plotting directives, and combat math.
- `scripts/dnd.org`
  A more narrative example around DnD use cases.
- `test.dice`
  Scratch file; currently incomplete and not a reliable executable test.

## Runtime Layers

### Parsing and AST

`diceparser.py` implements a hand-written recursive descent parser over the token stream from `lexer.py`.

AST node families in `syntaxtree.py`:

- `Val` for leaves
- `UnOp` for unary operators
- `BinOp` for binary operators
- `TenOp` for ternary forms
- `VarOp` for variadic constructs such as list literals or multi-statement programs

### Evaluation

`interpreter.py` uses a visitor pattern. It keeps a `global_scope` for assigned identifiers and dispatches nearly all math to an `Executor`, which defaults to the exact backend.

### Semantics

`diceengine.py` is the semantic center of the project. Important behaviors include:

- probability distribution generation
- sweep-aware lifting over multiple evaluation points
- distribution arithmetic
- comparison operators returning Bernoulli `0` / `1` distributions
- branching and summary operators over distributions
- indexing/selecting subsets of distributions
- advantage/disadvantage and high/low roll helpers

## Legacy Preprocessor Layer

The legacy runtime used to have a `Preprocessor` that handled:

- line comments beginning with `#`
- macro-style definitions beginning with `!define`
- multiline script preprocessing before parsing

That implementation still exists in git history (`git show HEAD:preprocessor.py`), but it is no longer part of the active runtime.

## Rendering Layer

Rendering is now centered on stateful `r_*` spec builders. Pending charts auto-render at the end of a top-level program by default, and `render(...)` remains the explicit flush/export step when you want to control timing or write multiple reports.

`viewer.py` renders runtime `Distributions` directly and chooses a chart shape from the result structure instead of parsing textual dict output.

## Documentation Serving

User-facing documentation is served from the MkDocs source under `manual/`, not from this internal `docs/` directory.

- `mkdocs.yml` defines the public docs site structure
- `manual/` holds the source pages
- the intended publish target is GitHub Pages
- `docs/` remains internal and explanatory for contributors and agents
