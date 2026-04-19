# TTRPG Discussions

Initial research backlog of online TTRPG statistics discussions worth recreating in `dice`.

Goal: turn these into sample programs and regression checks that test both mathematical correctness and language ergonomics.

## Implemented Findings

Current implemented D&D discussion samples live under `examples/01_dnd/`.

- Exact matches:
  Advantage/disadvantage rules of thumb matched the expected headline numbers.
  Elven Accuracy matched the common `14.2625%` crit-rate claim exactly.
  Great Weapon Fighting matched the usual `+1.33` on `2d6` and `+0.83` on `1d12`.
- Qualitative matches with assumption-sensitive breakpoints:
  Great Weapon Master versus ASI behaved like the online discussion suggests: the ASI was stronger across more AC values without advantage, while advantage made the power-attack line much better.
  Hunter's Mark versus Crossbow Expert matched the “about two rounds to pay back setup” rule of thumb in the simplified single-target model.
  Magic Missile as a concentration breaker strongly matched the online claim that one-check-per-dart makes the spell dramatically stronger at breaking concentration.
- Useful divergences:
  Bless as party DPR did not support the exact “12.5% closer to maximum DPR” phrasing under the modeled party; the benefit varied much more with AC than that slogan suggests.
  Spiritual Weapon caught up to the simplified Guiding Bolt line by round 2 in direct self-damage terms, which is faster than the skeptical online discussion and likely reflects omitted ally-followup value from Guiding Bolt.
  Polearm Master versus ASI was extremely assumption-sensitive; in the narrow level-4 one-main-attack halberd model, Polearm Master won across the whole tested AC range.
- Language/design takeaway:
  Keeping the exact math and the rendered report in the same `.dice` file worked well for most discussion samples.
  The main remaining pressure points were parser-sensitive `split`-heavy helper shapes and cases where cross-sample synthesis is cleaner in Python than in the DSL itself.

## Cross-Cutting Questions

## [ ] Where Should `dice` End And Python Begin?
Question: At what point is it sensible to drop down to Python, and what kinds of statistical questions fit cleanly in `dice` directly?
Why this is here: Several of the discussions below are good boundary tests. If a problem needs too much state bookkeeping, custom control flow, or post-processing glue, that may be a sign it wants Python orchestration around `dice` rather than a pure `dice` sample. Conversely, if a discussion is common, table-facing, and readable when expressed directly, it should probably stay in `dice`.
What to evaluate against these samples: readability, amount of scaffolding, how naturally the model maps to statements/expressions/sweeps, and whether the final program still looks like something a user would plausibly write by hand.

## D&D 5e

## [ ] Advantage / Disadvantage Rules Of Thumb
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/labqox/some_helpful_probability_rules_of_thumb_for/
Overview: A concise threshold-based summary of `2d20kh1` / `2d20kl1`. The thread highlights checks like advantage making a natural 20 about 1-in-10, a natural 1 about 1-in-400, about a 50% chance to roll 15+, and about a 90% chance to roll 7+; the disadvantage side mirrors those claims.
Mechanics to cover: keep-highest, keep-lowest, exact singleton checks, threshold predicates.
Why it matters: This is a good early correctness target because it turns raw distributions into memorable table-facing facts, which is exactly the kind of output users want from the language.

## [ ] When To Use Sharpshooter
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/jsspco/when_to_use_sharpshooter/
Overview: A discussion of the `-5 to hit / +10 damage` tradeoff. The headline rule of thumb is to use Sharpshooter when enemy AC is at or below roughly `16 + attack modifier - half average damage`, with commenters also reframing the choice in terms of base hit chance.
Mechanics to cover: expected damage under alternate attack modes, AC sweeps, optional flat hit penalty with flat damage bonus.
Why it matters: This is a strong ease-of-use benchmark because the target result is not a single scalar; people want a reusable comparison across AC bands.

## [ ] Great Weapon Master Versus ASI
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/202251/does-great-weapon-master-deal-more-expected-damage-than-an-asi
Overview: A focused optimization discussion on when `-5/+10` is actually better than simply taking Strength. One answer argues that without reliable advantage, an ASI is often the better early damage pick, while GWM becomes much more attractive once advantage is easy to generate.
Mechanics to cover: feat-vs-ASI comparison, expected DPR by AC, advantage-sensitive switching logic.
Why it matters: This is a good counterpart to Sharpshooter because it turns the same core tradeoff into a more general “when should a build take this at all?” benchmark.

## [ ] Polearm Master Versus ASI
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/202307/when-does-polearm-master-deal-more-damage-than-an-asi
Overview: A mathematically explicit comparison between “more accurate and stronger existing attacks” and “one extra butt-end attack.” The answer models expected damage as `h(D+M) + cD` and explores when the extra d4 attack beats a +1 Strength modifier and +1 attack bonus instead.
Mechanics to cover: extra-attack feats, bonus-action attack modeling, crit contribution, feat-vs-ASI breakpoint analysis.
Why it matters: This is a clean reference for multi-attack action modeling and for comparing “one more attack” against “better attacks.”

## [ ] Elven Accuracy Crit-Fishing
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/mm3zb0/elven_accuracy_is_it_really_that_good/
Overview: A discussion of “super advantage” that includes concrete hit and crit-rate comparisons. The thread frames ordinary advantage as taking crit chance from 5% to 9.75%, and Elven Accuracy to about 14.26%, then explores how that interacts with rogues and other advantage-heavy builds.
Mechanics to cover: keep-highest-of-3 d20s, crit probability, expected damage under advantage-heavy builds, feat comparisons.
Why it matters: This is an especially useful reference for correctness because it checks that the language handles “triple d20 keep highest” cleanly instead of only ordinary advantage/disadvantage.

## [ ] Bless As Party DPR
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/1of3fyk/how_to_calculate_how_much_extra_damage_the_bless/
Overview: A recent attempt to quantify Bless as a party-wide damage amplifier rather than a simple `+12.5% damage` buff. The central claim is that Bless moves party DPR about 12.5% closer to its theoretical maximum, which means the relative payoff is much larger when hit chances are bad, such as high AC or disadvantage-heavy situations.
Mechanics to cover: `1d4` attack buffs, party-wide aggregation, AC sweeps, advantage/disadvantage interaction.
Why it matters: Bless is one of the most common “simple but actually subtle” D&D math questions. This would make a strong ergonomics test for handling buffs over several attackers at once.

### Action Economy Focus

## [ ] Hunter's Mark Versus Crossbow Expert Bonus Action
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/n1c381/hunters_mark_sucks_but_rangers_are_awesome/
Overview: A practical optimization thread about whether Hunter's Mark is actually worth the setup and retargeting cost on ranged ranger builds. One argument in the discussion is that Hunter's Mark often needs around two rounds just to repay the lost Crossbow Expert bonus-action attack, and can easily fall behind again when targets die and the mark has to move.
Mechanics to cover: bonus-action competition, setup turns, retargeting costs, multi-round DPR comparison, concentration opportunity cost.
Why it matters: This is exactly the kind of action-economy case that separates “correct isolated math” from “real combat math people actually care about.”

## [ ] Spiritual Weapon Versus Immediate Damage Or Bless
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/k0vw32/spiritual_weapon_is_not_a_good_spell_an_essay_cmv/
Overview: A long argument about whether Spiritual Weapon is actually efficient once setup time and bonus-action usage are counted. One concrete comparison in the thread is that a 2nd-level Guiding Bolt can outperform first-round Spiritual Weapon damage, and that Spiritual Weapon may need multiple rounds before it catches up, especially if advantage from Guiding Bolt matters.
Mechanics to cover: delayed payoff, recurring bonus-action attacks, break-even-by-round analysis, alternate spell choices on round one.
Why it matters: This is a strong sample for modeling “damage now versus damage later,” which shows up everywhere in action-economy debates.

## [ ] Healing Word Versus Cure Wounds
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/na3awn/the_best_healing_spell_in_your_game_is_not_what/
Overview: A discussion built around the familiar claim that Cure Wounds is usually worse than Healing Word because the action cost matters more than the extra healing. The interesting part is not just “bonus action good”; it is the broader claim that preserving the target's next turn is often worth far more than a few extra HP.
Mechanics to cover: action-vs-bonus-action healing, revive-at-1-HP play, turn preservation, expected fight tempo after a pickup.
Why it matters: This would make a good benchmark for whether `dice` can express tactical value beyond raw healing averages.

## [ ] Yo-Yo Healing And Monster Counterplay
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/k1js8b/healing_word_tanking/
Overview: A concrete “is this intended?” thread about repeatedly using Healing Word to stand a barbarian back up so they can act again before being dropped once more. The follow-up discussion is useful because it brings in monster-side counterplay like finishing off downed PCs or targeting the healer.
Mechanics to cover: repeated pickup loops, initiative-order sensitivity, unconscious-state transitions, alternative enemy behavior assumptions.
Why it matters: This is a good stress test for whether the language should stay at pure player-side probability or also support turn-by-turn scenario scripting.

## [ ] Quickened Spell And Burst-Turn Casting
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/y6k9az/metamagic_quickened_spell/
Overview: A popular discussion about using Quickened Spell to cast Eldritch Blast twice in one turn, especially at level 11 where that means six beams. The thread also highlights the bonus-action spell restriction, which means some superficially obvious combinations are illegal while others are efficient burst turns.
Mechanics to cover: cast-as-bonus-action rules, repeated cantrip output in one turn, resource-limited burst rounds, legal and illegal sequencing.
Why it matters: This is a strong candidate for testing whether `dice` handles “turn packages” cleanly, especially when legality depends on action-type constraints and not just damage formulas.

## [ ] Action Surge Double-Spell Turns
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/11fhp8v/sorcereraction_surge_question/
Overview: A rules-and-optimization thread about what Action Surge actually enables for casters. The key result is that Action Surge can support two leveled action spells in one turn, but it does not bypass the separate restriction created by casting a bonus-action spell.
Mechanics to cover: extra actions, multi-spell rounds, turn sequencing legality, burst-round comparison.
Why it matters: This gives a clean line between “extra action” and “extra bonus action” value, which is useful both for engine semantics and for future sample design.

## [ ] Haste With Extra Attack And Two-Weapon Fighting
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/100601/does-extra-attack-stack-with-haste
Overview: A classic rules question on how Haste interacts with a martial turn. The reference answer is that Extra Attack applies to the normal Attack action, while the hasted action grants only one weapon attack; separate discussions then point out that taking that hasted Attack action can still unlock other effects like Two-Weapon Fighting.
Mechanics to cover: differentiated action types, one-attack-only restricted actions, interaction-triggered bonus attacks.
Why it matters: This is a compact but important action-economy correctness target because it checks that the language can distinguish “another action” from “another full attack routine.”

## [ ] Solo Bosses, Legendary Actions, And Party Turn Count
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/1cos89z/action_economy_and_legends/
Overview: A broader encounter-design discussion about whether solo monsters fail mainly because they only get one turn against a party with four or five turns. The useful part for this backlog is the way people compare “number of turns” to “value of turns,” then use legendary actions, lair actions, and minions as fixes.
Mechanics to cover: side-by-side turn budgets, extra off-turn actions, boss-versus-party scenario modeling.
Why it matters: This is the encounter-scale version of action economy, and it may be a useful boundary marker for deciding when `dice` alone is enough versus when Python-side simulation or scenario orchestration becomes cleaner.

## [ ] Fireball Expected Damage With Save-For-Half
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/178201/how-to-include-successful-saves-when-calculating-fireballs-average-damage
Overview: A straightforward Q&A on expected damage when a saving throw deals half damage on success. The key reference formula is `expected = p(successful save) * half damage + p(failed save) * full damage`, extended to multiple identical targets.
Mechanics to cover: save-vs-DC checks, branch-on-success, half-damage, multi-target aggregation.
Why it matters: Save-for-half is common enough that the language should make it feel direct instead of forcing users into ad hoc probability algebra.

## [ ] Conditional Sneak Attack On A Two-Weapon Round
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/97715/why-is-anydice-giving-me-a-larger-result-than-expected
Overview: A user tries to model a rogue turn where Sneak Attack is applied only if the first attack misses and the second hits. The discussion is really about conditional sequencing and correlated turn structure, not just one damage formula.
Mechanics to cover: ordered attack resolution, conditional extra damage, shared turn state, mutually exclusive branches.
Why it matters: This is an excellent expressiveness test. A dice language that handles simple independent rolls but struggles with “if the first attack missed, then the second gets Sneak Attack” is still missing a lot of real table math.

## [ ] 4d6 Drop Lowest Ability Score Distribution
System: D&D 5e / general fantasy chargen
Link: https://www.reddit.com/r/dndnext/comments/r8yfvs/probabilities_of_each_roll_using_4d6_drop_the/
Overview: A probability table for `4d6 drop lowest`, including the full 3..18 distribution. The headline takeaways are that 13 is the modal result, the average roll is about 12.2, and rolling an 18 is much more likely than rolling a 3.
Mechanics to cover: drop-lowest, discrete distribution tables, repeated-stat generation, array-level summaries.
Why it matters: Character generation is a natural showcase surface, and this gives both per-roll reference numbers and follow-up ideas like “chance of at least one 16+ in a six-stat array.”

## [ ] Great Weapon Fighting Average Damage
System: D&D 5e
Link: https://rpg.stackexchange.com/questions/47172/how-much-damage-does-great-weapon-fighting-add-on-average
Overview: A canonical average-damage calculation for the Great Weapon Fighting style. The main reference table gives increases like about `+0.83` for `1d12` and about `+1.33` for `2d6`, which makes the style a useful case for reroll-on-low-die semantics.
Mechanics to cover: reroll-on-1-or-2, per-die rerolls inside multi-die weapon damage, exact average damage deltas.
Why it matters: This is a very direct engine-correctness target. If reroll semantics are wrong, this example will expose it immediately.

## [ ] Magic Missile As Concentration Breaker
System: D&D 5e
Link: https://www.reddit.com/r/dndnext/comments/164jepm/magic_missile_and_concentration/
Overview: A long-running rules-and-math discussion about whether Magic Missile produces one concentration check or one per dart when focused on a single target. The interesting part for `dice` is not only the disputed ruling, but the downstream tactical claim that the spell can become a specialized concentration-breaking and death-save-finishing tool if each dart is treated as a separate damage instance.
Mechanics to cover: repeated simultaneous damage packets, concentration/save counts under alternate rulings, guaranteed-hit multi-dart spells.
Why it matters: This is a good scenario test because it combines exact damage, repeated effects from one spell, and table-rule toggles that should be easy to express intentionally.

## Pathfinder 2e

## [ ] Strike-Strike Versus Power Attack
System: Pathfinder 2e
Link: https://www.reddit.com/r/Pathfinder2e/comments/12j89wh/pathfinder_math_how_to_calculate_average_damage/
Overview: A worked expected-damage example for PF2e’s four degrees of success. In the sample, a level 1 fighter with a longsword against AC 16 gets about 11.9 expected damage from striking twice versus about 11.7 from Power Attack, and the thread continues by checking how flanking changes the comparison.
Mechanics to cover: crit-fail/fail/success/crit-success buckets, MAP on later attacks, crit doubling, action comparison.
Why it matters: This is a high-value target because it mixes exact probabilities with action-economy choices, which matches how people actually analyze PF2e.

## [ ] Value Of Third Actions
System: Pathfinder 2e
Link: https://www.reddit.com/r/Pathfinder2e/comments/124nved/objective_value_of_third_actions_how_to_quantify/
Overview: A deeper PF2e analysis that normalizes expected damage by damage-roll size and compares first, second, and third attacks against alternatives like flanking, Demoralize, moving, and raising a shield. One baseline result in the post is about `0.70 / 0.40 / 0.15` normalized damage for three non-agile strikes against a typical on-level high-AC foe.
Mechanics to cover: degree-of-success math, MAP sweeps, status/circumstance bonuses, offensive vs defensive action tradeoffs.
Why it matters: This is the kind of longer-form strategic analysis that can become a flagship sample for the language once distributions, sweeps, and named scenarios feel clean.

## Forged In The Dark / PbtA / Related

## [ ] Blades In The Dark Dice Pool Table
System: Blades in the Dark
Link: https://www.reddit.com/r/bladesinthedark/comments/v2e0wo/dice_pool_probabilities_blades_in_the_dark/
Overview: A clean table for 0d through 6d action results. The post gives percentages for no success, partial success, full success, and critical success; for example 2d is `25 / 44 / 28 / 3` and 4d is `6 / 42 / 39 / 13`.
Mechanics to cover: highest-of-pool classification, “zero dice means roll two and keep the lowest,” criticals from multiple sixes.
Why it matters: This is a strong non-d20 benchmark and would exercise a very different style of resolution than the current D&D-heavy samples.

## [ ] PbtA 2d6 Versus d12
System: Powered by the Apocalypse
Link: https://www.reddit.com/r/PBtA/comments/jik4jj/difference_between_rolling_a_2d6_and_rolling_a/
Overview: A discussion about why `2d6` is not interchangeable with `d12` even when the baseline miss/weak-hit/strong-hit bands are tuned to line up. The thread gives the classic PbtA baseline of about `42% miss / 42% weak hit / 16% strong hit` at +0 and points out how modifiers diverge sharply between bell-curve and flat distributions.
Mechanics to cover: summed dice, banded outcomes, modifier sweeps, comparison between flat and curved distributions.
Why it matters: This is a good language-design target because it checks whether the system can explain not just “what is the probability,” but “how do two superficially similar mechanics behave differently across modifiers?”

## Savage Worlds

## [ ] Why Exploding Dice Are Structurally Important
System: Savage Worlds
Link: https://www.reddit.com/r/savageworlds/comments/i9xft8/exploding_dice/
Overview: A discussion about whether the game still works if aces are removed or capped. The most useful claim is that exploding dice are baked into the probability structure deeply enough that some outcomes become impossible without them; one commenter notes that an untrained extra cannot succeed at all without explosions.
Mechanics to cover: exploding dice, target-number reachability, optional house-rule comparison.
Why it matters: This is a strong semantic target because it tests whether the language can model mechanics whose upper tail is open-ended and whose feasibility changes under house rules.

## [ ] Wild Die Size And The “d+1” Kink
System: Savage Worlds
Link: https://www.reddit.com/r/savageworlds/comments/12aziq6/is_it_worth_it_to_increase_your_wild_die/
Overview: A probability discussion around trait dice, wild dice, raises, and acing. The thread surfaces the counterintuitive result that a bigger die is generally better, but because of ace behavior a die can be slightly worse exactly at the `die size + 1` threshold; for example an exploding d6 can beat 7 slightly more often than a d8.
Mechanics to cover: exploding trait die plus exploding wild die, take-highest, success-vs-raise thresholds, TN sweeps.
Why it matters: This is a very good “interesting bug-shaped distribution” benchmark. If `dice` models it clearly, that will say a lot about both correctness and usability.

## Ironsworn

## [ ] Core Roll, Progress, And Momentum Tables
System: Ironsworn
Link: https://www.reddit.com/r/rpg/comments/l99fhw/ironsworn-probabilities/
Overview: A large post with probability tables for standard rolls, progress rolls, and momentum use. It includes exact strong-hit / weak-hit / miss percentages by modifier, plus the very reusable progress table where progress 6 corresponds to `25% strong / 50% weak / 25% miss`.
Mechanics to cover: `1d6 + stat` versus two challenge d10s, best-of-zero-one-two comparisons, progress as a fixed score, momentum burn.
Why it matters: This is a great reference set for any future support for opposed-threshold or custom outcome-band systems that are not plain additive dice.

## World Of Darkness

## [ ] oWoD Success / Failure / Botch Chart
System: Old World of Darkness
Link: https://forum.theonyxpath.com/forum/main-category/main-forum/the-classic-world-of-darkness/615300-owod-dice-probability-chart
Overview: A forum post sharing a spreadsheet of success percentage, failure percentage, botch percentage, and average successes per roll for WoD dice pools.
Mechanics to cover: dice pools, per-die success counting, botches, average-success summaries over many pool sizes and difficulties.
Why it matters: This would broaden coverage beyond additive and keep-highest systems into classic success-counting pools.

## Next Research Pass

- Opposed dice-pool systems with explicit margin-of-success tables.
- Symbol dice systems where outcomes are not numeric sums.
- More Pathfinder 2e spell/save discussions, especially success-with-effect and failure-without-effect cases.
- OSR / Traveller chargen discussions where the interesting quantity is an entire career or full stat array, not a single roll.
