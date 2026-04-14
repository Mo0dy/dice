# Architecture

## Purpose

The repository implements a small domain-specific language for dice and probability calculations, mainly for tabletop RPG analysis.

## Main Components

- `lexer.py`
  Converts source text into tokens. It recognizes arithmetic operators, dice operators, comparison operators, indexing, rendering syntax, identifiers, and strings.
- `diceparser.py`
  Builds an AST from lexer tokens using hand-written recursive descent parsing.
- `syntaxtree.py`
  Defines the AST node types used by the parser and interpreter.
- `interpreter.py`
  Walks the AST and dispatches actual semantics to `Diceengine` or `viewer`.
- `diceengine.py`
  Holds the core math and type behavior: distributions, sweeps, branching, indexing, and arithmetic.
- `viewer.py`
  Provides Matplotlib-backed rendering over runtime `Distributions`, including smart defaults for bars, lines, heatmaps, and simple comparisons.

## Execution Flow

### Expression path

1. Source text is tokenized by `Lexer`.
2. `DiceParser` turns tokens into AST nodes from `syntaxtree.py`.
3. `Interpreter` evaluates the AST.
4. Operator semantics are delegated to `Diceengine`.
5. Render statements call into `viewer.py`.

### Entry points

- `dice.py`
  Intended CLI for interactive, single-command, and file execution.
- `viewer.py`
  Provides the direct runtime rendering backend used by the interpreter and CLI.

## Core Data Types

- `int`
  Plain scalar values.
- `Distrib`
  Probability distribution of outcome -> probability.
- `Distributions`
  Sweep-aware collection of one or more `Distrib` values.
- `Sweep`
  Finite input axis used to evaluate an expression over multiple values.

## Change Boundaries

- Syntax work usually spans `lexer.py`, `diceparser.py`, and `interpreter.py`.
- Semantic/operator work is centered in `diceengine.py`.
- AST shape changes belong in `syntaxtree.py` and then ripple into parser/interpreter.
- Rendering changes usually stay in `viewer.py`, unless new language syntax is added.
