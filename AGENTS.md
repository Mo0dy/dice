# AGENTS

## Project Snapshot

`dice` is a Python dice-probability language for tabletop RPG calculations. The durable core is the language pipeline:

`lexer.py` -> `diceparser.py` -> `syntaxtree.py` -> `interpreter.py` -> `diceengine.py`

Secondary surfaces:

- `dice.py`: CLI entry point
- `directdiceengine.py`: sampling-based reference backend and validation helpers
- `viewer.py`: Matplotlib plotting helper
- `README.md`: brief user-facing language reference during the rewrite
- `DICE_REWRITE_PLAN.md`: active rewrite design and implementation plan
- `scripts/`: sample dice programs
- `notes.org`: legacy design notes

## Repository Structure

- Top-level runtime modules: `dice.py`, `directdiceengine.py`, `lexer.py`, `diceparser.py`, `interpreter.py`, `diceengine.py`, `syntaxtree.py`, `viewer.py`
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
- Minimal first-class comments and file imports now belong to the active language surface: `// ...` and `import "path.dice"`.
- `README.md` examples are part of the executable contract through the test suite.
- The current ongoing task is the semantic rewrite described in `DICE_REWRITE_PLAN.md`.

## Where To Read Next

- `README.md`: current user-facing language semantics and executable examples
- `DICE_REWRITE_PLAN.md`: active rewrite target for unifying distributions and sweeps
- `docs/README.md`: documentation map
- `docs/architecture.md`: module responsibilities and execution flow
- `docs/language-runtime.md`: language model, data types, and sample program surfaces
- `docs/rewrite-status.md`: verified rewrite seams and practical cautions

## Working Notes For Agents

- Keep `README.md` brief during development. Its main job is to be the current user-facing reference for tested language semantics.
- Treat `DICE_REWRITE_PLAN.md` as the active design brief for ongoing semantic changes.
- During this rewrite, every semantic feature change should come with sensible end-to-end tests where practical.
- Do not recreate parallel user docs like the removed `documentation.org` / `documentation.html` unless the user explicitly asks for them.
- For syntax changes, update `lexer.py`, `diceparser.py`, and `interpreter.py` together.
- When adding standard-library builtins, define them in `diceengine.py` and register them through `executor.py` so dice and Python use the same callable surface.
- For import behavior, keep resolution relative to the importing file and prefer explicit runtime syntax over hidden preprocessing.
- For semantic changes, check `diceengine.py` first; most exact operator and callable behavior lives there.
- The old macro/preprocessor layer is historical only. If you need that behavior again, redesign it intentionally instead of assuming it still exists.
- Prefer `README.md` for current tested examples and `scripts/` / `notes.org` for older intent or design history.

## Tests

- Test framework: `unittest` with tests under `tests/`.
- First-line syntax coverage lives in `tests/test_readme_examples.py`, which extracts fenced `dice` blocks from `README.md` and executes them through `dice.py`.
- Runtime regressions live in `tests/test_runtime.py`.
- Focused math regression checks live in `tests/test_math_correctness.py`.
- Direct-backend smoke coverage lives in `tests/test_direct_engine.py`.
- Slow Monte Carlo validation lives in `tests/test_stochastic_validation.py` and does not need to be run constantly; use it after major semantic changes are completed.
- When adding language examples to `README.md`, keep them executable by the current runtime or update the runtime and tests in the same change.
- Run tests with `python3 -m unittest discover -s tests -v`.
- Run optional stochastic validation with `RUN_STOCHASTIC_VALIDATION=1 python3 -m unittest tests.test_stochastic_validation -v`.
