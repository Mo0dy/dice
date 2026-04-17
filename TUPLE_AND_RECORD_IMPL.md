# Tuple And Record Brainstorm

This document explores syntax and semantics for first-class tuples and records in `dice`.
It is upstream of the sweep-indexing work described in [SWEEP_INDEXING.md](SWEEP_INDEXING.md).

## Implemented V1 Decisions

- tuples use Python-like construction:
  - `()` empty tuple
  - `(x)` grouping only
  - `(x,)` one-element tuple
  - `(x, y, z)` multi-element tuple
- records use `(KEY: value, ...)`
- record keys are identifiers or integers only in v1
- empty records are not supported in v1
- mixed tuple/record literals such as `(1, PLAN: 11)` are rejected
- duplicate record keys are rejected
- tuples and records are first-class runtime values and can appear anywhere ordinary values can
- CLI and JSON preserve record entry order
- tuple/record comparison operators are not supported in DSL v1
- field access is intentionally deferred to the next phase

The goal is not just "support container literals".
The deeper goal is to give the language a small structured-value layer that can support:

- mixed named/positional axis specs
- coordinate values returned by `argmax(...)`
- variable-driven sweep indexing like `study[coord, axes]`
- future richer standard-library APIs without inventing ad hoc syntax per feature

## Why Add Them

The immediate use case is sweep work:

- tuples express axis specs like `("PLAN", "LEVEL")`
- records express coordinates like `(PLAN: "great_weapon_master", LEVEL: 11)`
- reducers can take axis specs as ordinary values
- `[]` can consume coordinates and axis specs stored in variables

That by itself is already strong enough to justify the feature.
Records may also help later with:

- more structured function results
- richer diagnostics
- standard-library helpers that return more than one value
- plotting and reporting metadata

Related design note: [SWEEP_INDEXING.md](SWEEP_INDEXING.md)

## Existing Syntax Pressure

The current language already uses the relevant tokens heavily:

- `(...)` is grouping and function-call syntax
- `:` is used in:
  - function definitions: `f(x): ...`
  - sweep literals: `[AC:10..20]`
- `=` is used in:
  - assignments: `x = ...`
  - keyword arguments: `f(level=11)`

So the tuple/record design must avoid creating parse ambiguities around:

- parenthesized expressions versus tuples
- parenthesized expressions versus records
- record entries versus function definition syntax
- tuple literals versus function argument lists

The good news is that these collisions are manageable because tuple/record literals only need to exist in expression position.

## Design Goals

- Keep the syntax small and unsurprising.
- Reuse familiar tuple/record notation.
- Preserve ordinary parenthesized grouping.
- Allow records to mix integer and string-like axis refs as keys.
- Make tuple and record values first-class at runtime.
- Do not require field access or destructuring in the first version.
- Be strong enough to support [SWEEP_INDEXING.md](SWEEP_INDEXING.md) cleanly.

## Proposed Literal Syntax

### Tuples

Examples:

```dice
()
(1,)
(1, 2)
("AC", "PLAN")
((1, 2), ("AC", "PLAN"))
```

Rules:

- `()` is the empty tuple.
- `(x,)` is a one-element tuple.
- `(x, y, z)` is a multi-element tuple.
- `(x)` remains ordinary grouping, not a tuple.

This matches Python and keeps the grouping story clear.

### Records

Examples:

```dice
(AC: 16)
(PLAN: "great_weapon_master", LEVEL: 11)
(0: 5, 1: 10)
(kind: "line", title: "Damage vs AC")
```

Rules:

- a parenthesized comma-separated list with at least one `key: value` entry is a record literal
- record keys can be identifiers or integer literals in the first version
- records may contain one or more entries
- record entry order is preserved for display, though the semantic lookup is keyed

This gives the axis/coordinate surface directly:

```dice
(PLAN: "great_weapon_master", LEVEL: 11)
(0: 5, 1: 10, AC: 3)
```

## Basic Parsing Rule

The parser can likely treat `(` as:

1. parse the first expression-like item
2. inspect the next token
3. decide between:
   - grouped expression
   - tuple literal
   - record literal

Conceptually:

- `(` `expr` `)` => grouped expression
- `(` `expr` `,` ... `)` => tuple
- `(` `key` `:` `expr` ... `)` => record

That keeps the decision local and avoids statement-level ambiguity.

## Candidate Key Syntax

There are three obvious options for record keys.

### Option A: identifier or integer keys only

```dice
(PLAN: "gwm", LEVEL: 11)
(0: 5, 1: 10)
```

Pros:

- compact
- ideal for sweep coordinates
- easy to read

Cons:

- keys are not arbitrary expressions
- `"PLAN": ...` would not be legal unless explicitly added

### Option B: arbitrary expression keys

```dice
("PLAN": "gwm", ("LEVEL"): 11, 0: 5)
```

Pros:

- very general

Cons:

- much harder to parse and explain
- weakens readability
- not needed for the sweep use case

### Option C: two syntaxes, bare and explicit

```dice
(PLAN: "gwm", LEVEL: 11)
(key("PLAN"): "gwm")
```

Pros:

- leaves room for future expansion

Cons:

- more language surface immediately

Current recommendation:

- start with Option A
- allow identifier keys and integer keys only
- consider string/expression keys later only if a real need appears

## Runtime Model

### Tuple value

A tuple is an ordered immutable sequence of runtime values.

Examples:

```text
()
(1,)
(1, 2)
("AC", "PLAN")
```

Likely properties:

- preserves order
- allows nested tuples/records
- equality is structural

### Record value

A record is an immutable keyed mapping from keys to runtime values.

Examples:

```text
(PLAN: "gwm", LEVEL: 11)
(0: 5, 1: 10)
```

Likely properties:

- keyed lookup semantics
- no duplicate keys
- preserves insertion order for printing
- equality is structural by keys and values

## Minimal v1 Semantics

The first version does not need full "data language" power.
It only needs enough behavior to be useful and stable.

Recommended v1:

- literal creation
- passing tuples/records to functions
- storing them in variables
- returning them from functions
- printing them in CLI/JSON output
- structural equality
- consumption by sweep APIs

Recommended to defer:

- field access like `record.PLAN`
- index access like `tuple[0]`
- destructuring assignment
- record merge/update
- tuple/list comprehensions or higher-order data operations

This keeps the feature small enough to implement without accidentally turning `dice` into a general-purpose host language.

## Equality And Comparison

At minimum:

```dice
(1, 2) == (1, 2)
(PLAN: "gwm") == (PLAN: "gwm")
```

should work.

Questions:

- Should tuple/record ordering matter for equality?
  - tuple: yes
  - record: probably key-based equality, regardless of written order
- Should `<`, `>`, `in`, arithmetic, or dice operators accept them?
  - probably no in v1
- Should they be valid finite-measure outcomes?
  - probably yes, if the runtime already supports arbitrary hashable-like outcomes

Allowing them as measure/distribution outcomes could be surprisingly useful later.

## Suggested String Representations

Readable display matters because these values may appear in:

- REPL output
- error messages
- `argmax(...)` results
- JSON mode

Suggested text forms:

```text
()
(1,)
(1, 2)
(PLAN: "gwm", LEVEL: 11)
(0: 5, 1: 10, AC: 3)
```

Suggested JSON shape:

- tuple: array-like with a distinct top-level tag, or plain arrays if acceptable
- record: object-like with preserved key spelling, but integer keys need a clear encoding

This will matter for interoperability if tuples/records are returned from `--json`.

## Interaction With Functions

### Passing structured values

These should work naturally:

```dice
axes = ("PLAN", "LEVEL")
coord = (PLAN: "great_weapon_master", LEVEL: 11)

sum(damage, axes)
damage[coord, "AC"]
```

### Returning structured values

These should also be possible:

```dice
best = argmax(damage, ("PLAN", "LEVEL"))
```

where each cell value is a record.

### Function definitions

There is no need to add tuple/record parameters specially in v1.

This should already be enough:

```dice
pick(study, coord, axes): study[coord, axes]
```

The runtime just treats `coord` and `axes` as ordinary values.

## Interaction With Sweep APIs

This is the main downstream consumer.

From [SWEEP_INDEXING.md](SWEEP_INDEXING.md):

```dice
sum(damage, ("PLAN", "LEVEL"))
argmax(damage, ("PLAN", "LEVEL"))

focus = (PLAN: "great_weapon_master", LEVEL: 11)
keep_axes = ("AC", "SEED")

damage[focus, keep_axes]
```

Without tuples/records, those APIs need custom syntax.
With tuples/records, the whole sweep feature set becomes ordinary structured-value plumbing.

## Ambiguity Examples

These cases need deliberate rules.

### Grouping versus tuple

```dice
(x)
(x,)
(x, y)
```

Recommendation:

- `(x)` is grouping
- `(x,)` is one-element tuple
- `(x, y)` is tuple

### Grouping versus record

```dice
(PLAN: 11)
```

Recommendation:

- if the parser sees `ID COLON` or `INTEGER COLON` immediately inside `(`, parse a record

### Call arguments versus tuple literals

```dice
f((1, 2))
f((PLAN: "gwm", LEVEL: 11))
```

These should be fine because the tuple/record literal lives inside expression position as one argument.

### Function definition versus record literal

```dice
f(x): x + 1
(PLAN: 11)
```

These should not collide because function definition syntax only exists in top-level statement position after `ID LPAREN ... RPAREN COLON`.

## Duplicate Keys And Invalid Shapes

Recommended errors:

- duplicate record keys are errors:

```dice
(PLAN: "gwm", PLAN: "longbow")
```

- mixed tuple/record entries in one literal are errors:

```dice
(1, PLAN: "gwm")
```

That second rule is important.
Allowing mixed tuple and record entry syntax in one literal would make the surface harder to reason about and complicate parsing for little gain.

## Open Syntax Questions

### Should empty records exist?

Possible spellings:

- impossible in v1
- `(:)`
- `record()`

My current inclination:

- no empty record literal in v1
- tuples get `()`
- records must have at least one entry

The sweep use cases do not need empty records.

### Should string keys be allowed?

Possible spellings:

```dice
("PLAN": "gwm")
```

This could be useful eventually, but it adds parser and semantic complexity early.
I would defer it unless another feature clearly needs it.

### Should record keys allow floats or arbitrary expressions?

Probably not.
Identifier and integer keys are enough for coordinates and many metadata cases.

## Open Semantic Questions

- Should records be valid distribution outcomes?
- Should records compare equal regardless of entry order?
- Should CLI/JSON printing preserve original key order or canonicalize it?
- Should tuples/records be allowed in sets/measures immediately?
- Do we want field access soon after v1, or can records stay opaque for a while?

## Recommended v1 Shape

If the goal is to begin implementation without overcommitting, the smallest solid version is:

- tuple literals:
  - `()`
  - `(x,)`
  - `(x, y, z)`
- record literals:
  - `(PLAN: "gwm")`
  - `(PLAN: "gwm", LEVEL: 11)`
  - `(0: 5, 1: 10)`
- grouped expressions remain `(expr)`
- tuple/record values are immutable and first-class
- identifier and integer keys only
- duplicate record keys are errors
- mixed tuple/record entry forms are errors
- no field access or destructuring yet
- sweep APIs consume these values directly

That is enough to unlock the multidimensional indexing design in [SWEEP_INDEXING.md](SWEEP_INDEXING.md) without making the language surface explode.
