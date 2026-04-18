# Python integration

## Intention

Python integration is how you extend `dice` without turning the language itself into a kitchen sink.

Use it when you want to:

- keep a persistent dice session from Python
- register trusted helper functions
- expose domain-specific helpers to dice code
- operate on distributions or sweeps directly from Python

## Exact semantics

The public Python-facing entry points live in `dice.py`, while function registration and lifting behavior are implemented through `interpreter.py`, `executor.py`, and `diceengine.py`.

Important rules:

- `dice_interpreter()` returns a persistent session
- `session("...")` evaluates dice code in that session
- `session.assign(name, value)` injects supported runtime values
- Python functions must be decorated with `@dicefunction` before registration
- `session.register_function(...)` exposes a decorated Python helper to dice code
- untyped parameters receive projected cell values
- parameters typed as `Distribution` or `FiniteMeasure` are auto-lifted cellwise
- parameters typed as `Sweep[...]` receive the whole sweep container
- `D("...")` allows dice-expression defaults for Python helpers, and those defaults are resolved against dice globals only during dice-session calls

## Examples

Minimal session use from Python:

```python
from dice import dice_interpreter

session = dice_interpreter()
result = session("d20 >= [AC:10..12] -> 5 | 0")
cached = session.assign("cached", result)
again = session("cached")
```

Registering a helper:

```python
from dice import dice_interpreter, dicefunction

session = dice_interpreter()

@dicefunction
def add_two(value):
    return value + 2

session.register_function(add_two)
result = session("add_two([1..3])")
```
