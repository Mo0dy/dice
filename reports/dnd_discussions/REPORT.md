# D&D Discussion Comparison Report

This report is generated from the `samples/dnd/discussions/` programs.
Raw serialized outputs live under `reports/dnd_discussions/data/`.

## Coverage

- Samples executed: 10
- Focus: D&D online discussion claims that are useful as exactness or ergonomics benchmarks

## Findings

### Advantage Rules Of Thumb

- Sample: `samples/dnd/discussions/advantage_rules_of_thumb.dice`
- Source: https://www.reddit.com/r/dndnext/comments/labqox/some_helpful_probability_rules_of_thumb_for/
- Online claim: Advantage should put nat 20 at about 9.75%, nat 1 at about 0.25%, 15+ at about 51%, and 7+ at about 91%.
- Comparison: Exact match to the thread's headline numbers after ordinary rounding.
- Plain nat 20: 5.00%
- Advantage nat 20: 9.75%
- Advantage nat 1: 0.25%
- Advantage 15+: 51.00%
- Advantage 7+: 91.00%
- Disadvantage nat 1: 9.75%

### Elven Accuracy Crit-Fishing

- Sample: `samples/dnd/discussions/elven_accuracy_crit.dice`
- Source: https://www.reddit.com/r/dndnext/comments/mm3zb0/elven_accuracy_is_it_really_that_good/
- Online claim: Crit rate should move from 5.00% to 9.75% with advantage and 14.26% with Elven Accuracy.
- Comparison: Exact match on the crit-rate claims; hit-rate gains versus AC 15 are also easy to inspect in the sample output.
- Plain crit: 5.000%
- Advantage crit: 9.750%
- Elven Accuracy crit: 14.2625%
- Hit chance vs AC 15 at +8: plain 70.00%, advantage 91.00%, Elven Accuracy 97.30%

### Great Weapon Fighting Average Damage

- Sample: `samples/dnd/discussions/great_weapon_fighting_average.dice`
- Source: https://rpg.stackexchange.com/questions/47172/how-much-damage-does-great-weapon-fighting-add-on-average
- Online claim: Great Weapon Fighting should add about +1.33 damage to 2d6 weapons and about +0.83 damage to 1d12 weapons.
- Comparison: Exact match after rounding.
- 2d6 mean: 7.000 -> 8.333 (delta 1.333)
- 1d12 mean: 6.500 -> 7.333 (delta 0.833)

### Great Weapon Master Versus ASI

- Sample: `samples/dnd/discussions/gwm_vs_asi.dice`
- Source: https://rpg.stackexchange.com/questions/202251/does-great-weapon-master-deal-more-expected-damage-than-an-asi
- Online claim: Without reliable advantage, an early ASI is often the safer damage pick; with advantage, Great Weapon Master becomes much more attractive.
- Comparison: Matches the thread qualitatively: under these level-4 assumptions the feat build needs to lean on the power-attack mode, and advantage dramatically expands the AC range where it beats the ASI build.
- GWM build beats ASI without advantage at AC values [10, 11, 12, 13].
- GWM build beats ASI with advantage at AC values [10, 11, 12, 13, 14, 15].
- The sample exposes both the plain swing and the power-attack swing so the report layer can choose the better mode per AC.

### Polearm Master Versus ASI

- Sample: `samples/dnd/discussions/polearm_master_vs_asi.dice`
- Source: https://rpg.stackexchange.com/questions/202307/when-does-polearm-master-deal-more-damage-than-an-asi
- Online claim: The extra butt-end attack can outperform an early +2 Strength, depending on assumptions about weapon, attack count, and accuracy.
- Comparison: Under this one-attack level-4 halberd model, Polearm Master wins across the whole tested AC range with and without advantage.
- Polearm Master beats the ASI build without advantage at AC values [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22].
- Polearm Master beats the ASI build with advantage at AC values [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22].
- This is strongly assumption-sensitive because the sample intentionally models the narrow early-level one-attack case that favors extra bonus-action attacks.

### Bless As Party DPR

- Sample: `samples/dnd/discussions/bless_party_dpr.dice`
- Source: https://www.reddit.com/r/dndnext/comments/1of3fyk/how_to_calculate_how_much_extra_damage_the_bless/
- Online claim: Bless moves party DPR about 12.5% closer to its theoretical maximum, and its relative value rises when accuracy is bad.
- Comparison: The second part matches clearly: Bless matters much more as AC climbs. The exact '12.5% closer to max' phrasing does not hold under this party model because the benefit is concentrated near the low-probability tail of missed attacks.
- Gap closed at AC 16: 35.06%
- Gap closed at AC 20: 22.46%
- Gap closed ranges from 19.04% to 69.24% across AC 10..22.

### Hunter's Mark Versus Crossbow Expert Bonus Action

- Sample: `samples/dnd/discussions/hunters_mark_xbe_rounds.dice`
- Source: https://www.reddit.com/r/dndnext/comments/n1c381/hunters_mark_sucks_but_rangers_are_awesome/
- Online claim: Hunter's Mark often needs around two rounds just to repay the lost Crossbow Expert bonus-action attack.
- Comparison: Matches under the simplified single-target model here: the mark build is still slightly behind on round 1 and clearly ahead by round 2.
- Round 1 cumulative DPR gap: -0.125
- Round 2 cumulative DPR gap: 6.700
- Break-even round: 2

### Spiritual Weapon Versus Guiding Bolt

- Sample: `samples/dnd/discussions/spiritual_weapon_rounds.dice`
- Source: https://www.reddit.com/r/dndnext/comments/k0vw32/spiritual_weapon_is_not_a_good_spell_an_essay_cmv/
- Online claim: Spiritual Weapon may need multiple rounds to catch up to immediate-damage alternatives, especially once Guiding Bolt's granted advantage is counted.
- Comparison: The sample reaches break-even by round 2 on direct caster damage alone, which is faster than the thread's skepticism. That difference is expected because this model omits the allied attack that could cash in Guiding Bolt's advantage.
- Round 1 cumulative DPR gap: -0.650
- Round 2 cumulative DPR gap: 4.675
- Break-even round in the simplified self-damage model: 2

### Burst Turns, Action Surge, And Haste

- Sample: `samples/dnd/discussions/burst_turns.dice`
- Source: https://www.reddit.com/r/dndnext/comments/y6k9az/metamagic_quickened_spell/
- Online claim: Quickened Spell at level 11 enables six Eldritch Blast beams in one turn; Action Surge allows two leveled action spells; Haste adds one attack, not another full attack routine.
- Comparison: Matches the structural online claims exactly; this sample turns them into explicit expected-damage deltas.
- Quickened Agonizing Eldritch Blast doubles expected damage from 17.925 to 35.850.
- Action Surge doubles the single-fireball expectation from 22.300 to 44.600.
- Haste raises the fighter turn from 10.650 to 15.975, which is one extra attack rather than another full two-attack action.

### Magic Missile Concentration Pressure

- Sample: `samples/dnd/discussions/magic_missile_concentration.dice`
- Source: https://www.reddit.com/r/dndnext/comments/164jepm/magic_missile_and_concentration/
- Online claim: If concentration requires one check per dart, Magic Missile becomes a much stronger concentration breaker than under the one-check ruling.
- Comparison: Matches strongly and numerically: the per-dart interpretation radically increases failure rates, especially at higher slot levels.
- At Con +2, fail chance is 35.00% for one total check, 72.54% for 3 darts, and 88.40% for 5 darts.
- At Con +5, fail chance is 20.00% for one total check, 48.80% for 3 darts, and 67.23% for 5 darts.
