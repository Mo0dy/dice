# D&D Sample Library

Executable sample programs for stressing the current dice language with D&D-like use cases.

- `at_table/`: concrete actions you might evaluate during play
- `analysis/`: sweep-based setup comparisons and expected-value views
- `lib/`: reusable helper libraries imported by the sample programs

The mechanics are intentionally approximate. Their main purpose is to exercise the language surface and reveal modeling gaps.

The samples now intentionally exercise:

- `import "..."` for reusable combat helpers
- `// ...` comments inside `.dice` files
- `match ... as ...` for shared-roll crit logic
- `sum(n, expr)` for repeated independent attacks or beams
- sweep-based build analysis across AC, save bonuses, or dart counts
