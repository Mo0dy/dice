# Docs

This folder keeps agent-facing project context out of the root `AGENTS.md`.

User-facing documentation is no longer centered here:

- `README.md` is the brief GitHub-facing introduction
- `manual/` is the canonical user-facing language manual and MkDocs source
- `docs/` remains internal project and agent documentation

Use these files in roughly this order:

1. [architecture.md](./architecture.md) for the module map and execution flow.
2. [language-runtime.md](./language-runtime.md) for the language model, data types, and examples.
3. [rewrite-status.md](./rewrite-status.md) for verified gaps between the legacy design and the current worktree.

Useful legacy references outside `docs/`:

- `README.md`: current brief user-facing semantics and quickstart
- `manual/`: canonical user-facing language manual and MkDocs source
- `notes.org`: design notes, grammar sketches, and implementation history
- `scripts/`: real sample programs that exercise macros, plotting, and RPG use cases
