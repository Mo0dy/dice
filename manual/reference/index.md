# Reference overview

This section explains the language surface in terms of the current implementation.

Main source boundaries:

- `diceparser.py`: syntax and grammar decisions
- `interpreter.py`: statement execution, function definitions, imports, and split dispatch
- `diceengine.py`: runtime values, arithmetic, reducers, indexing, and report state
- `viewer.py`: chart planning and rendering

The pages are grouped by the shape of the language:

- [Values And Types](values-and-types.md)
- [Core Expressions](core-expressions.md)
- [Functions And Imports](functions-and-imports.md)
- [Sweeps And Reducers](sweeps-and-reducers.md)
- [Split](split.md)
- [Reports](reports.md)
- [Python Integration](python-integration.md)
