# Rewrite Status

## Current Rewrite Outcome

These notes describe the repository after the current rewrite cleanup on 2026-04-14.

### Runtime shape

- `diceparser.py` now parses EOF-delimited statement sequences instead of `BEGIN ... END` wrappers.
- `interpreter.py` executes either a single statement or a semicolon/newline separated program.
- `dice.py` is the only active top-level runtime surface.

### Removed surfaces

- The Discord bot has been removed.
- The legacy preprocessor is no longer part of the active runtime.
- Old user-facing docs were replaced by the brief `README.md`.

### Remaining historical material

- `notes.org` and `scripts/` still reflect the older macro-heavy workflow.
- Sample scripts that depend on `!define`, `#`, or viewer comment directives are historical references unless they are explicitly brought back into the runtime.

## What Still Looks Stable

- `diceengine.py` is the most self-contained and coherent part of the codebase.
- `syntaxtree.py` is small and stable.
- `README.md`, `notes.org`, and `scripts/` still provide useful intent even when the runtime is in flux.

## Suggested Agent Strategy

1. Treat `README.md` and `tests/` as the current contract.
2. Keep syntax/parser/interpreter changes coordinated.
3. Treat macro/preprocessor behavior as a new feature if reintroduced, not as something half-supported.
4. Use `scripts/` and `notes.org` for intent, not as guaranteed executable inputs.

## Quick Verification Commands

These commands are useful when resuming work:

```bash
python3 -m py_compile dice.py diceengine.py diceparser.py interpreter.py lexer.py syntaxtree.py viewer.py
python3 -m unittest discover -s tests -v
python3 dice.py execute "d20 >= 11"
```
