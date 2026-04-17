# Sweep Indexing Brainstorm

This document is a syntax and semantics sketch for multidimensional sweep indexing.
It reflects the current brainstorming direction, not a committed language contract.

Related design note: [TUPLE_AND_RECORD_IMPL.md](TUPLE_AND_RECORD_IMPL.md)

## Current Direction

- `expr[...]` is a view builder over an existing sweep.
- Reductions stay outside brackets as ordinary functions.
- The reduction API is value-first:
  - `sum(value, axes?)`
  - `mean(value, axes?)`
  - `max(value, axes?)`
  - `argmax(value, axes?)`
- Omitting `axes` means "reduce over all sweep axes" if that reduction makes sense.
- Tuples and records become first-class runtime values.
- Field access on records is still deferred; indexing examples here assume tuples/records are passed around as opaque values for now.
- Axis specs and coordinates are ordinary values that can be passed around, stored in variables, returned from functions, and used directly in `[]`.
- Brackets accept a mixed list of:
  - axis refs
  - coordinate entries
  - axis spec values
  - coordinate values
  - filter clauses such as `AXIS in {...}`

## New Core Values

### Axis refs

An axis ref identifies one axis.

Examples:

```dice
"AC"
"PLAN"
0
1
```

Named refs use strings.
Unnamed refs use integer positions in the current axis order.

### Axis specs

An axis spec identifies one or more axes.

Examples:

```dice
"AC"
0
("AC", "PLAN")
(0, 1, "AC", "PLAN")
```

Axis specs are useful for:

- reducers
- explicit keep-lists
- axis reordering
- passing axis selections through variables

### Coordinates

A coordinate identifies one point in one or more axes.

Examples:

```dice
(AC: 16)
(PLAN: "great_weapon_master", LEVEL: 11)
(0: 5, 1: 10, AC: 3, PLAN: "greatsword")
```

Coordinates are records.
They can mix positional and named axis references.

### Why tuples and records matter

Once tuples and records exist, the sweep features stop needing custom one-off syntax.
Both reducers and indexers can consume the same structured values.
See also [TUPLE_AND_RECORD_IMPL.md](TUPLE_AND_RECORD_IMPL.md) for the underlying tuple/record syntax and runtime model.

## Shared Mental Model

Given a study like this:

```dice
damage = attack_damage(
    [PLAN:"longsword", "great_weapon_master", "hunters_mark_longbow"],
    [AC:10..22],
    [LEVEL:1, 5, 11, 17],
    [SEED:0..99]
)
```

the shape is:

```text
PLAN x AC x LEVEL x SEED -> damage
```

The user should be able to:

- fix axes
- filter axes
- keep some axes visible
- reorder visible axes
- reduce over one or more axes
- compute best coordinates
- feed those best coordinates back into the study

## Reduction API

### One axis

```dice
sum(damage, "PLAN")
mean(damage, "SEED")
max(damage, "PLAN")
argmax(damage, "PLAN")
```

### Multiple axes

```dice
sum(damage, ("PLAN", "LEVEL"))
mean(damage, ("SEED", "LEVEL"))
max(damage, ("PLAN", "LEVEL"))
argmax(damage, ("PLAN", "LEVEL"))
```

### All axes

```dice
sum(damage)
mean(damage)
max(damage)
argmax(damage)
```

This means:

- if `axes` is omitted, reduce across every sweep axis
- if `axes` is given, reduce only those axes

This makes `total(...)` largely redundant.
It can survive as a compatibility helper if needed, but the clearer long-term surface is `sum(value, axes?)`.

## What Each Reducer Returns

### `sum`, `mean`, `max`

These return ordinary reduced cell values.

If `damage` is:

```text
PLAN x AC x LEVEL x SEED -> number
```

then:

```dice
mean(damage, ("SEED", "LEVEL"))
```

returns:

```text
PLAN x AC -> number
```

### `argmax` over one axis

```dice
argmax(damage, "PLAN")
```

returns:

```text
AC x LEVEL x SEED -> PLAN coordinate/value
```

In practice the cell values would look like:

```dice
(PLAN: "great_weapon_master")
```

not just the bare string.

That matters because the result can then be fed directly back into indexing.

### `argmax` over multiple axes

```dice
argmax(damage, ("PLAN", "LEVEL"))
```

returns:

```text
AC x SEED -> coordinate
```

with cell values like:

```dice
(PLAN: "great_weapon_master", LEVEL: 11)
```

This is the main reason records are valuable: multi-axis `argmax` naturally returns a coordinate record rather than an ad hoc special type.

## Bracket Semantics

`expr[...]` takes a comma-separated list of selector clauses.

Each clause may be:

- an axis ref
- a coordinate entry
- an axis spec value
- a coordinate value
- a filter clause

Examples:

```dice
damage["AC", "PLAN"]
damage[LEVEL: 11, "AC"]
damage[(PLAN: "great_weapon_master", LEVEL: 11)]
damage[("AC", "LEVEL")]
damage[(PLAN: "great_weapon_master"), ("AC", "LEVEL")]
damage[best_coord]
damage[best_coord, keep_axes]
damage[AC in {12, 16, 20}, "PLAN"]
```

There is no separate `[()]` wrapper feature.
Ordinary tuples and records simply appear inside `[]` like any other value.

## Clause Meanings

### Axis ref clause

An axis ref means "keep this axis visible".

Examples:

```dice
damage["AC"]
damage[0]
damage["AC", "PLAN"]
```

### Coordinate entry clause

A coordinate entry fixes an axis to one value and removes that axis from the result.

Examples:

```dice
damage[LEVEL: 11]
damage[PLAN: "great_weapon_master", LEVEL: 11]
damage[0: 5, 1: 10]
```

### Axis spec value clause

An axis spec value expands into several axis ref clauses.

Examples:

```dice
keep_axes = ("AC", "PLAN")

damage[keep_axes]
damage[LEVEL: 11, keep_axes]
```

### Coordinate value clause

A coordinate value expands into several coordinate entry clauses.

Examples:

```dice
focus = (PLAN: "great_weapon_master", LEVEL: 11)

damage[focus]
damage[focus, "AC"]
```

### Filter clause

Filters keep an axis but shrink its domain.

Examples:

```dice
damage[AC in {12, 16, 20}]
damage[PLAN in {"longsword", "great_weapon_master"}]
damage[LEVEL in {5, 11}, "PLAN", "AC"]
```

This document keeps filter clauses as direct syntax for now.
They could later become first-class values too, but that is not required for the core indexing model.

## Default Keep Rule

The most workable rule seems to be:

- if no axis ref or axis spec clauses appear, keep all unfixed axes in their original order
- if any axis ref or axis spec clauses appear, keep exactly those axes in that order

So:

```dice
damage[LEVEL: 11]
```

means:

```text
keep PLAN x AC x SEED
```

while:

```dice
damage[LEVEL: 11, "AC", "PLAN"]
```

means:

```text
keep exactly AC x PLAN
```

and drop `SEED`.

## Basic Examples

### Fix one axis

```dice
damage[LEVEL: 11]
```

Shape:

```text
PLAN x AC x SEED
```

### Fix two axes

```dice
damage[PLAN: "great_weapon_master", LEVEL: 11]
```

Shape:

```text
AC x SEED
```

### Fix everything

```dice
damage[PLAN: "great_weapon_master", AC: 16, LEVEL: 11, SEED: 7]
```

Shape:

```text
unswept scalar or distribution
```

### Keep only the axes you want to see

```dice
damage[LEVEL: 11, "AC", "PLAN"]
```

Shape:

```text
AC x PLAN
```

### Reorder visible axes

```dice
damage[LEVEL: 11, "PLAN", "AC"]
```

Shape:

```text
PLAN x AC
```

## Variable-Driven Examples

This is one of the main goals of the design.

### Reuse an axis spec

```dice
table_axes = ("AC", "PLAN")
damage[LEVEL: 11, table_axes]
```

### Reuse a coordinate

```dice
boss_case = (PLAN: "great_weapon_master", LEVEL: 11)
damage[boss_case]
damage[boss_case, "AC"]
```

### Reuse both together

```dice
focus = (PLAN: "great_weapon_master", LEVEL: 11)
keep_axes = ("AC", "SEED")

damage[focus, keep_axes]
```

### Use positional and named selectors together

```dice
coord = (0: "great_weapon_master", LEVEL: 11)
axes = (1, "SEED")

damage[coord, axes]
```

This assumes positional refs use the current axis order at the point where indexing happens.

## Multidimensional Reduction Examples

### Sum away nuisance axes

```dice
sum(damage, ("SEED", "LEVEL"))
```

Shape:

```text
PLAN x AC
```

### Mean over simulation seed, then inspect one plan

```dice
mean(damage, "SEED")[PLAN: "great_weapon_master", "AC", "LEVEL"]
```

Shape:

```text
AC x LEVEL
```

### Reduce all axes

```dice
sum(damage)
```

Shape:

```text
unswept scalar or distribution
```

### Reduce after slicing

```dice
max(
    damage[
        PLAN in {"longsword", "great_weapon_master", "hunters_mark_longbow"},
        LEVEL in {5, 11, 17}
    ],
    ("PLAN", "LEVEL")
)
```

Shape:

```text
AC x SEED
```

## Single-Axis Best-Choice Examples

### Best plan at each AC, LEVEL, SEED

```dice
best_plan = argmax(damage, "PLAN")
```

Shape:

```text
AC x LEVEL x SEED -> (PLAN: ...)
```

### Gather the winning values back out

```dice
best_damage = damage[best_plan]
```

Shape:

```text
AC x LEVEL x SEED
```

### Best plan at one level only

```dice
best_plan_11 = argmax(damage[LEVEL: 11], "PLAN")
best_damage_11 = damage[LEVEL: 11, best_plan_11, "AC"]
```

Shapes:

```text
best_plan_11   : AC x SEED -> (PLAN: ...)
best_damage_11 : AC
```

The second example uses the explicit keep rule to drop `SEED`.

## Multi-Axis Best-Choice Examples

### Best `(PLAN, LEVEL)` pair at each AC and SEED

```dice
best_choice = argmax(damage, ("PLAN", "LEVEL"))
```

Shape:

```text
AC x SEED -> (PLAN: ..., LEVEL: ...)
```

### Gather the corresponding values

```dice
best_damage = damage[best_choice]
```

Shape:

```text
AC x SEED
```

### Gather and then keep only AC

```dice
damage[best_choice, "AC"]
```

Shape:

```text
AC
```

### Restrict candidates before choosing

```dice
martial_only = damage[
    PLAN in {"longsword", "great_weapon_master", "hunters_mark_longbow"}
]

best_martial = argmax(martial_only, ("PLAN", "LEVEL"))
martial_value = martial_only[best_martial]
```

This is one of the strongest arguments for the whole model: adaptive strategies become ordinary study transformations rather than special syntax.

## Four-Dimensional Workflow Examples

### Build a 2D table from a 4D study

```dice
damage[
    (PLAN: "great_weapon_master", SEED: 0),
    ("AC", "LEVEL")
]
```

Shape:

```text
AC x LEVEL
```

### Build a 1D AC curve from a 4D study

```dice
damage[
    (PLAN: "great_weapon_master", LEVEL: 11),
    "AC"
]
```

Shape:

```text
AC
```

### Average out SEED, then choose the best plan and level

```dice
mean_damage = mean(damage, "SEED")
best_choice = argmax(mean_damage, ("PLAN", "LEVEL"))
best_curve = mean_damage[best_choice, "AC"]
```

Shapes:

```text
mean_damage : PLAN x AC x LEVEL
best_choice : AC -> (PLAN: ..., LEVEL: ...)
best_curve  : AC
```

## Comparison Examples

Once the gather story exists, comparison studies become much stronger.

```dice
best_plan = argmax(damage, "PLAN")
best_damage = damage[best_plan]
gwm = damage[PLAN: "great_weapon_master"]
```

Now compare an adaptive strategy against a fixed strategy:

```dice
render(
    mean(best_damage, "SEED")[LEVEL: 11, "AC"], "Best plan",
    mean(gwm, "SEED")[LEVEL: 11, "AC"], "Always GWM",
    "Armor class",
    "Adaptive best plan versus fixed GWM at level 11"
)
```

## Semantic Guardrails

These examples imply a few important constraints:

- Duplicate axis references inside one reducer or index expression are errors.
- Positional refs use the current axis order, not some remembered original order.
- `expr[coord]` requires the coordinate keys to refer to axes that actually exist in `expr`.
- `expr[coord]` requires coordinate values to be present in the corresponding axis domains.
- `expr[argmax(...)]` works because `argmax` returns coordinate records.
- If any explicit keep axes are mentioned, only those axes remain visible.
- Filter clauses should preserve the original axis order, not reorder to match literal order.
- `sum(value)` and friends should fail clearly if reducing all axes does not make semantic sense for the cell type.

## Open Questions

- Should `argmax(value, "PLAN")` return `(PLAN: "...")` or the bare axis value `"..."`?
  This document assumes the record form because it composes better with `[]`.
  Answer: User record form.
- Do we want a first-class filter value type later, analogous to axis specs and coordinates?
  Answer: No
- Should records preserve insertion order for display only, or should order matter semantically anywhere?
  Answer: Preserve order internally. Note in the implementation but don't yet promise in docs. Keep as internal contract for now.
- Do we want tuple/record field access immediately, or can structured values stay mostly opaque at first?
  Answer: Immediately.

## Takeaway

The most coherent story now looks like this:

- tuples and records become first-class values
- axis specs and coordinates are ordinary values
- reducers take `value` first and optional `axes` second
- `[]` accepts mixed axis refs, coordinates, axis specs, coordinate values, and filters
- `argmax` over multiple axes returns coordinate records
- those coordinate records can be fed straight back into indexing

That is strong enough to express:

- ordinary slicing
- multidimensional substudies
- axis reordering
- multi-axis reduction
- multi-axis `argmax`
- gather-style lookup
- adaptive-versus-fixed strategy comparisons
