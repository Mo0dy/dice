# Troll Comparison Notes

This is an initial working comparison between our dice DSL and Troll, focused on the D&D helper surface in `stdlib/dnd`.

## Local Setup

- The Troll port is test-only and lives under `tests/troll/`.
- Setup instructions live in [tests/troll/README.md](/home/felix/_Documents/Projects/dice/tests/troll/README.md:1).
- Weapon helpers live in `tests/troll/dnd/weapons.t`.
- Spell helpers live in `tests/troll/dnd/spells.t`.

Example commands:

```bash
./tests/troll/run_troll.sh 0 tests/troll/dnd/weapons.t MODE=6 AC=16 BONUS=7 MOD=4 EXTRA=0 ATTACKS=0
./tests/troll/run_troll.sh 0 tests/troll/dnd/spells.t MODE=5 AC=0 BONUS=0 STAT=0 COUNT=0 DC=15 SAVEBONUS=2
```

## Main Language Differences

- Our DSL has Bernoulli `0` / `1` comparison results and branching operators like `->`, `|`, `|/`, and `|//`.
- Troll does not have boolean values. It uses empty vs non-empty collections as truthiness.
- Our DSL has imports and a standard-library surface such as `import "std:dnd/weapons.dice"`.
- Troll has functions, but no comparable module/import mechanism in the language, so shared helpers are duplicated across files.
- Our DSL has named sweeps like `[AC:10:20]` and sweep-aware evaluation.
- Troll has no direct equivalent to named parameter sweeps; batch comparison is usually driven outside the language.
- Our DSL distinguishes exact distributions from summary operators such as `~expr`.
- Troll prints distributions directly and reports summary statistics such as average and spread in the CLI.

## D&D Library Porting Notes

- `damage_on_hit(...)` ports naturally to Troll using `if hit then dmg else 0`.
- `crit_hit(...)` also ports well, but needs an explicit local binding so one `d20` roll is reused across the crit and hit branches.
- `repeat_sum(n, expr)` maps cleanly to `sum (n # expr)`.
- Attack-roll helpers like advantage are straightforward because Troll has strong collection operators like `max`, `largest`, and `count`.
- `save_half(...)` now maps cleanly: the D&D helper uses `|//` on our side, and Troll's integer arithmetic already rounds `dmg / 2` down.

## Verified Ports

These examples currently match between our DSL and the Troll implementation to the displayed precision:

- `crit_longsword(16, 7, 4)`:
  our DSL `5.32`, Troll `5.325`
- `paladin_smite(17, 8, 4, 3)`:
  our DSL `14.10`, Troll `14.1`
- `fireball(15, 2)`:
  our DSL `22.30`, Troll `22.3`
- `magic_missile(3)`:
  our DSL `10.50`, Troll `10.5`

For an AC sweep, our DSL can express the whole study in one program:

```text
import "std:dnd/weapons.dice"; ~crit_longsword([AC:10, 12, 14, 16, 18, 20], 7, 4)
```

which yields:

```text
/AC
10: 7.88
12: 7.02
14: 6.17
16: 5.32
18: 4.47
20: 3.62
```

The Troll version produces the same numbers, but only by driving multiple runs from the shell, one `AC=...` value at a time.

## Full Distribution Checks

We now also have an executable comparison in [tests/test_troll_comparison.py](/home/felix/_Documents/Projects/dice/tests/test_troll_comparison.py:1).

That comparison now covers the dedicated D&D regression manifest in [tests/dnd_cases.py](/home/felix/_Documents/Projects/dice/tests/dnd_cases.py:1).

The test handles three shapes:

- full unswept distributions, for example attack and damage distributions
- one-axis scalar sweeps, by comparing our deterministic `~...` sweep result against repeated Troll average calculations
- final scalar results such as `fireball_party_total.dice`

We also added missing sample coverage for:

- `inflict_wounds`
- `sacred_flame`

Those checks currently pass. The comparison uses a tiny floating tolerance because Troll prints decimal probabilities rather than exposing an exact machine-readable format, but the observed differences are only from decimal rendering, not from semantic mismatches.

## Takeaways So Far

- Troll is stronger than our current DSL at unordered dice-pool algebra.
- Our DSL is much stronger at parameterized analysis, reusable file structure, and user-facing standard-library organization.
- Translating top-level D&D helpers is feasible, but Troll wants "one runnable program per scenario" more than "one importable library shared across scenarios".
