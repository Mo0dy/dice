# DICE Rewrite Plan

## Status

This is the current active rewrite direction for the project.

The goal is to simplify the runtime around one main semantic object and remove the old split between `Distrib` and `ResultList`.

## Problem Summary

The current design mixes several overlapping concepts:

- `Distrib` for probability distributions
- `ResultList` for target-to-value tables
- range syntax that behaves like a sweep in practice
- rendering concerns mixed into semantic result types

This makes the language harder to reason about. In particular, `ResultList` currently acts both like:

- a probability table from comparisons
- a resolved expected-value table after `->`

That makes operator behavior inconsistent and ad hoc.

## New Core Model

The rewrite should move to a single main semantic container.

### Main runtime object

Use one unified object, currently best thought of as `Distributions`.

It represents:

- one probability distribution if there are no sweeps
- many probability distributions indexed by sweep assignments if sweeps are present

Conceptually:

- no sweep: one distribution
- one sweep: map from one sweep value to one distribution
- many sweeps: map from the cross product of sweep assignments to one distribution each

This replaces `ResultList` as a semantic result type.

### Outcomes

Probability distributions may contain:

- numeric outcomes
- symbolic outcomes such as `true` and `false`

Comparisons should return boolean distributions over symbolic atoms, not `0` and `1`.

Example:

```text
d20 >= 11
=> {true: 0.5, false: 0.5}
```

## Sweeps

### Sweep values

Ranges should become sweep values.

There is no need to distinguish deeply between:

- unnamed sweeps
- named sweeps

They are the same kind of value, with optional metadata.

Examples:

```text
d20 >= [5:10]
d20 >= [AC:5:10]
```

Unnamed sweeps can receive generated names internally based on occurrence order.

### Sweep semantics

An expression containing sweeps evaluates over the full cross product of all sweeps present in the expression.

Each point in that cross product produces one probability distribution.

This means the evaluator should return:

- one distribution when there are no sweeps
- a sweep-indexed set of distributions otherwise

### Consequence

This effectively replaces the old meaning of range syntax as a first-class list-like runtime value.

That is acceptable because ranges are already used primarily as sweep inputs.

## Operators Under The New Model

### Comparisons

Comparisons return boolean distributions.

Examples:

```text
d20 >= 11
d20 >= [AC:5:10]
```

### Branching and resolution

`->`, `|`, and `|/` should branch on boolean distributions instead of consuming `ResultList`.

Examples:

```text
d20 >= 11 -> 5 | 0
d20 < 14 -> 2d10 |/
```

The result is still a probability distribution.

Expected-value style rendering should be done later through summarization functions such as `~` or `mean(...)`.

### Summaries

`~expr` should compute expectation pointwise over the current distribution set.

`!expr` should sample one outcome pointwise over the current distribution set.

`mass(expr)` should compute total probability mass pointwise over the current distribution set.

These should preserve sweep structure.

Rendering can then decide how to display scalar summaries over sweep axes.

## Rendering

Rendering should be separated from semantic evaluation.

The evaluator should produce `Distributions`.

Rendering helpers can then provide:

- raw distribution output
- scalar summary output
- table rendering
- single-axis plots
- multi-axis slicing or projection

This is a better home for the old “target table” behavior than a dedicated runtime type like `ResultList`.

## Implementation Strategy

### 1. Remove `ResultList` from the semantic model

- stop creating it from comparisons
- stop requiring it for `->`
- migrate comparison and branching logic to plain distributions

### 2. Introduce the unified container

Implement the main runtime object that can represent:

- one unswept distribution
- a sweep-indexed set of distributions

This container should be the standard return type for evaluation.

### 3. Treat ranges as sweeps

Parser and interpreter changes should make range syntax produce sweep values instead of plain list values.

Named sweep syntax should also be added.

### 4. Lift operators over sweeps automatically

Most semantic functions should ignore sweeps directly and operate on one unswept distribution at a time.

Then a helper, likely a decorator, should lift them across sweep dimensions automatically.

This should work similarly to broadcasting or vectorization.

Recommended shape:

- write base semantic functions for one plain distribution
- use a decorator such as `@lift_sweeps`
- the decorator aligns sweep axes, builds the cross product, applies the base function pointwise, and reassembles the result

### 5. Rebuild rendering on top

After semantic evaluation is unified, add rendering helpers for:

- textual summaries
- tables
- plots

These should consume the unified distribution container instead of special-case runtime types.

## Suggested Rewrite Order

1. Specify the new runtime data model in code comments or docs.
2. Replace comparison results with boolean distributions.
3. Rework `->`, `|`, and `|/` to branch on boolean distributions.
4. Introduce sweep values and sweep-aware evaluation.
5. Add the sweep-lifting helper/decorator.
6. Remove `ResultList`.
7. Rework rendering around the new container.
8. Update README examples and tests alongside each step.

## Constraints For The Rewrite

- keep the language executable at each step when possible
- prefer one coherent semantic model over compatibility hacks
- treat old macro/preprocessor behavior as out of scope unless explicitly reintroduced
- keep `README.md` as the brief user-facing contract
- extend tests as the new model lands

## Immediate Next Task

The next concrete implementation task is:

1. define the unified distribution container API
2. decide the internal representation of sweep assignments
3. prototype a sweep-lifting helper for one or two operators
4. replace comparison output with boolean distributions
