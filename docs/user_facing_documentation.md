# User-Facing Documentation

## Current Decisions

- The canonical user-facing language manual lives under `manual/`.
- The current internal `docs/` directory stays internal for now. We may consider renaming it later.
- The public docs site uses MkDocs.
- The user-facing example library lives under `examples/`.
- The example library is split into `00_basic/`, `01_dnd/`, and `02_python_extensions/`.
- `00_basic/` and `02_python_extensions/` are intentionally ordered by complexity and should read like short tutorials.
- `01_dnd/` holds the larger D&D example corpus without forcing a tutorial ordering.
- Language pages should be written in this order:
  1. intention first
  2. precise semantics second
  3. examples after that
- The intention section should be readable for people who just want to use the language.
- The precise section may be denser and may be skipped by readers who only need the practical model.
- Examples should be understandable on their own, even when they range from basic to advanced.
- Ask for a few structure and style decisions early when changing the public docs substantially, so the documentation matches the user's preferences before the content is expanded too far.

## Repository Split

- `README.md` remains the GitHub-first quickstart and brief user-facing reference.
- `manual/` is the canonical user-facing language manual and the source for the MkDocs site.
- `examples/` is the canonical user-facing example library.
- `docs/` is internal project and agent documentation.

## Serving Plan

- The MkDocs configuration lives at the repository root in `mkdocs.yml`.
- The docs source directory for the site is `manual/`.
- The intended publish target is GitHub Pages once deployment is wired.
- `dice-web` should consume or link to the canonical manual rather than maintain a second copy.

## Testing Rule

- Fenced `dice` examples in `README.md` are part of the executable contract.
- Fenced `dice` examples in `manual/` must also execute in tests.
- When Python examples are added to the manual, prefer keeping them short and executable as well.
