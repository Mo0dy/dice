# Session Findings

- The language now supports a useful split between at-table evaluation and build analysis:
  - concrete damage distributions for one attack or spell
  - sweep-based expected-value views across AC or save bonuses
- Functions plus sweeps are already enough to model a small D&D sample library cleanly.
- Variable-driven dice syntax such as `a d b`, `d sides`, and `n d s h k` was necessary to make reusable D&D formulas practical.
- Save-for-half effects map nicely to `-> ... |/`, so spells like Fireball are a good fit for the current language.
- Advantage and disadvantage also fit naturally for comparison samples such as reckless attacks.
- Imports and line comments make the sample library much cleaner. Shared helpers now live well in `samples/dnd/lib/*.dice`.
- `match ... as ...` is enough to model crit branches cleanly when one d20 should drive miss, hit, and crit outcomes.
- `sum(n, expr)` cleanly covers repeated independent attacks or beams and works in both exact and direct execution models.
- The current language is already good at:
  - evaluating one attack, spell, or stat roll during play
  - sweeping AC or save bonuses to compare setups
- The main gaps surfaced by the D&D samples are:
  - function arguments are eager, so writing fully generic crit-aware helpers is still awkward
  - imported helpers all share one global namespace, so larger libraries may eventually want namespacing
