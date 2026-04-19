# Performance Improvement Through Hashing

This note captures a possible performance direction for the exact engine:

- perform a cleanup pass on builtin-function structure
- move more pure builtin functions onto a common `@dicefunction` path
- add opt-in memoization such as `@dicefunction(cache=True)`
- rely on immutable runtime values to make structural hashing practical
- use that cache to cut repeated exact work across sweeps and repeated convolution

This is not an implementation plan yet. It is a design note for a likely optimization seam.

## Motivation

The current exact profile suggests two different classes of cost:

- Algorithmic cost:
  repeated exact combination work, especially around `repeat_sum_with`, `add`, and sweep lifting.
- Low-level cost:
  repeated canonicalization, numeric pairwise loops, and guard checks.

These costs interact. If the engine recomputes the same pure exact subproblem many times across a multidimensional sweep, then even a low-level-optimized implementation still wastes work.

Hash-based memoization is interesting because it addresses recomputation directly.

There is also an important specialized optimization seam alongside hashing:

- a fast path for integer-valued distributions

Many tabletop and dice workloads spend most of their time on distributions whose support is entirely integer-valued, often over fairly compact ranges. Those cases are much more structured than the general runtime value model, and they open the door to specialized convolution algorithms.

## Builtin Function Cleanup

Part of this rewrite should be a cleaner separation of builtin functions.

The current builtin surface is split between:

- exact semantic helpers in `diceengine.py`
- exported builtin registration and wrappers in `executor.py`
- backend-specific overrides in alternate executors

The intended cleanup direction is:

- implement all applicable builtin functions through the `@dicefunction` decorator
- let that decorator handle common lifting and, later, optional caching
- reduce the amount of wrapper boilerplate currently living in `executor.py`

This should be done for all functions where it is semantically appropriate.

In practice, that means:

- pure exact builtin operations should move toward the decorated function path
- the executor should still retain special setup/stateful functions

Examples of executor-retained functionality likely include:

- render/config/setup helpers
- report-building helpers
- backend-specific behavior that is not just the exact pure function surface

So this is not a proposal to eliminate the executor. It is a proposal to narrow the executor to the parts that genuinely need to stay there, while moving applicable builtin semantics onto the shared decorated path.

## Core Idea

Many `diceengine.py` runtime values are effectively immutable:

- `FiniteMeasure`
- `Distribution`
- `Sweep`
- tuple/record runtime values

Because of that, pure exact functions should be candidates for memoization.

The ideal user-facing shape would be something like:

```python
@dicefunction(cache=True)
def add(left, right):
    ...
```

The cache key would be based on:

- function identity
- positional arguments
- normalized keyword arguments if relevant

This would let the runtime reuse exact results for repeated calls with equal arguments.

## Why This Fits The Current Engine

The exact engine performs many structurally repeated computations:

- binary distribution combination
- repeated summation / convolution
- comparisons on identical distributions
- the same pure function evaluated across sweep cells where only some axes matter

The current evaluation model is eager and cell-oriented, which makes repeated work more likely:

- `_lift_cellwise(...)` enumerates full coordinates
- each cell then re-evaluates pure exact operations
- many of those operations may have identical arguments across different cells

Memoization is a clean first step before deeper dependency-aware sweep evaluation.

## Relationship To `repeat_sum_with`

`repeat_sum_with(...)` is the clearest immediate example.

Today it repeatedly builds sums via:

```python
repeated = 0
for _ in range(count_outcome):
    repeated = add_function(repeated, value)
```

That creates two opportunities:

1. Recursive repeated sum

Define repeated summation recursively instead of by linear chaining from zero every time.

The important idea is not naive recursion, but divide-and-conquer:

- `sum^0 = 0`
- `sum^1 = value`
- if `n` is even, compute `half = sum^(n/2)` and combine `half` with itself
- if `n` is odd, reduce to a smaller repeated sum plus one more `value`

This gives a much better structure for reuse.

2. Cache repeated subproblems

If repeated sums are recursive and cached, then:

- `repeat_sum(value, 8)` can reuse `repeat_sum(value, 4)`
- `repeat_sum(value, 9)` can reuse `repeat_sum(value, 8)`
- repeated counts across sweep cells can reuse the same exact result

This is likely much better than recomputing each count from scratch.

## Fast Path For Integer Distributions

In addition to caching, the exact engine should likely have a specialized fast path for integer-valued distributions.

Why this matters:

- many important dice workloads are integer-valued
- sums of independent integer-valued random variables are exactly discrete convolutions
- repeated sums are repeated convolutions / powers of a probability generating function

This is a standard and well-studied problem family.

Relevant standard ideas:

- direct discrete convolution for smaller or sparse supports
- repeated convolution by binary exponentiation / repeated squaring
- FFT-based convolution for larger dense supports

So for a deterministic integer count and an integer-valued distribution, `repeat_sum(...)` should not necessarily flow through the most generic engine path.

Instead, the engine should eventually recognize a case like:

- count is a deterministic non-negative integer
- value is a plain integer-valued `Distribution`
- operator is ordinary numeric addition

and use a dedicated repeated-convolution implementation.

This fast path is narrower than the full runtime model, but that is acceptable. It is meant to accelerate the common arithmetic-distribution case, not replace the general semantics.

## Relationship Between Hashing And Integer Fast Paths

These ideas reinforce each other.

- Hashing/memoization helps avoid recomputing identical exact subproblems.
- Integer fast paths reduce the cost of the subproblems that still need to be computed.

For example:

- a cached `repeat_sum(value, 8)` result can be reused across cells
- the first computation of that result can itself be much cheaper if it uses repeated convolution by squaring instead of the generic repeated-add path

So the likely long-term picture is:

- generic exact semantics remain available for all supported runtime values
- memoization cuts repeated work across those semantics
- specialized integer-distribution algorithms accelerate the most common exact arithmetic workloads

## Why Hashing Matters

Caching only works well if the runtime values can be compared and hashed efficiently.

The good news is:

- most core value objects are frozen
- distributions already normalize to canonical entry tuples
- sweeps and tuple/record values are also close to structural values

So structural hashing appears realistic.

The required work is likely:

- verify hashability and equality of core runtime objects
- ensure all relevant nested payloads are also hashable or normalized
- avoid expensive ad hoc key construction in hot paths

## What This Does Not Yet Require

It does not immediately require a global distribution interning store.

That stronger design would look like:

- constructing a distribution goes through a canonical store
- if an identical distribution already exists, return that same object
- identity checks then become extremely cheap

This is attractive long-term, but it is a larger architectural step and should probably not be the first optimization.

For now, structural hashing plus memoization is the smaller and safer step.

## Likely Scope For `cache=True`

This should only apply to pure exact functions.

Good candidates:

- `add`
- `sub`
- `mul`
- `div`
- comparisons
- `repeat_sum`
- other exact pure transforms

Bad candidates:

- `sample`
- report/render/config helpers
- anything stateful
- anything backend-specific where cached exact results would conflict with direct sampling behavior

So the feature should be opt-in, not global.

## Broader Architectural Direction

This idea also supports a cleaner builtin design.

Possible direction:

- more pure builtin functions are defined as decorated exported functions
- all applicable builtins are moved onto that path
- the executor auto-registers those functions
- alternate backends override only the subset that truly differs semantically
- executor-only setup/stateful helpers remain in the executor

That would separate:

- exact pure semantics
- registration/export
- backend-specific behavior

more cleanly than the current wrapper-heavy structure.

## Expected Benefits

If this works well, it should help in several ways:

- cut repeated exact work across sweep cells
- make recursive repeated-sum evaluation viable
- reduce recomputation of identical convolutions and comparisons
- create a reusable optimization mechanism rather than one-off special cases

It does not replace low-level optimization. Functions like:

- `_canonicalize_weighted_entries`
- `_pairwise_numeric`

may still need direct improvement.

But memoization through hashing could remove a large amount of repeated work before those low-level optimizations are even attempted.

## Open Questions

- Which runtime objects need custom `__hash__` / `__eq__` implementations, if any?
- Are there any non-hashable payloads currently flowing through distributions or sweeps?
- Should the cache live at the decorator layer, executor layer, or inside specific engine functions?
- How should cached functions interact with sweep lifting?
- Should recursive `repeat_sum` use divide-and-conquer directly, or should there first be a more general cached convolution primitive?

## Current Conclusion

The most promising medium-sized performance idea so far is:

1. move more pure exact builtins toward a shared decorated function path
2. add opt-in memoization such as `cache=True`
3. rely on immutable structural runtime values for cache keys
4. redefine repeated summation recursively so cached subproblems can be reused

This is likely a better first architectural move than adding a global distribution store immediately.
