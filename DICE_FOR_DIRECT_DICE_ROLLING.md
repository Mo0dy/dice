# Dice For Direct Dice Rolling

This note collects examples that are easy to express as distributions, but become tricky when we want one concrete roll at the table together with a useful roll log.

The recurring themes are:

- sometimes we want the final total and the individual dice that produced it
- sometimes we need to read the same sampled die more than once
- sometimes we need to distinguish "reuse this exact rolled value" from "roll this expression again"
- eager function arguments are fine for exact distributions, but can be surprising in direct mode

## 1. Plain damage roll hides the component dice

```dice
2d6 + 3
```

For simulation, the total is enough. For rolling at the table, the player usually wants to see something like `5 + 2 + 3 = 10`, not just the final sampled total.

## 2. Keep-high / drop-low needs provenance

```dice
4d6h3
```

This is a good total distribution, but a direct roll usually needs to show all four dice and which one was dropped. A sampled total like `14` is not enough to explain whether it came from `6, 5, 3, 1` or `4, 4, 4, 2`.

## 3. Advantage needs both d20s, not only the kept value

```dice
d+20 + 7 >= 16 -> 1 d 8 + 4 | 0
```

For exact math this is fine, but for live rolling the player usually wants to see both attack dice and which one won. Sampling only the final hit result or only the kept d20 loses the table-facing story of the roll.

## 4. Extra dice on the attack roll should stay visible

```dice
d20 + d4 + 7 >= 16 -> 1 d 8 + 4 | 0
```

This is the Bless-style case. The player usually wants to see the raw d20, the bonus d4, and how they combined, especially on near misses where the extra die matters.

## 5. Shared attack-roll logic already needs one stable sampled die

```dice
match d20 as roll | roll == 20 = 2 d 8 + 4 | roll + 7 >= 16 = 1 d 8 + 4 | otherwise = 0
```

This is the classic crit / hit / miss pattern. `match` helps because `roll` names one shared d20 sample, but a direct backend still needs that sampled roll to stay stable across multiple reads and still remember that it came from a visible d20 roll.

## 6. Generic crit helpers run into eager function arguments

```dice
attack(ac, bonus, dmg) = match d20 as roll | roll == 20 = dmg + dmg | roll + bonus >= ac = dmg | otherwise = 0
attack(16, 7, 1 d 8 + 4)
```

**This looks like a reusable helper, but in direct mode it is dangerous because function arguments are eager. `dmg` may get sampled before we even know whether we hit, and the crit branch can accidentally mean "use the same sampled damage twice" instead of "roll the damage dice twice".**

## 7. Per-die rerolls need access to the roll tree, not just the sum

```dice
2 d 6 + 4
```

This is a stand-in for Great Weapon Fighting and similar mechanics. If one die shows `1` or `2`, the rule cares about that specific die, so a direct representation needs something like `[1, 6]` with a reroll history, not just the sampled total `11`.

## 8. Rerolling a natural 1 cares about the raw die, not the final outcome

```dice
d20 + 7 >= 16 -> 1 d 8 + 4 | 0
```

This is the Halfling Lucky style problem. The rule triggers from the unmodified d20 result, so a direct backend needs to preserve the raw die and possibly replace it with a second d20 roll before the rest of the expression keeps going.

## 9. Some effects want one damage roll shared across multiple targets

```dice
save_half(dc, bonus, dmg) = d20 + bonus < dc -> dmg |/
save_half(15, 2, 8 d 6) + save_half(15, 5, 8 d 6)
```

For exact distributions, independent calls are fine. At the table, though, many effects want one shared `8d6` damage roll applied to several different save results, so direct rolling needs a way to say "roll this once, reuse it there and there" rather than sampling each call independently.

## 10. Repeated independent attacks need a structured log, not only a final total

```dice
sum(3, d20 + 7 >= 16 -> 1 d 10 + 4 | 0)
```

This is fine as an aggregate damage distribution, but at the table the player usually wants three separate beam or attack results. Direct rolling should probably preserve something like "beam 1 miss, beam 2 hit for 9, beam 3 crit for 15" instead of collapsing everything immediately into one number.

## 11. Natural-roll side effects reuse the same die in more than one way

```dice
match d20 as roll | roll == 1 = 2 | roll == 20 = -1 | roll >= 10 = 0 | otherwise = 1
```

This is a death-save style example. One d20 sample controls natural-1 logic, natural-20 logic, and the usual threshold check, so direct rolling needs stable shared access to one die result plus a clear way to report which branch fired.

## 12. Host functions also lose information if they only receive final sampled values

```dice
damage_twice(dmg) = dmg + dmg
damage_twice(1 d 8)
```

Even this tiny helper is ambiguous in direct mode. If `dmg` is already a sampled scalar-like object, then `dmg + dmg` reuses one roll; if we wanted two fresh damage rolls, the current function surface does not express that difference clearly.

## Online Research Notes For Items 6-12

I only researched the harder cases from item 6 onward. The simpler visibility cases from 1-5 look much more like UI / presentation work than language-design blockers.

### 6. Generic crit helpers and eager arguments

- [Foundry VTT's `Roll` API](https://foundryvtt.com/api/classes/foundry.dice.Roll.html) keeps a parsed roll object with `terms`, `dice`, `result`, and `total`, and says that once evaluated the roll is immutable. It also exposes `clone()` to get a fresh unevaluated copy.
- [AnyDice functions](https://anydice.com/docs/functions/) avoid flattening everything to one scalar type. Functions can declare parameters as number, die, or sequence, and the engine changes evaluation behavior based on that type.

Takeaway: similar projects usually separate "formula / roll plan" from "evaluated roll result". That gives them a clean way to distinguish "reuse this evaluated roll" from "evaluate the same expression again".

### 7. Per-die rerolls

- [Foundry's `Die` term](https://foundryvtt.com/api/v14/classes/foundry.dice.terms.Die.html) has explicit reroll support, and [its `DiceTermResult` structure](https://foundryvtt.com/api/interfaces/foundry.dice.DiceTermResult.html) tracks flags like `discarded`, `rerolled`, and `exploded` per die result.
- [RPG Dice Roller's `RollResult`](https://dice-roller.github.io/documentation/api/results/RollResult.html) stores `initialValue`, `value`, `calculationValue`, modifier names, and whether that die still counts toward the total.
- [AnyDice introspection](https://anydice.com/docs/introspection/) and [sequence-typed functions](https://anydice.com/docs/functions/) let code inspect individual dice positions instead of only the summed result.

Takeaway: the common solution is to keep a per-die result record, not just a final distribution or sampled sum.

### 8. Rerolling a natural 1

- [Foundry's roll results](https://foundryvtt.com/api/interfaces/foundry.dice.DiceTermResult.html) keep the raw die result as a first-class field, separate from whether that result is active or rerolled.
- [Retroactive Advantage for DnD5e](https://foundryvtt.com/packages/retroactive-advantage-5e) works by reusing relevant d20 results from an existing chat card rather than recomputing only from a final total.
- [Advantage Reminder for dnd5e](https://foundryvtt.com/packages/adv-reminder/) explicitly surfaces critical and advantage sources in the roll workflow instead of treating them as invisible arithmetic.

Takeaway: tools that support nat-1 / nat-20 style rules usually treat the raw d20 as a special object in the roll history, not as a number that disappears into a later comparison.

### 9. One damage roll shared across multiple targets

- [Foundry dnd5e attack activities](https://github-wiki-see.page/m/foundryvtt/dnd5e/wiki/Activity-Type-Attack) use an attack card with separate Attack and Damage buttons, so related rolls live in one workflow object instead of being flattened immediately.
- [Damage Application](https://foundryvtt.com/packages/damage-application) applies one already-rolled damage result to selected tokens, which is exactly the "roll once, consume many times" pattern.
- [Foundry dnd5e hooks](https://github-wiki-see.page/m/foundryvtt/dnd5e/wiki/Hooks) expose roll and damage-application stages separately, which reinforces the same workflow split.

Takeaway: similar projects often solve this above the formula language by introducing a persistent roll workflow object that can be applied to many targets after it is rolled.

### 10. Repeated independent attacks with a useful log

- [RPG Dice Roller group rolls](https://dice-roller.github.io/documentation/guide/notation/group-rolls.html) preserve sub-roll expressions and show each sub-roll before summing them.
- [Ready Set Roll for D&D5e](https://foundryvtt.com/packages/ready-set-roll-5e/) advertises compounded chat cards that keep attack, damage, save, and other related rolls visible as separate parts of one action.

Takeaway: repeated rolls are usually modeled as a list of child rolls plus an aggregate, not as one total with the intermediate history thrown away.

### 11. Natural-roll side effects

- [Dramatic Rolls](https://foundryvtt.com/packages/dramatic-rolls/) triggers effects from natural 20s and natural 1s.
- [Advantage Reminder for dnd5e](https://foundryvtt.com/packages/adv-reminder/) says it can show when the preceding attack was a natural 20 and treat that as a critical source.
- [Pathfinder 1e for Foundry's `D20RollConstructorOptions`](https://foundryvtt-pathfinder1-053b2a.gitlab.io/interfaces/pf1._types_.D20RollConstructorOptions.html) includes explicit `critical` and `staticRoll` fields, which is another example of keeping d20-test metadata separate from the final total.

Takeaway: systems that care about natural-roll side effects tend to represent "a d20 test" as a richer domain object with metadata, not just an integer plus modifiers.

### 12. Host functions losing provenance

- [Foundry `Roll` objects](https://foundryvtt.com/api/classes/foundry.dice.Roll.html) and [dice-term results](https://foundryvtt.com/api/interfaces/foundry.dice.DiceTermResult.html) pass around structured roll data instead of only scalar totals.
- [RPG Dice Roller's `RollResult`](https://dice-roller.github.io/documentation/api/results/RollResult.html) similarly preserves raw value, modified value, calculation value, and modifier flags.
- [AnyDice parameter typing](https://anydice.com/docs/functions/) distinguishes numbers, dice, and sequences, which is a language-level way to preserve intent instead of erasing it before user code runs.

Takeaway: similar projects usually solve this by making roll objects first-class. A plain "scalar that happens to have come from dice" is usually not rich enough once users want rerolls, crit logic, or roll explanations.

## Current Direction Suggested By The Research

The strongest pattern across these projects is:

- keep an unevaluated roll expression separate from an evaluated direct roll result
- make the evaluated result rich enough to remember child dice, kept / dropped status, rerolls, and display text
- provide an explicit way to reuse one evaluated roll versus re-evaluating the same expression
- treat some workflows, especially "one roll applied to many targets", as action objects above the expression language rather than trying to encode everything as plain arithmetic

That points away from a `DirectDistribution` that only impersonates a scalar distribution, and more toward a first-class direct-roll object with roll provenance.
