# Session Findings

## Current D&D library work

- The DSL's one-line function-definition rule is a practical stdlib sharp edge.
  - Exact D&D helpers naturally want longer bodies with several branches and shared subexpressions.
  - The current surface pushes library authors toward either dense unreadable one-liners or a larger number of tiny helper functions.

- There is no lightweight local binding form inside an expression.
  - Reusing a computed damage bundle, slot-scaling result, or crit-only dice package often requires a separate top-level helper.
  - This makes stdlib code noisier than the underlying math.

- Boolean-style flags are still just numeric conventions.
  - Modeling rules like "ally adjacent", "target is wounded", or "undead or fiend" works, but only by passing `0`/`1` style parameters and composing them manually.
  - A clearer first-class boolean / logical surface would make rule-heavy libraries less error-prone.

- The language would benefit from a terse clamp/min/max surface.
  - D&D math repeatedly needs bounded quantities such as Divine Smite dice caps, cantrip tiers, or slot-scaling ceilings.
  - Today these are expressible with `split`, but they are more verbose than the rules themselves.

## Renderer iteration pain points

- Sweep alignment across separately-written expressions is still easy to get wrong.
  - For renderer samples, writing `a = f([AC:10..22])` and `b = g([AC:10..22])` looks like "the same AC sweep", but arithmetic like `b - a` can still behave like combining two independent sweeps unless the shared axis is explicitly bound once and reused.
  - In practice this pushes authors toward `ac = [AC:10..22]` scaffolding in cases that feel like they should be semantically aligned by default.

- `~expr` is semantically correct but ergonomically ambiguous when the user really wants a scalar sweep.
  - It returns a degenerate distribution, which still renders fine in many cases, but it is less predictable for follow-up arithmetic and chart composition than `expr $ mean`.
  - For report/sample authoring, this creates friction because "expected value" reads scalar while the runtime surface stays distribution-shaped.

## Online discussion sample pass

- Python orchestration was the right boundary for this pass.
  - The `.dice` samples were a good fit for exact probability calculations, AC sweeps, and round-by-round damage packages.
  - The cross-sample work of dumping structured data, selecting the best mode per AC, and comparing local outputs against online claims was much cleaner in Python than in one giant `dice` program.
  - This is the clearest current example of "keep the math in `dice`, do report assembly and aggregation in Python".

- `split` remains an awkward edge inside user-defined functions.
  - Multiline functions do exist and are useful, but a `split ...` body still feels parser-sensitive in shapes that look like they should be straightforward.
  - In practice, samples were more robust when they exposed raw plan lines and let the Python report layer compute derived comparisons like gaps or "best of two strategies".
  - This is a concrete language pain point because many TTRPG discussions naturally want "evaluate several plans, then compare them".

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
  - This suggests the language is already good at short-horizon round-economy questions when the scenario does not need target death, retarget timing, or enemy-side behavior modeling.
