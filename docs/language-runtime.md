# Language And Runtime

## What The Language Models

The language is built around tabletop dice math:

- rolling dice distributions such as `d20` or `2d6`
- comparisons such as `d20 >= 15`
- resolving hit chance into average damage such as `d20 >= 15 -> 2d6 + 3`
- list/range driven calculations such as `[14:20]`
- advantage/disadvantage and pick-high/pick-low forms
- optional plotting commands for graph output

## Language Surfaces In The Repository

- `README.md`
  Current brief user-facing reference for tested language semantics.
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

`interpreter.py` uses a visitor pattern. It keeps a `global_scope` for assigned identifiers and dispatches nearly all math to `Diceengine`.

### Semantics

`diceengine.py` is the semantic center of the project. Important behaviors include:

- probability distribution generation
- distribution arithmetic
- comparison operators returning `ResultList`
- resolving `ResultList` against damage distributions
- indexing/selecting subsets of distributions
- advantage/disadvantage and high/low roll helpers

## Legacy Preprocessor Layer

The legacy runtime used to have a `Preprocessor` that handled:

- line comments beginning with `//`
- macro-style definitions beginning with `!define`
- multiline script preprocessing before parsing

That implementation still exists in git history (`git show HEAD:preprocessor.py`), but it is no longer part of the active runtime.

## Plotting Layer

Plotting is split across language intrinsics and plain-text directives:

- intrinsic commands parsed in the language: `plot`, `label`, `xlabel`, `ylabel`, `show`
- viewer-side comment directives in sample scripts: `#label`, `#xlabel`, `#ylabel`, `#title`, `#grid`

Future edits should decide whether plotting remains a textual post-processing layer, a first-class language feature, or both.
