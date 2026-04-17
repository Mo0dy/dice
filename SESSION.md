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
