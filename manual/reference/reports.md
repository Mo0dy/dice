# Reports

## Intention

The report surface turns exact results into charts and report layouts.

The mental model is stateful:

- build chart specs with `r_*`
- append them to the pending report
- call `render(...)` to flush the report and reset state

This is meant for analysis scripts rather than for single expressions typed at the REPL.

## Exact semantics

The report state and chart spec types live in `diceengine.py`. Report planning and concrete rendering live in `viewer.py`. The executor exposes the public `r_*` helpers in `executor.py`.

Important rules:

- `r_auto`, `r_dist`, `r_cdf`, and `r_surv` build chart specs from one expression
- `r_compare`, `r_diff`, and `r_best` build multi-series or strategy charts
- bare top-level chart specs auto-append to the pending report
- `r_title`, `r_note`, `r_hero`, `r_row`, `r_wide`, and `r_narrow` shape the pending report
- `render(path=..., format="png", dpi=...)` flushes the pending report and resets report state
- calling `render()` without pending report items is an error
- duplicate `r_title(...)` and duplicate `r_hero(...)` calls in the same pending report are rejected

Current planner coverage includes:

- unswept distributions
- one-axis scalar sweeps
- one-axis distribution sweeps
- two-axis scalar heatmaps
- labeled scalar and distribution comparisons
- strategy winner and margin views for suitable two-axis scalar sweeps

> Pitfall: a chart assigned to a variable does not auto-append until it is evaluated as a top-level statement or placed into a layout helper.

## Examples

Single chart:

```dice
r_title("d20")
r_auto(d20, x="Outcome")
render()
```

Distribution and CDF in one row:

```dice
r_title("Distributions")
r_row(r_dist(d20, x="Outcome", title="d20"), r_cdf(d20, x="Outcome", title="CDF"))
render()
```

Comparison plus delta:

```dice
r_title("Hit chance")
r_hero(r_compare(("Normal", ~(d20 >= [AC:10..18] -> 5 | 0)), ("Boosted", ~(d20 + 1 >= [AC:10..18] -> 5 | 0)), x="Armor class", y="Expected damage"))
r_wide(r_diff(("Boosted", ~(d20 + 1 >= [AC:10..18] -> 5 | 0)), ("Normal", ~(d20 >= [AC:10..18] -> 5 | 0)), x="Armor class", y="Expected damage delta"))
render()
```

Two separate reports in one program:

```dice
r_title("First")
r_auto(d20)
render()
r_title("Second")
r_auto(d6)
render()
```
