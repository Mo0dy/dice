# Session Findings

## Earlier sample/library findings

- The main gaps surfaced by the D&D samples are:
  - function arguments are eager, so writing fully generic crit-aware helpers is still awkward
  - imported helpers all share one global namespace, so larger libraries may eventually want namespacing

## Language review findings

- Top-level nested calls are currently broken.
  - `render(mean(d2), "x", "t")` and `f(g(1))` fail when they appear as statements.
  - The immediate cause is speculative function-definition parsing that re-raises instead of backtracking cleanly in `diceparser.py`.
  - This is amplified by the statement-entry path in `dice.py`, which uses `parser.statement()` for single-line inputs instead of always parsing a full program.

- The numeric surface is internally inconsistent.
  - There are no float literals.
  - There is no unary minus.
  - `/` is currently floor division, so `3 / 2` becomes `1`.
  - `-1` is a syntax error.
  - `1.5` is tokenized as `1 . 5` and currently behaves like probability lookup / dot-selection rather than a float literal.
  - This is the largest syntax trap in the current surface.

- `[]`, `.`, and bare `->` currently produce sub-probability distributions, not conditioned distributions.
  - `d20[20]` keeps mass `0.05` rather than normalizing to certainty.
  - `d20[20] $ mean` gives `1.0` rather than `20`.
  - `!(d20 >= 11 -> 5)` can return `{}` because sampling explicitly allows total mass below `1`.
  - README wording currently says indexing "filters a distribution", which does not make the partial-mass behavior clear.

- Sweep identity is underspecified.
  - Duplicate sweep values are silently deduped, so `[a:1,1,2]` becomes `[a:1,2]`.
  - Duplicate user axis names are allowed, so expressions can contain two different axes both named `a`.
  - That later makes `sumover("a", ...)` ambiguous.

- Prefix `~` and `!` have unusual precedence.
  - They bind to the entire following expression, so `~d2 + 1` parses as `~(d2 + 1)`.
  - That is asymmetric with `d`, `d+`, and `d-`, which bind only to the next factor.

- Rendering is a partial language surface, not a general projection tool.
  - Valid runtime values outside unswept results, one-axis results, and two-axis scalar grids fail only at render time.
  - Comparisons additionally require matching axis names and matching axis values.
  - This is acceptable short-term, but it is a semantic cliff rather than a smooth general facility.

- Exact `h` / `l` semantics are expensive enough to be a language rough corner, not just an implementation detail.
  - `rollhigh` and `rolllow` recursively enumerate all `s^n` outcomes.
  - Expressions that look ordinary in the DSL can become impractical quickly.

## Follow-up findings from discussion

- In the real sample programs under `samples/`, postfix `expr[...]` is not used.
  - Bracket syntax there is used for sweeps, named axes, plotting, and reductions.
  - Branching logic in the samples is handled by `split` and `-> |`, not postfix filtering.
  - That suggests `[...]` as sweep syntax is valuable, while postfix selection is currently marginal in real usage.

- Without postfix `[]`, the language is missing a direct "event membership" form over one shared sample.
  - The question "what is the probability that a `d20` is `10` or `15`?" can be expressed correctly with:
    - `split d20 as roll | roll == 10 -> 1 | roll == 15 -> 1 | otherwise -> 0`
  - `((d20 == 10) + (d20 == 15)) $ mean` happens to give the same numeric answer for this disjoint case, but for the wrong semantic reason: it adds expectations of separate Bernoulli expressions rather than expressing one shared-roll event.

- `==` against a sweep is close to event membership syntactically, but not semantically.
  - `d20 == [10, 15]` is a sweep over two separate target questions.
  - Reducing that sweep does not ask "is one roll in this set?"
  - A counterexample is `total(d20 >= [TARGET:10, 15])`:
    - the real single-roll question collapses to `roll >= 10`
    - current reduction instead builds a count-style distribution over `0`, `1`, and `2`

- A dedicated membership predicate looks warranted.
  - Something like `member(expr, a, b, c)`, `oneof(expr, a, b, c)`, or an infix `in` operator would express "evaluate once, test membership, return Bernoulli".
  - This would cover much of the useful intent that postfix `expr[...]` was gesturing at.

- Sets or finite domains may be worth adding, but the need is clearer than the exact data model.
  - A form like `d20 in {10, 15}` reads naturally for event membership.
  - A categorical die like `d{"fire", "water", "ice"}` is also attractive.
  - The main design tension is whether this should be a strict mathematical set or a more general finite domain:
    - a strict set is unordered and deduplicated
    - a domain literal may be a better long-term fit for dice faces and possible future weighted / repeated categories

- Current design direction under discussion:
  - keep `[...]` clearly for sweeps
  - consider dropping postfix `expr[...]` if it remains unused in samples
  - add an explicit membership/event form instead
  - if collection literals are added, prefer designing them as finite domains first and only later decide whether they should become a full first-class set type

## Set/domain rewrite direction

- The current rewrite direction is now explicitly set-centered.
  - normalized distributions only
  - first-class finite domains
  - `d20` as sugar for `d{1..20}`
  - `expr in {...}` as the direct shared-sample membership question

- Troll is a useful reference, but not a template.
  - Troll collections use `{...}` and `a..b`, which is a good precedent for a domain syntax.
  - Troll collections are unordered multisets and flatten nested collections.
  - We should intentionally diverge by preserving nesting and by keeping explicit Bernoulli distributions instead of empty/non-empty truthiness.

- The likely internal model is a weighted finite domain rather than a strict mathematical set.
  - repeated elements add weight
  - future explicit fractional weights are likely desirable
  - user-facing docs may still say "set", but the runtime type should probably be called `Domain`

- The D&D sample library has been partially moved to the planned set/domain notation so the readability can be evaluated before full implementation lands.
  - core dice now read like `d{1..20}` and `4 d {1..6} h 3`
  - crit checks preview `roll in {20}`
  - a dedicated preview sample now exists under `samples/language/sets_preview.dice`

- Important runtime-model clarification:
  - probabilistic results should be thought of internally as one uniform sweep-indexed container
  - the unswept case is just the zero-axis case of that same container
  - so, operationally, "distributions are internally always sweeps over distributions"
  - the real semantic distinction is between probabilistic values on that container layer and non-probabilistic values such as `Domain` and `Sweep`
