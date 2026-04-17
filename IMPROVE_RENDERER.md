# Improve Renderer

## Aim

Make graphics a first-class target of `dice`.

The target is not "expose Matplotlib from the DSL". The target is:

- beautiful results with almost no configuration
- strong defaults for common tabletop analysis
- a small amount of layout control for report-like output
- a clean Python escape hatch when users want exact control
- deterministic enough behavior to test and document

That implies a renderer that is more semantic than the current one, but still much narrower than a full plotting library.


## What The Current Sample Set Actually Wants

The sample library is already a good product spec. It is fairly consistent.

Most real sample use falls into six buckets:

1. one exact distribution
2. one probability sweep across a threshold
3. one expected-value sweep across a numeric axis
4. several plans compared across one numeric axis
5. a plan-by-condition matrix
6. a multi-chart narrative report around one scenario

That is a strong signal. The renderer should optimize for those cases first.

### Sample-by-sample reading

| Sample | User question | Perfect-world output |
| --- | --- | --- |
| `ability_scores_4d6h3.dice` | "What does 4d6 drop lowest look like from several angles?" | One report page, not five disconnected figures. Hero exact PMF for one score, target-reach line, total modifier distribution, threshold plot, plus 2-3 text callouts. |
| `agonizing_eldritch_blast_vs_ac.dice` | "How do a few attack packages compare over AC?" | Clean multi-series line chart with direct labels and maybe a small delta panel vs baseline. |
| `cantrip_progression.dice` | "How do several plans scale over level?" | A progression chart with level on x, expected damage on y, direct labeling, and possibly endpoint labels instead of a legend. |
| `combat_profiles.dice` | "What do several full damage profiles look like?" | Not a five-series spaghetti overlay. Prefer faceted PMFs, small multiples, or a PMF plus summary stats / exceedance comparison. |
| `eldritch_blast_debug.dice` | "What is happening inside this spell package?" | A debugging report: hit-count PMF, single-beam PMFs, action-level PMF, and brief summary text. |
| `fireball_party_total.dice` | "How does total damage scale by slot?" | A simple hero line chart with slot labels and a readable headline expectation trend. |
| `greatsword_gwf_vs_ac.dice` / `hunters_mark_longbow_vs_ac.dice` | "Which package is better across AC?" | Multi-series line chart, plus optional delta-from-baseline mode. |
| `magic_missile_vs_slot.dice` | "How does one spell scale by slot?" | Single line or step chart with direct point labels. |
| `martial_tradeoffs.dice` / `spell_slot_showdown.dice` | "Compare many named plans over one axis." | Small multiples or labeled overlay for a few plans; automatic faceting or winner emphasis when the series count gets high. |
| `strategy_heatmap.dice` | "Which strategy wins under which conditions?" | Two-panel strategy report: winner map and winner-margin heatmap. Raw EV matrix is secondary. |

### The real product requirement behind the samples

In perfect-world `dice`, users should be able to ask:

- "show me the exact shape"
- "show me the chance to clear a threshold"
- "show me how this scales over AC / level / slot"
- "show me which option wins where"
- "turn this into a readable one-page report"

Those are the core rendering jobs.


## Current Renderer Reality

Today [viewer.py](/home/felix/_Documents/Projects/dice/viewer.py) is structurally smart, but semantically thin.

It currently chooses among a small shape-based set:

- `bar`
- `bar_scalar`
- `line`
- `heatmap_distribution`
- `heatmap_scalar`
- `compare_bar`
- `compare_line`
- `compare_probability_line`
- `compare_distribution_line`

That is a reasonable base, but it has clear limits:

- chart choice is driven mostly by runtime shape, not user intent
- full-distribution comparisons degrade into noisy overlays quickly
- there is no notion of "winner", "margin", "delta", or "headline plot"
- report composition does not exist
- styling is close to raw Matplotlib defaults
- wide supports and high-series-count comparisons do not have a graceful fallback

The biggest present mismatch is `compare_distribution_line`: it is technically generic, but it is not how a human wants to compare several full damage profiles.


## What We Should Want To See

### 1. Single exact distributions

For one exact PMF, the renderer should make it obvious:

- where the mass is concentrated
- what the mean / median / common outcomes are
- whether the support is narrow or broad

Preferred rendering:

- small discrete numeric support: bars or lollipops
- broader contiguous support: step / area / filled curve
- categorical support: ordered bars
- optional reference markers for mean, median, and interval

### 2. Threshold and cumulative questions

These appear repeatedly in the samples even when the code currently expresses them indirectly.

Preferred rendering:

- threshold sweep: line or step
- exact Bernoulli series: probability line with percent axis
- cumulative and survival views as first-class render modes, not user workarounds

### 3. Multi-series scalar sweeps

This is the core D&D workload.

Preferred rendering:

- 2 to 4 series: one shared chart, direct labels when possible
- 5 to 8 series: either a careful overlay or small multiples
- more than that: small multiples, winner summary, or delta vs selected baseline

Default behavior should avoid giant legends when direct labeling or faceting would read better.

### 4. Full distribution comparisons

This is the area where "shape only" heuristics are not enough.

Preferred rendering:

- 2 to 3 series: overlay may be acceptable
- 4+ series: facet by plan, or switch to summary comparison
- optional companion views: CDF, survival, exceedance at threshold, interval summary

For combat-option analysis, users often care less about the full PMF overlay than about:

- expected value
- variance / volatility
- chance to hit a target
- where one option overtakes another

### 5. Strategy matrices

The current `strategy_heatmap` sample is already pointing at a better product.

For plan-by-condition sweeps, the best default is usually not the raw scalar matrix.

Preferred rendering:

- winner identity map
- winner margin map
- raw value heatmap as a secondary view
- annotation only for small matrices

### 6. Reports

Several samples are obviously report-shaped, not single-chart-shaped.

Perfect-world output should support:

- one hero plot
- one or more supporting plots
- short captions or notes
- one or two compact tables or summary stats
- export as one coherent artifact

This matters especially for:

- `ability_scores_4d6h3.dice`
- `eldritch_blast_debug.dice`
- future "build guide" style analyses


## House Style Requirements

Creating nice graphics should be an explicit goal of `dice`, not an accidental side effect.

The default renderer needs a house style.

Minimum expectations:

- readable typography hierarchy
- restrained gridlines
- no noisy top/right spines
- colorblind-safe categorical palette
- good sequential and diverging colormaps
- percent-aware formatting
- direct labels where practical
- legends that do not dominate the figure
- sensible annotation rules
- figure sizes that match likely use: terminal popup, exported PNG, exported SVG

Visual semantics should be consistent:

- probabilities: one recognizable family
- scalar value comparisons: restrained categorical palette
- deltas: diverging palette centered at zero
- winners: categorical palette with strong legend treatment
- uncertainty / intervals: muted bands, not dominant fills


## What The DSL Should And Should Not Own

### The DSL should own

- semantic intent
- series names
- report structure at a high level
- a few high-level layout choices
- export target / format if needed

### The DSL should not own

- arbitrary colors per series
- manual subplot coordinates
- hand-tuned axis limits in normal use
- low-level legend placement
- per-mark styling knobs
- CSS-like layout control

The language should say what the user wants to show, not how every pixel is drawn.


## Adjacent Projects Worth Borrowing From

These are useful reference points, not direct templates.

- [AnyDice](https://anydice.com/docs/introduction/) is a strong domain precedent: one mechanic can be shown in multiple views, including normal, at least, at most, table, graph, and transposed comparison. `dice` should likely learn from that separation between data semantics and view.
- [Observable Plot](https://observablehq.com/plot/features/marks) is valuable because it is opinionated and keeps the surface small. It favors good defaults and layered composition over a giant options API.
- [Vega-Lite composition](https://vega.github.io/vega-lite/docs/composition.html) and [faceting](https://vega.github.io/vega-lite/docs/facet.html) are useful references for small-multiple thinking, multi-view composition, and separating semantic spec from backend rendering.
- [Quarto dashboards](https://quarto.org/docs/dashboards/layout.html) are relevant for report layout: cards, rows, columns, and a small number of layout concepts go a long way.

The broad pattern across all of them:

- semantic or opinionated plot requests work better than low-level plotting APIs
- multi-view composition matters
- layout benefits from a few strong primitives, not full freedom


## Multiple Viable Approaches

This is the part where the draft should stay open-minded. There are several credible paths.

### Approach A: Smarter `render(...)` only

Keep the public API almost unchanged and make the existing renderer much smarter.

What it means:

- improve chart-choice heuristics
- improve default styling
- add automatic small-multiple fallback
- infer more from axis names, series count, and result shape

Pros:

- lowest language complexity
- easiest migration path
- preserves the current quick-start feel

Cons:

- hard to express intent cleanly
- ambiguous cases stay ambiguous
- tests become more brittle if too much behavior depends on heuristics
- report composition is still missing unless `render(...)` becomes overloaded

Best use:

- a strong first phase, but probably not the whole story


### Approach B: Add a small family of semantic render intents

Keep `render(...)`, but add a narrow set of intent-oriented helpers.

Strong candidates:

- `renderdist(...)`
- `rendercdf(...)`
- `rendersurv(...)`
- `renderdiff(...)`
- `renderbest(...)`
- `rendersummary(...)`

What it means:

- the user can say "this is a distribution view" or "this is a delta view"
- the renderer still controls actual chart choice and style

Pros:

- cleaner semantics than pure heuristics
- still much smaller than a plotting DSL
- easier to test and document
- fits the existing language style well

Cons:

- expands the surface area
- some intents overlap and need clear definitions
- may still be incomplete without a report layer

Best use:

- likely the best next step for single-chart rendering


### Approach C: Introduce a narrow report/page surface

Treat single-chart rendering and report composition as separate jobs.

Possible public surface:

- `report(...)`
- `section("...", ...)`
- `note("...")`
- `table(...)`
- maybe `hero(...)` or `aside(...)`

Possible layout choices:

- single hero
- hero plus two supporting panels
- two-up
- small-multiples grid
- portrait vs landscape
- compact vs roomy

Pros:

- directly addresses the most obvious gap in the sample library
- turns several current multi-window programs into coherent outputs
- creates a path to good PNG / SVG / HTML exports

Cons:

- introduces genuine new language surface
- layout semantics need careful scoping
- could drift toward document markup if left unconstrained

Best use:

- probably necessary if "beautiful reports" is a real product goal


### Approach D: Internal spec-first renderer with backend adapters

Keep the public API small, but build a richer internal render/report spec.

That spec could capture:

- data shape
- semantic intent
- density class
- comparison mode
- scale semantics
- recommended presentation
- composition layout

Backends could then target:

- Matplotlib first
- HTML later
- maybe SVG-first export paths

Pros:

- clean separation between DSL and backend
- better tests
- enables several public APIs to share one rendering core
- makes future HTML output much more realistic

Cons:

- more upfront design work
- may feel abstract until the first backend fully benefits

Best use:

- very strong internal architecture, especially if reports are added


### Approach E: Keep the DSL thin and push most serious rendering to Python

This is the most conservative option.

What it means:

- improve `render(...)` a bit
- document Python helpers for anything sophisticated
- maybe ship a Python report helper library instead of a dice report DSL

Pros:

- smallest language footprint
- maximum flexibility for expert users
- simplest long-term boundary

Cons:

- misses the stated goal
- "beautiful reports are easy" would not actually be true
- users drop to Python too early for common, repeatable workflows

Best use:

- as the escape hatch, not as the main product story


## Recommendation

The strongest direction is a combination, not a single bet.

The intended goal should be:

- Approach A
- Approach B
- Approach C

Approach D is still useful, but only as much as A/B/C actually require in practice. We should not build a large speculative internal spec up front.

### Recommended near-term direction

Combine Approach A and Approach B:

- make the existing renderer noticeably more beautiful
- keep `render(...)` as the default quick path
- add a small number of semantic render intents for cases where heuristics are weak

This should cover:

- single PMFs
- CDF / survival views
- scalar sweeps
- delta-vs-baseline comparisons
- winner-oriented strategy plots

### Recommended medium-term direction

Layer Approach C and Approach D on top:

- add a narrow report surface
- add only the internal render/report spec needed to support the chosen public surface
- keep Matplotlib as the first backend
- preserve Python as the place for fully custom work

That gives `dice` three levels:

1. `render(...)` for quick results
2. semantic render helpers for clearer intent
3. reports for polished multi-view outputs

Python remains the fourth level when someone wants full control.

### Scope discipline for the internal spec

The internal render spec should be introduced incrementally.

For now the rule should be:

- add internal structure only when it simplifies A/B/C
- do not design for hypothetical backends before the current renderer needs it
- do not create a large abstract rendering model just because it looks architecturally clean

In other words:

- the public goal is smarter defaults, semantic render intents, and narrow reports
- the internal goal is only enough structure to make those work cleanly

That keeps the project focused on user-visible rendering wins rather than speculative renderer architecture.


## A Concrete Public Surface Worth Exploring

This is intentionally sketch-level, not a final API commitment.

### Single-chart surface

```dice
render(expr)
renderp(expr)
renderdist(expr)
rendercdf(expr)
rendersurv(expr)
renderdiff(a, "A", b, "B")
renderbest(expr)
rendersummary(expr)
```

Important point: these should express intent, not low-level style.

### Report surface

```dice
report(
    title("11th-level eldritch blast"),
    hero(renderdiff(agonizing, "Agonizing", plain, "Plain")),
    row(
        renderdist(plain_action),
        renderdist(hexed_action)
    ),
    note("Hex overtakes plain blast once multi-beam scaling matters.")
)
```

This kind of surface is probably enough:

- title
- section / row
- hero panel
- note / caption
- maybe compact table

It is not enough to become a full document language, which is good.


## Data-Shaping Helpers That Would Unlock Better Graphics

Some rendering improvements will require small semantic helpers rather than more plot knobs.

Strong candidates:

- `median(expr)`
- `quantile(expr, q)`
- `interval(expr, lo, hi)`
- `mode(expr)`
- `bucket(expr, width)` or `bin(expr, width)`
- `delta(a, b)`
- `ratio(a, b)`
- `argmax(expr)` or `best(expr)`
- `margin(expr)` for winner margin style reports

These help because they let users ask plot-friendly questions directly:

- show median and interval by level
- show uplift over baseline
- show winner by condition
- compress very wide supports into readable buckets


## Backends

Matplotlib is still a sensible primary backend.

Reasons:

- already integrated
- deterministic enough for tests
- solid static export story
- good enough for polished output if given a real house style

But the public design should avoid becoming "whatever Matplotlib happens to expose".

Longer term, an HTML-oriented backend could be worthwhile for:

- hover tooltips
- hide/show series
- zooming dense plots
- richer embedded reports

That only becomes attractive if there is already a backend-neutral internal render spec.


## How We Should Test Renderings And Reports

If graphics are a real product surface, they need real tests.

But "compare every PNG byte-for-byte" is the wrong strategy on its own. It is too brittle, and it does not tell us clearly what broke.

The right approach is layered.

### 1. Keep unit tests for render choice and semantic planning

This is the current style in [tests/test_render.py](/home/felix/_Documents/Projects/dice/tests/test_render.py), and it should stay.

Examples:

- this runtime shape chooses `line` vs `heatmap`
- this comparison chooses `diff` vs overlay
- this strategy matrix chooses winner-map mode
- this report request expands into hero-plus-secondary layout

These tests should validate the semantic render choice before any pixels are drawn.

### 2. Add structure tests on the rendered Matplotlib figure

After planning tests, the next layer should inspect the actual figure object rather than the final image file.

Examples:

- number of axes
- number of plotted series
- presence or absence of legend
- axis labels, titles, and subtitles
- colorbar existence for heatmaps
- annotation count rules
- report panel count and layout slots

This is more stable than image snapshots and catches many regressions directly.

### 3. Add curated golden-image tests for a small fixture set

For the most important visual cases, we should render deterministic fixture outputs and compare them against stored expected images.

This set should stay small and deliberate. It should cover:

- one exact PMF
- one probability sweep
- one multi-series scalar comparison
- one full-distribution comparison in its preferred display mode
- one strategy winner heatmap
- one representative report page

Important constraints:

- pin backend to `Agg`
- pin figure size, DPI, font family, and theme
- save images through one canonical export path
- compare with a small tolerance, not exact byte equality

This is the layer that answers: "did the chart still look like the intended chart?"

### 4. Snapshot report specs and layout manifests separately

For reports, image snapshots alone are not enough.

We should also serialize a small report manifest or spec that records things like:

- page kind
- panel count
- panel roles such as hero / secondary / table / note
- assigned chart intents
- titles and captions

That gives us a stable way to test report composition without making every layout change depend entirely on image diffs.

### 5. Use the existing sample library as render fixtures

The current D&D samples should become the main acceptance corpus for rendering.

That means:

- pick a subset of samples as official render fixtures
- render them through the canonical renderer
- store either figure snapshots, report manifests, or both

Best candidates:

- `samples/dnd/ability_scores_4d6h3.dice`
- `samples/dnd/agonizing_eldritch_blast_vs_ac.dice`
- `samples/dnd/combat_profiles.dice`
- `samples/dnd/eldritch_blast_debug.dice`
- `samples/dnd/strategy_heatmap.dice`

These already represent the product's most important visual stories.

### 6. Keep a manual gallery-generation workflow

Automated tests should protect the contract, but there should also be an easy way to regenerate a gallery for human review.

For example:

- render the curated fixtures into `tests/render_gallery/`
- produce one contact-sheet style index or HTML page
- review it when changing house style, layout heuristics, or report composition

This matters because "beautiful" is partly a human judgment. CI can catch regressions, but it cannot fully replace eyeballs.

### Recommended practical split

The most realistic testing stack for `dice` is:

1. semantic spec tests
2. figure structure tests
3. a small number of golden-image tests
4. report-manifest snapshots
5. manual gallery review for style changes

That gives us strong coverage without making renderer work miserable.

### Recommendation for initial implementation

Start small.

Phase 1 test support should be:

- extend unit tests from render kind selection into render-intent selection
- add figure-structure assertions for legends, colorbars, titles, and axis counts
- add a tiny golden-image fixture set for 3 to 6 canonical charts

Phase 2, once reports exist:

- snapshot report manifests
- add 1 to 2 golden report pages
- add a simple gallery-generation script for visual review

This is probably enough for me to reliably test renderings and reports while keeping the system maintainable.


## Things To Avoid

Avoid turning `dice` into a plotting package.

Specifically avoid:

- arbitrary styling dictionaries
- subplot coordinate systems
- dozens of optional keyword-like knobs
- per-series styling in ordinary dice code
- mixing semantic requests and low-level chart mechanics in one call

Those belong in Python.


## Practical Roadmap

### Phase 1: Make the current renderer respectable

- introduce a real house style
- improve figure sizing and export defaults
- improve legends, labels, and tick formatting
- handle high-series-count comparisons more gracefully

### Phase 2: Add semantic render intents

- add explicit distribution / CDF / survival / diff / best surfaces
- support delta and winner semantics cleanly
- add small-multiple fallback for cluttered comparisons

### Phase 3: Support strategy and summary views

- add `delta`, `interval`, `quantile`, `argmax`, `margin`, `bucket`
- make strategy winner maps and margin maps first-class outputs
- improve broad-support and high-density rendering

### Phase 4: Add reports

- add a narrow report surface
- support a few opinionated page layouts
- export coherent PNG / SVG artifacts
- keep HTML as a possible later extension, not a prerequisite


## Bottom Line

The sample library already tells us what the renderer should optimize for:

- exact PMFs
- probability and EV sweeps
- plan comparisons
- winner-by-condition analysis
- one-page narrative reports

The best overall direction is:

- smarter defaults
- a small semantic render family
- a narrow report surface
- Python for anything highly custom

That would make `dice` much better at its most important visual job: turning exact tabletop probability models into graphics that are both beautiful and actually useful.
