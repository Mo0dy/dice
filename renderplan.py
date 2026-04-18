#!/usr/bin/env python3

"""Backend-neutral render planning for dice charts and reports."""

from __future__ import annotations

from dataclasses import dataclass

from diceengine import (
    ChartSpec,
    PanelWidthClass,
    ReportBlock,
    ReportSpec,
    TupleValue,
    _coerce_to_distributions,
)


@dataclass(frozen=True)
class ChartRenderPlan:
    kind: str
    width_class: str
    payload: object
    x_label: str | None = None
    y_label: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class ReportRenderPlan:
    title: str | None
    hero: ChartRenderPlan | None
    rows: tuple[tuple[ChartRenderPlan, ...], ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class RenderOutcome:
    plan: object
    result: object
    output_path: str | None = None


def _is_scalar_distribution(distrib):
    items = list(distrib.items())
    return len(items) == 1 and items[0][1] == 1 and isinstance(items[0][0], (int, float))


def _all_scalar(result):
    return all(_is_scalar_distribution(distrib) for distrib in result.cells.values())


def _validate_series_entries(entries):
    normalized = []
    for entry in entries:
        if not isinstance(entry, TupleValue):
            raise Exception('comparison entries must be tuple literals like ("Label", value)')
        items = tuple(entry.items)
        if len(items) != 2:
            raise Exception("comparison entries must contain exactly two items")
        label, value = items
        if not isinstance(label, str):
            raise Exception("comparison entry labels must be strings")
        normalized.append((label, value))
    if len(normalized) < 2:
        raise Exception("comparisons require at least two labeled entries")
    return tuple(normalized)


def build_chart_plan(chart_spec):
    if not isinstance(chart_spec, ChartSpec):
        raise Exception("expected a chart spec")

    intent = chart_spec.intent
    payload = chart_spec.payload

    if intent in {"auto", "dist", "cdf", "surv", "best"}:
        result = _coerce_to_distributions(payload)
        width_class = PanelWidthClass.NARROW
        if intent == "best":
            width_class = PanelWidthClass.WIDE
            return ChartRenderPlan(
                "best_strategy",
                width_class,
                result,
                chart_spec.x_label,
                chart_spec.y_label,
                chart_spec.title,
            )
        if result.is_unswept():
            kind = "unswept_distribution" if intent in {"auto", "dist"} else intent
        elif len(result.axes) == 1:
            if _all_scalar(result):
                kind = "scalar_sweep"
            else:
                kind = "distribution_sweep"
                width_class = PanelWidthClass.WIDE
        elif len(result.axes) == 2 and _all_scalar(result):
            kind = "scalar_heatmap"
            width_class = PanelWidthClass.WIDE
        else:
            raise Exception("render does not support this result shape yet")
        if chart_spec.width_override is not None:
            width_class = chart_spec.width_override
        return ChartRenderPlan(
            kind,
            width_class,
            result,
            chart_spec.x_label,
            chart_spec.y_label,
            chart_spec.title,
        )

    if intent in {"compare", "diff"}:
        normalized = _validate_series_entries(payload)
        results = [(label, _coerce_to_distributions(value)) for label, value in normalized]
        width_class = PanelWidthClass.NARROW
        if intent == "diff":
            width_class = PanelWidthClass.WIDE
            plan_kind = "diff"
        else:
            if all(result.is_unswept() for _, result in results):
                plan_kind = "compare_unswept"
                if len(results) > 3:
                    width_class = PanelWidthClass.WIDE
            elif all(len(result.axes) == 1 and _all_scalar(result) for _, result in results):
                plan_kind = "compare_scalar"
            else:
                plan_kind = "compare_faceted"
                width_class = PanelWidthClass.WIDE
        if chart_spec.width_override is not None:
            width_class = chart_spec.width_override
        return ChartRenderPlan(
            plan_kind,
            width_class,
            tuple(results),
            chart_spec.x_label,
            chart_spec.y_label,
            chart_spec.title,
        )

    raise Exception("unknown chart intent {}".format(intent))


def build_report_plan(report_spec):
    if not isinstance(report_spec, ReportSpec):
        raise Exception("expected a report spec")
    hero = build_chart_plan(report_spec.hero) if report_spec.hero is not None else None
    rows = []
    pending_narrow = []
    notes = []

    def flush_pending():
        nonlocal pending_narrow
        if pending_narrow:
            rows.append(tuple(pending_narrow))
            pending_narrow = []

    for block in report_spec.blocks:
        if not isinstance(block, ReportBlock):
            raise Exception("invalid report block")
        if block.kind == "note":
            notes.append(block.value)
            continue
        if block.kind == "row":
            flush_pending()
            rows.append(tuple(build_chart_plan(chart) for chart in block.value))
            continue
        if block.kind == "panel":
            plan = build_chart_plan(block.value)
            if plan.width_class == PanelWidthClass.WIDE:
                flush_pending()
                rows.append((plan,))
            else:
                pending_narrow.append(plan)
                if len(pending_narrow) == 2:
                    flush_pending()
            continue
        raise Exception("unknown report block {}".format(block.kind))

    flush_pending()
    return ReportRenderPlan(report_spec.title, hero, tuple(rows), tuple(notes))
