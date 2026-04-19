# Python Extension Examples

These files are ordered as a short Python-extension tutorial.

Suggested order:

1. `00_import_python_library.dice`
2. `01_untyped_cellwise.py`
3. `02_typed_distribution.py`
4. `03_typed_sweep.py`
5. `04_weighted_measure.py`

The first example shows the most important user-facing workflow: write a Python helper library, import it from dice, and call the exported functions in a dice program.

Semantics note:

- `~expr` and `mean(expr)` are equivalent in the current language. Both return the expectation as a deterministic result.
- Deterministic values are represented internally as degenerate distributions, so plain scalars and probability-`1` scalar distributions are intended to be interchangeable in normal composition.
