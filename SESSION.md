# Session Findings

## Concrete Language Pain Points

The earlier notes in this file and in [TTRPG_DISCUSSIONS.md](/home/felix/_Documents/Projects/dice/TTRPG_DISCUSSIONS.md) were directionally right, but too abstract. The useful version is the concrete one: what exact sample shape felt awkward, and what a better language could let the same sample look like.

### Branch-heavy plan comparison leans too hard on `split`

This is the most common shape in the D&D discussion samples. The current language can express it, but the expression surface is denser than the underlying game logic.

Actual examples:

```dice
# examples/01_dnd/hunters_mark_xbe_rounds.dice
plan_value(plan, round):
    split plan as name
    | name == "plain" -> plain_round(16) * round
    | otherwise -> split round | == 1 -> mark_open_round(16) | otherwise -> mark_open_round(16) + mark_full_round(16) * (@ - 1)
```

```dice
# examples/01_dnd/polearm_master_vs_asi.dice
state_value(state, ac):
    split state as name
    | name == "asi" -> halberd_attack(ac, 6, 4) $ mean
    | name == "pam" -> polearm_master_attack(ac, 5, 3) $ mean
    | name == "asi_adv" -> halberd_attack(ac, 6, 4, roll=d+20) $ mean
    | otherwise -> polearm_master_attack(ac, 5, 3, roll=d+20) $ mean
```

Why it hurts:

- These are just "pick one plan, then evaluate it" helpers.
- `split` works, but nested `split` expressions become line-noisy quickly.
- Multiline functions help, but the branch form still reads like parser choreography instead of rules text.

An improved language could look like this:

```dice
plan_value(plan, round):
    match plan:
        "plain" => plain_round(16) * round
        "hunters_mark" =>
            if round == 1
                then mark_open_round(16)
                else mark_open_round(16) + mark_full_round(16) * (round - 1)
```

```dice
state_value(state, ac):
    match state:
        "asi" => mean halberd_attack(ac, 6, 4)
        "pam" => mean polearm_master_attack(ac, 5, 3)
        "asi_adv" => mean halberd_attack(ac, 6, 4, roll=d+20)
        "pam_adv" => mean polearm_master_attack(ac, 5, 3, roll=d+20)
```

The main point is not the exact syntax. The point is that plan selection wants a first-class branching surface that reads as plan selection, not as a clever distribution split.

More pragmatic resolution for this specific problem:

- A dedicated `match` form may not be the first thing to build.
- If tuples and records support ordinary indexing, and `split` can work over tuple/record values, then many current plan-selection helpers become acceptable without new control-flow syntax.
- For example:

```dice
split (plan, round)
| @.0 == "plain" -> plain_round(16) * @.1
| @ == ("hunters_mark", 1) -> mark_open_round(16)
| @.0 == "hunters_mark" -> mark_open_round(16) + mark_full_round(16) * (@.1 - 1)
||
```

- This keeps the solution inside the current `split` model while making tagged tuple state much more usable.
- General tuple/record indexing would help outside `split` too, so this is a broader win than a one-off branch feature.
- Destructuring would still make the same pattern substantially cleaner.

For example, a more elegant follow-on could look like:

```dice
split (plan, round) as (plan_name, round_number)
| plan_name == "plain" -> plain_round(16) * round_number
| (plan_name, round_number) == ("hunters_mark", 1) -> mark_open_round(16)
| plan_name == "hunters_mark" -> mark_open_round(16) + mark_full_round(16) * (round_number - 1)
||
```

- If tuple/record destructuring exists, a pattern-oriented `match` likely becomes much cheaper to add conceptually, because much of the interesting work is already in the structured-value representation and binding mechanics.
- At that point, `match` would mostly be a readability layer over capabilities the language already has, rather than a completely separate semantic feature.

### Bounded tier math wants `clamp` / `min` / `max`

Several D&D helpers are structurally simple, but read longer than the rule they implement because they have to spell out caps using `split`.

Actual examples:

```dice
# stdlib/dnd/weapons.dice
divine_smite_dice(slot_level): split slot_level | >= 5 -> 5 | >= 1 -> @ + 1 | otherwise -> 0

divine_smite_dice_vs_fiend(slot_level): split divine_smite_dice(slot_level) + 1 | >= 6 -> 6 | otherwise -> @
```

```dice
# stdlib/dnd/core.dice
cantrip_dice(level, die_size): split level | >= 17 -> 4 d die_size | >= 11 -> 3 d die_size | >= 5 -> 2 d die_size | otherwise -> d die_size

eldritch_blast_beams(level): split level | >= 17 -> 4 | >= 11 -> 3 | >= 5 -> 2 | otherwise -> 1
```

Why it hurts:

- These are all tier or cap rules.
- They are mathematically simple and common in tabletop systems.
- The current spelling is correct, but verbose enough that authors start building helper stacks just to keep samples readable.

An improved language could look like this:

```dice
divine_smite_dice(slot_level): clamp(slot_level + 1, 0, 5)
divine_smite_dice_vs_fiend(slot_level): clamp(divine_smite_dice(slot_level) + 1, 0, 6)
```

```dice
cantrip_dice(level, die_size): d die_size ^ tier(level, 1, 5 => 2, 11 => 3, 17 => 4)
eldritch_blast_beams(level): tier(level, 1, 5 => 2, 11 => 3, 17 => 4)
```

Even just `min` and `max` would remove a lot of noise here.

### Rule toggles currently encourage duplicated helpers instead of booleans

The earlier note about "numeric convention booleans" was really pointing at a broader issue: rule toggles do not have a natural first-class surface, so the library tends to fork helpers instead.

Actual examples:

```dice
# stdlib/dnd/spells.dice
toll_the_dead(dc, save_bonus, level=1, roll=d20, save_extra=0):
    save_none(dc, save_bonus, cantrip_dice(level, 8), roll=roll, save_extra=save_extra)

toll_the_dead_wounded(dc, save_bonus, level=1, roll=d20, save_extra=0):
    save_none(dc, save_bonus, cantrip_dice(level, 12), roll=roll, save_extra=save_extra)
```

```dice
# stdlib/dnd/weapons.dice
paladin_smite(ac, attack_bonus, damage_mod, slot_level=1, roll=d20, hit_bonus=0):
    smite_rolls = divine_smite_damage(slot_level)
    attack(ac, attack_bonus, 1 d 8 + smite_rolls, damage_mod, roll=roll, hit_bonus=hit_bonus)

paladin_smite_vs_fiend(ac, attack_bonus, damage_mod, slot_level=1, roll=d20, hit_bonus=0):
    smite_rolls = divine_smite_damage_vs_fiend(slot_level)
    attack(ac, attack_bonus, 1 d 8 + smite_rolls, damage_mod, roll=roll, hit_bonus=hit_bonus)
```

Why it hurts:

- These are one mechanic with a condition, not two unrelated mechanics.
- Duplicating helpers scales badly once a spell or feature has several toggles.
- The duplication makes samples read like API inventory instead of rules composition.

An improved language could look like this:

```dice
toll_the_dead(dc, save_bonus, level=1, wounded=false, roll=d20, save_extra=0):
    die_size = if wounded then 12 else 8
    save_none(dc, save_bonus, cantrip_dice(level, die_size), roll=roll, save_extra=save_extra)
```

```dice
paladin_smite(ac, attack_bonus, damage_mod, slot_level=1, vs_fiend=false, roll=d20, hit_bonus=0):
    extra_smite = if vs_fiend then 1 else 0
    smite_rolls = d8 ^ clamp(slot_level + 1 + extra_smite, 0, 6)
    attack(ac, attack_bonus, 1 d 8 + smite_rolls, damage_mod, roll=roll, hit_bonus=hit_bonus)
```

The missing pieces here are ordinary booleans plus a lightweight conditional expression.

Practical resolution for this specific problem:

- A full boolean runtime type is probably unnecessary here.
- `true` and `false` can likely be introduced as pure syntax sugar over the existing Bernoulli `1` / `0` branch surface.
- That means:
  - parse `true` as the current true Bernoulli outcome
  - parse `false` as the current false Bernoulli outcome
  - keep `condition -> a | b` exactly as it already works
  - render comparison outcomes and boolean-looking values back as `true` / `false` in user-facing output
- This would solve the readability problem for rule toggles without adding new semantic machinery.
- It would not solve the unrelated branch-structure pain around `split`, tier/cap math, sweep alignment, or scenario-state modeling.

### Scalar summaries want a clearer surface than "distribution but degenerate"

The report samples mostly want scalar lines such as expected damage by AC or by round. The language can do this today with `$ mean`, and that is what the current D&D samples use.

Actual examples:

```dice
# examples/01_dnd/spiritual_weapon_rounds.dice
flame_round(): sacred_flame(15, 2, level=5) $ mean

weapon_round():
    swing = spiritual_weapon_attack(16, 7, 4) $ mean
    swing + flame_round()
```

```dice
# examples/01_dnd/bless_party_dpr.dice
fighter(ac, hit_bonus=0): fighter_attack_action(2, ac, 7, 4, hit_bonus=hit_bonus) $ mean
ranger(ac, hit_bonus=0): longbow_attack(ac, 9, 4, hit_bonus=hit_bonus) $ mean
warlock(ac, hit_bonus=0): agonizing_eldritch_blast_by_level(ac, 7, 4, level=11, hit_bonus=hit_bonus) $ mean
```

Why it hurts:

- The model is right, but report authors are almost always thinking in scalars here.
- `~expr` is technically valid for "degenerate distribution at the mean", but it is not the thing authors usually want next.
- Reaching for `$ mean` everywhere is fine, but it reads more like a reduction operator than a first-class notion of expected value.

An improved language could look like this:

```dice
flame_round(): mean sacred_flame(15, 2, level=5)

weapon_round():
    swing = mean spiritual_weapon_attack(16, 7, 4)
    swing + flame_round()
```

```dice
fighter(ac, hit_bonus=0): mean fighter_attack_action(2, ac, 7, 4, hit_bonus=hit_bonus)
```

This is a smaller pain point than `split`, but it shows up everywhere in report-oriented samples.

### Sweep alignment still needs explicit shared-axis scaffolding

The current samples generally avoid sweep-misalignment bugs by binding the axis once and reusing it everywhere.

Actual examples:

```dice
# examples/01_dnd/bless_party_dpr.dice
ac = [AC:10..22]
results = measure_value([MEASURE:"plain", "blessed", "gap_closed"], ac)

plain = measure_value("plain", ac)
blessed = measure_value("blessed", ac)
gap_closed = measure_value("gap_closed", ac)
```

```dice
# examples/01_dnd/polearm_master_vs_asi.dice
ac = [AC:10..22]
results = state_value([STATE:"asi", "pam", "asi_adv", "pam_adv"], ac)

asi = state_value("asi", ac)
pam = state_value("pam", ac)
asi_adv = state_value("asi_adv", ac)
pam_adv = state_value("pam_adv", ac)
```

Why it hurts:

- This is the right defensive pattern today.
- It still feels like extra ceremony for a conceptually simple question: "compare these plans over the same AC sweep".
- If the author forgets to share the bound axis, follow-up arithmetic can become less predictable than expected.

An improved language could look like this:

```dice
ac_sweep [AC:10..22]:
    plain = measure_value("plain", AC)
    blessed = measure_value("blessed", AC)
    gap_closed = (blessed - plain) / (party_hit_cap() - plain)
```

Or more minimally:

```dice
plain = over [AC:10..22] as ac -> measure_value("plain", ac)
blessed = over [AC:10..22] as ac -> measure_value("blessed", ac)
gap_closed = align(blessed - plain)
```

Again, the exact syntax is less important than the intent: if two expressions are obviously over the same named sweep, the language should make that the easy path.

Preferred resolution for this problem:

- Named sweeps should align automatically by default.
- Unnamed sweeps should not align automatically.
- Combining two unnamed sweeps in one expression should be an error rather than silently producing cartesian behavior.
- The user-facing fix should be to name or bind the sweep explicitly first.

That implies a further simplification:

- A value may contain any number of named sweeps.
- A value should contain at most one unnamed sweep.
- Constructing a value that would carry multiple unnamed sweeps should fail early with a direct error.

This gives a clear model:

- named sweep = semantic axis, so alignment is implicit
- unnamed sweep = anonymous generator, so reuse must be made explicit by naming it

Examples of the intended behavior:

```dice
f([AC:10..22]) - g([AC:10..22])    # align by AC automatically
```

```dice
f([10..22]) - g([10..22])          # error: two unnamed sweeps
```

```dice
ac = [AC:10..22]
f(ac) - g(ac)                      # explicit shared axis, therefore aligned
```

```dice
[1..4] + [1..4]                    # error: would create multiple unnamed sweeps
```

This is stricter than maximum convenience, but it is much easier to reason about and avoids hidden coupling or accidental cartesian products.

### There is still no clean scenario-state surface for richer action economy

The D&D discussion pass showed a clear boundary. Fixed-plan comparisons fit the DSL well. Stateful combat scripts are where the surface starts to creak.

Actual example that worked:

```dice
# examples/01_dnd/hunters_mark_xbe_rounds.dice
plan_value(plan, round):
    split plan as name
    | name == "plain" -> plain_round(16) * round
    | otherwise -> split round | == 1 -> mark_open_round(16) | otherwise -> mark_open_round(16) + mark_full_round(16) * (@ - 1)
```

Why it worked:

- Single target.
- No target death.
- No re-target cost after the first mark.
- No enemy-side behavior.

Why the next step gets awkward:

- The moment the sample wants "the marked target died on round 2", or "the monster finished off the downed PC", the program wants explicit state transitions, not just a closed-form round expression.
- That is the real reason some TTRPG questions still want Python orchestration.

An improved language would need something closer to scenario blocks:

```dice
combat 6 rounds:
    state marked = false
    state current_target_hp = hp(target)

    each round:
        when plan == "hunters_mark":
            if !marked:
                bonus_action cast hunters_mark
                marked = true
            else:
                bonus_action hand_crossbow_attack(with hunters_mark)

        when target dies:
            marked = false
            current_target_hp = hp(next_target)
```

That is not a small syntactic addition. It is a different semantic surface. Until something like that exists, Python remains the right fallback for action-economy questions with real combat state.

## What Worked Well

- Keeping the exact math and the rendered report in the same `.dice` file worked well for most discussion samples.
- Multiline functions materially improved readability; the remaining pain is mostly around branchy expression forms, not around local bindings in general.
- Fixed-plan exact comparisons were a strong fit for the DSL:
  - advantage rules of thumb
  - Elven Accuracy crit rate
  - Great Weapon Fighting averages
  - Great Weapon Master versus ASI
  - Polearm Master versus ASI
  - Bless over an AC sweep
  - Hunter's Mark payback by round
  - Spiritual Weapon break-even by round

## Result Notes From The D&D Discussion Pass

- Several online claims matched exactly once turned into exact `dice` samples.
  - Advantage rules of thumb matched the expected 9.75% advantage crit rate, 0.25% advantage nat-1 rate, 51% chance for 15+, and 91% chance for 7+.
  - Elven Accuracy matched the common 14.2625% crit-rate claim exactly.
  - Great Weapon Fighting matched the usual `+1.33` on `2d6` and `+0.83` on `1d12`.

- The main result deltas were in assumption-heavy action-economy discussions, not the exact math baselines.
  - The Bless sample did not support the exact "12.5% closer to maximum DPR" phrasing under the modeled three-attacker party; it landed around 35% at AC 16 and stayed above 19% even at AC 22.
  - Spiritual Weapon caught up to the simplified Guiding Bolt line by round 2 in direct self-damage terms, which is faster than the skeptical online discussion; that difference is plausibly explained by the thread pricing in Guiding Bolt's granted advantage on a later allied attack.
  - Polearm Master versus ASI was extremely assumption-sensitive: in the narrow level-4, one-main-attack halberd model, the feat won across the whole tested AC range.

- The Hunter's Mark versus Crossbow Expert sample was a useful "exact enough" action-economy success case.
  - Under a simple single-target level-5 model, Hunter's Mark was slightly behind on round 1 and ahead by round 2, which lines up well with the thread's rule of thumb.
  - This is a good example of the current boundary: short-horizon fixed-plan action economy fits the DSL well, while richer target-state scripting still points toward Python or a new scenario-language layer.
