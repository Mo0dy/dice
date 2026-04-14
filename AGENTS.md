# AGENTS

## Project Snapshot

`dice` is a Python dice-probability language for tabletop RPG calculations. The durable core is the language pipeline:

`lexer.py` -> `diceparser.py` -> `syntaxtree.py` -> `interpreter.py` -> `diceengine.py`

Secondary surfaces:

- `dice.py`: CLI entry point
- `viewer.py`: Matplotlib plotting helper
- `README.md`: brief user-facing language reference during the rewrite
- `scripts/`: sample dice programs
- `notes.org`: legacy design notes

## Repository Structure

- Top-level runtime modules: `dice.py`, `lexer.py`, `diceparser.py`, `interpreter.py`, `diceengine.py`, `syntaxtree.py`, `viewer.py`
- User-facing docs: `README.md`
- Examples and sample programs: `test.dice`, `scripts/*.txt`, `scripts/*.org`
- Agent-facing docs: `docs/`
- Tests: `tests/`
- Historical design notes: `notes.org`
- Images for old notes/docs: `images/`

## Current State

The active runtime is now the parser/interpreter/engine stack plus the CLI in `dice.py`.

- Programs are parsed as EOF-delimited statement sequences rather than `BEGIN ... END` wrappers.
- The legacy preprocessor and Discord bot have been removed from the active surface.
- `README.md` examples are part of the executable contract through the test suite.

## Where To Read Next

- `README.md`: current user-facing language semantics and executable examples
- `docs/README.md`: documentation map
- `docs/architecture.md`: module responsibilities and execution flow
- `docs/language-runtime.md`: language model, data types, and sample program surfaces
- `docs/rewrite-status.md`: verified rewrite seams and practical cautions

## Working Notes For Agents

- Keep `README.md` brief during development. Its main job is to be the current user-facing reference for tested language semantics.
- Do not recreate parallel user docs like the removed `documentation.org` / `documentation.html` unless the user explicitly asks for them.
- For syntax changes, update `lexer.py`, `diceparser.py`, and `interpreter.py` together.
- For semantic changes, check `diceengine.py` first; most operator behavior lives there.
- The old macro/preprocessor layer is historical only. If you need that behavior again, redesign it intentionally instead of assuming it still exists.
- Prefer `README.md` for current tested examples and `scripts/` / `notes.org` for older intent or design history.

## Tests

- Test framework: `unittest` with tests under `tests/`.
- First-line syntax coverage lives in `tests/test_readme_examples.py`, which extracts fenced `dice` blocks from `README.md` and executes them through `dice.py`.
- Runtime regressions live in `tests/test_runtime.py`.
- When adding language examples to `README.md`, keep them executable by the current runtime or update the runtime and tests in the same change.
- Run tests with `python3 -m unittest discover -s tests -v`.
