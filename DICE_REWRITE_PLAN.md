# DICE Rewrite Plan

## Status

This is the current active rewrite direction for the project.

The next rewrite phase is set-centered. The language should move toward:

- normalized probability distributions only
- first-class finite domains written with set-like syntax
- explicit event membership instead of partial-mass filtering
- a clean separation between domains and sweeps

## Goals

1. Eliminate unnormalized distributions from the runtime surface.
2. Make finite domains a core language value.
3. Treat `d20` as sugar for `d{1..20}`.
4. Allow domain members to be arbitrary runtime values, including nested domains and other non-numeric values.
5. Keep sweep analysis as a distinct feature rather than overloading domain syntax.
6. Prefer one internally coherent model over compatibility with the current postfix indexing semantics.

## Troll Reference

The Troll manual is a useful reference point for collection-oriented dice semantics:

- Troll uses curly-brace collection literals such as `{1, 2, 1}`.
- Troll uses `1..6` for inclusive integer ranges.
- Troll uses `choose` to sample uniformly from a collection.
- Troll treats collections as unordered multisets.

Those ideas are useful, but we should intentionally diverge where our goals are different:

- Troll flattens nested collections. We should not do this by default, because we want domains over arbitrary values, including nested domains.
- Troll uses empty vs non-empty collections as truthiness. We already have Bernoulli `0` / `1` distributions and should keep explicit probability values.
- Troll allows partial / empty collections as part of the semantic core. We want normalized probability distributions only.

## Core Runtime Values

The rewrite should converge on three main runtime categories:

- probabilistic results
  one unified sweep-indexed container of normalized distributions
- `Domain`
  a finite weighted domain of values, written with set-like syntax
- `Sweep`
  a finite analysis axis used for broadcast evaluation and rendering

Important clarification:

- probabilistic results should be treated internally as one uniform container
- the unswept case is just the zero-axis case of that container
- so, operationally, distributions are always "sweeps over distributions", with zero axes as the simplest case

Conceptually:

- the probabilistic container is for ordinary deterministic and random expression results
- `Domain` is for membership and sampling
- `Sweep` is for parameter studies and rendering axes

These categories should not share syntax or semantics by accident.

## Normalization Invariant

This should become a hard runtime invariant:

- every distribution stored in a successful probabilistic runtime value has total probability mass exactly `1`
- deterministic literals in probabilistic expressions are treated as degenerate distributions of mass `1`
- operators that would currently yield sub-probability distributions should be redesigned or rejected

Consequences:

- postfix `expr[...]` should not survive in its current partial-mass form
- bare `cond -> expr` should not survive in its current partial-mass form
- `sample(expr)` should only ever sample normalized distributions
- helpers such as `mean`, `var`, `std`, `cum`, and `surv` should never need to reason about sub-probability inputs

## Domains

### User-facing syntax

Planned syntax:

```text
{10, 15}
{"fire", "water", "ice"}
{1..20}
d{1..20}
```

Range syntax should use one shared notation across the language.

The current rewrite direction is to replace the old colon-based sweep ranges with one shared range syntax:

```text
1..20     // inclusive by default
1..<20    // explicit end-exclusive range
```

Decision:

- ranges are inclusive by default
- `..<` is the explicit end-exclusive form

Open-ended forms such as `..20` or `5..` should only be added if they make sense for a finite domain or finite sweep. The language should not imply infinite domains or infinite sweeps by default.

### Internal model

User-facing syntax may look like sets, but the internal model should likely be a weighted finite domain:

- repeated members add weight
- future explicit fractional weights should be allowed
- equality should be based on value + accumulated weight, not source spelling

This is stricter and more useful than a plain mathematical set while still reading naturally.

The internal type name should be `Domain`, even if user-facing documentation continues to say "set" informally.

### Nesting

Domains should preserve nesting:

- domains may contain domains
- domains may contain non-numeric values such as strings
- domains may eventually contain dice-valued objects if we decide those are first-class values

Unlike Troll, nested domains should not be flattened automatically.

## Dice Over Domains

### Single-die sampling

`d domain` should mean:

- normalize the domain weights
- choose one element from the domain
- return a normalized distribution over the chosen outcomes

Examples:

```text
d{1..20}
d{"fire", "water", "ice"}
```

### Numeric sugar

Numeric dice sugar should remain:

```text
d20 == d{1..20}
```

More generally, when the right-hand side is numeric and positive:

```text
dN
```

should remain sugar for:

```text
d{1..N}
```

### Multiple dice

Current multi-die syntax such as `2d6` means repeated independent rolls summed together.

That should remain the numeric shorthand:

```text
2d6 == repeat_sum(2, d{1..6})
```

Open question:

- what surface should represent repeated draws from non-numeric domains?

For now, repeated-sum shorthand should stay numeric-only.

## Membership

The language needs a direct shared-sample membership form.

Planned form:

```text
expr in domain
```

Semantics:

- evaluate `expr` once
- test whether the sampled outcome belongs to `domain`
- return a Bernoulli distribution over `1` and `0`

Examples:

```text
d20 in {10, 15}
roll in {"fire", "cold"}
```

This should replace most of the conceptual need for postfix `expr[...]`.

## Sweeps

Sweep syntax should remain bracket-based for introducing an analysis axis, but the range expression inside the sweep should use the same shared range syntax as domains.

```text
[10..20]
[10..20]
[10..<20]
[AC:10..20]
[name:a, b, c]
```

Sweeps are still the correct tool for:

- parameter studies
- plotting across targets
- reduction with `sumover` and `total`

This gives one consistent range language:

- `10..20` is an inclusive range expression
- `10..<20` is an explicit end-exclusive range expression
- `{10..20}` is a domain containing that integer range
- `[AC:10..20]` is a named sweep over that same range

Domains and sweeps should still stay distinct:

- `{...}` is a finite domain
- `[...]` is a sweep

## Operators That Need Redesign

### Remove or replace postfix indexing

Current postfix `expr[...]` produces partial-mass distributions.

That conflicts with the normalization invariant and should be removed or replaced.

### Redefine bare `->`

Current bare `cond -> expr` produces partial-mass results.

To preserve normalization, bare `->` should instead mean:

```text
cond -> expr
```

desugars to:

```text
cond -> expr | 0
```

This keeps the common "on success, otherwise zero" reading while preserving normalized results.

The operator should still work over the unified probabilistic container, with deterministic `0` treated as a degenerate distribution.

### Revisit `mass(...)`

If normalized distributions are mandatory, `mass(expr)` is no longer a useful general summary of ordinary runtime values.

It should likely be:

- retired
- or replaced with an explicit event/domain probability helper
- or limited to a different kind of object introduced later

## Sample Integration

The D&D sample programs are a good integration target for the domain rewrite.

Representative translations:

```text
d20                -> d{1..20}
d8                 -> d{1..8}
4 d 6 h 3          -> 4 d {1..6} h 3
roll == 20         -> roll in {20}
[AC:10:20]         -> [AC:10..20]
```

The samples may temporarily move ahead of the implementation so we can evaluate the readability of the new surface before every parser/runtime change is finished.

## Suggested Rewrite Order

1. Add a runtime `Domain` type and decide its internal weighted representation.
2. Add one shared range syntax with inclusive-by-default `a..b` and explicit end-exclusive `a..<b`.
3. Add syntax for domain literals `{...}` built on top of that shared range syntax.
4. Update sweep range syntax to use the same range expressions inside `[...]`.
5. Add `in` membership and make it return Bernoulli distributions.
6. Add `d{...}` sampling.
7. Preserve `d20` as sugar for `d{1..20}`.
8. Make the unified probabilistic container model explicit in code and docs.
9. Enforce normalized distributions in runtime helpers.
10. Remove postfix partial-mass indexing.
11. Redefine bare `cond -> expr` as `cond -> expr | 0`.
12. Revisit `mass(...)` and related examples.
13. Update README, samples, and tests together around the new surface.

## Immediate Next Task

The next concrete implementation task should be:

1. define the `Domain` runtime API
2. decide how weighted members are represented and normalized
3. decide the exact supported range forms beyond `..` and `..<`, including whether any open-ended forms are allowed
4. add parser support for `{...}`, shared range expressions, updated sweep ranges, and `in`
5. update the samples to reflect the intended set/domain surface
