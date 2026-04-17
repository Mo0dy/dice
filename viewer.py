#!/usr/bin/env python3

"""Render chart and report specs with Matplotlib."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import tempfile

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "dice-mplconfig"))
from matplotlib.backends import BackendFilter, backend_registry
from matplotlib.colors import ListedColormap
from matplotlib.ticker import FuncFormatter
import matplotlib.pyplot as plt
import numpy as np

from diceengine import (
    ChartSpec,
    Distributions,
    Distribution,
    PanelWidthClass,
    RenderConfig,
    RenderPlan,
    ReportBlock,
    ReportSpec,
    Sweep,
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
    output_path: str | None = None


_PALETTE = ("#2F5D8C", "#D97706", "#2F855A", "#B83280", "#4C51BF", "#C05621")
_SEQUENTIAL_CMAP = "Blues"
_DIVERGING_CMAP = "RdBu_r"
_TAIL_CLIP_MASS = 0.001


def _is_interactive_backend(backend_name):
    normalized = backend_name.lower()
    interactive_backends = {
        name.lower() for name in backend_registry.list_builtin(BackendFilter.INTERACTIVE)
    }
    return normalized in interactive_backends


def wait_for_rendered_figures(render_config=None):
    render_config = render_config if render_config is not None else RenderConfig()
    if not render_config.wait_for_figures_on_exit:
        return
    if not _is_interactive_backend(plt.get_backend()):
        return
    if not plt.get_fignums():
        return
    plt.show()


def _set_window_title(figure, title):
    if title is None:
        return
    manager = getattr(figure.canvas, "manager", None)
    if manager is None:
        return
    set_window_title = getattr(manager, "set_window_title", None)
    if set_window_title is not None:
        set_window_title(title)


def _apply_house_style():
    plt.rcParams.update(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "grid.linestyle": "-",
            "axes.facecolor": "#FCFCFD",
            "figure.facecolor": "white",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "font.size": 10,
            "savefig.dpi": 160,
        }
    )


def _default_output_path(output_format="png"):
    handle, path = tempfile.mkstemp(prefix="dice-render-", suffix=".{}".format(output_format))
    os.close(handle)
    return path


def _save_or_show(figure, *, render_config=None, path=None, output_format="png", dpi=None):
    render_config = render_config if render_config is not None else RenderConfig()
    dpi = dpi if dpi is not None else 160
    backend = plt.get_backend()
    if path is not None:
        figure.savefig(path, dpi=dpi, bbox_inches="tight")
        plt.close(figure)
        return path
    if _is_interactive_backend(backend):
        if render_config.interactive_blocking:
            plt.show()
            plt.close(figure)
            return None
        plt.show(block=False)
        plt.pause(0.001)
        return None
    output_path = _default_output_path(output_format=output_format)
    figure.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _scale_probability(value, render_config):
    return value * render_config.probability_scale(default="percent")


def _probability_label(render_config):
    return render_config.probability_axis_label(default="percent")


def _ordered_values(values):
    try:
        return tuple(sorted(values))
    except TypeError:
        return tuple(values)


def _is_scalar_distribution(distrib):
    items = list(distrib.items())
    return len(items) == 1 and items[0][1] == 1 and isinstance(items[0][0], (int, float))


def _scalar_value(distrib):
    return next(iter(distrib.keys()))


def _all_scalar(result):
    return all(_is_scalar_distribution(distrib) for distrib in result.cells.values())


def _common_axis_name(results):
    explicit_names = []
    for result in results:
        axis = result.axes[0]
        if axis.name and not axis.name.startswith("sweep_"):
            explicit_names.append(axis.name)
    if explicit_names and len(set(explicit_names)) == 1:
        return explicit_names[0]
    return "Sweep 1"


def _category_positions(values):
    numeric = all(isinstance(value, (int, float)) for value in values)
    if numeric:
        return list(values), None
    positions = list(range(len(values)))
    return positions, [str(value) for value in values]


def _format_percent_axis(ax):
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _pos: "{}%".format(int(y) if float(y).is_integer() else f"{y:.0f}")))


def _looks_like_damage_axis(label):
    if not isinstance(label, str):
        return False
    normalized = label.strip().lower()
    return normalized == "dmg" or "damage" in normalized


def _add_plot_notes(ax, notes):
    visible = [note for note in notes if note]
    if not visible:
        return
    ax.text(
        0.98,
        0.98,
        "\n".join(visible),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8.5,
        color="#4A5568",
        bbox={"facecolor": "white", "alpha": 0.92, "edgecolor": "#E2E8F0", "boxstyle": "round,pad=0.25"},
    )


def _central_probability_window(distrib):
    outcomes = _ordered_values(distrib.keys())
    if len(outcomes) < 25 or not all(isinstance(outcome, (int, float)) for outcome in outcomes):
        return outcomes, None
    probabilities = [distrib[outcome] for outcome in outcomes]
    left_index = 0
    right_index = len(outcomes) - 1
    removed_mass = 0.0
    while left_index < right_index:
        left_mass = probabilities[left_index]
        right_mass = probabilities[right_index]
        if removed_mass + min(left_mass, right_mass) > _TAIL_CLIP_MASS:
            break
        if left_mass <= right_mass:
            removed_mass += left_mass
            left_index += 1
        else:
            removed_mass += right_mass
            right_index -= 1
    if left_index == 0 and right_index == len(outcomes) - 1:
        return outcomes, None
    kept = outcomes[left_index : right_index + 1]
    if not kept:
        return outcomes, None
    return kept, "Showing central 99.9% of mass; tails omitted."


def _dominant_zero_note(distrib, x_label):
    if not _looks_like_damage_axis(x_label):
        return None
    if 0 not in distrib.keys():
        return None
    other_outcomes = [outcome for outcome in distrib.keys() if outcome != 0]
    if not other_outcomes:
        return None
    zero_probability = distrib[0]
    highest_other = max(distrib[outcome] for outcome in other_outcomes)
    if zero_probability < 0.2 or zero_probability < highest_other * 2:
        return None
    return "0 dmg omitted from scale: {:.0f}% miss.".format(zero_probability * 100)


def _dominant_zero_probability(distrib, x_label):
    if not _looks_like_damage_axis(x_label):
        return None
    if 0 not in distrib.keys():
        return None
    other_outcomes = [outcome for outcome in distrib.keys() if outcome != 0]
    if not other_outcomes:
        return None
    zero_probability = distrib[0]
    highest_other = max(distrib[outcome] for outcome in other_outcomes)
    if zero_probability < 0.2 or zero_probability < highest_other * 2:
        return None
    return zero_probability


def _display_outcomes(distrib, x_label, clip_tails=True):
    if clip_tails:
        outcomes, tail_note = _central_probability_window(distrib)
    else:
        outcomes, tail_note = _ordered_values(distrib.keys()), None
    notes = [tail_note]
    zero_note = _dominant_zero_note(distrib, x_label)
    if zero_note is not None and 0 in outcomes:
        outcomes = tuple(outcome for outcome in outcomes if outcome != 0)
        notes.append(zero_note)
    if not outcomes:
        outcomes = _ordered_values(distrib.keys())
        notes = []
    return outcomes, tuple(note for note in notes if note)


def _validate_series_entries(entries):
    normalized = []
    for entry in entries:
        if not isinstance(entry, TupleValue):
            raise Exception("comparison entries must be tuple literals like (\"Label\", value)")
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
            return ChartRenderPlan("best_strategy", width_class, result, chart_spec.x_label, chart_spec.y_label, chart_spec.title)
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
        return ChartRenderPlan(kind, width_class, result, chart_spec.x_label, chart_spec.y_label, chart_spec.title)

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
        return ChartRenderPlan(plan_kind, width_class, tuple(results), chart_spec.x_label, chart_spec.y_label, chart_spec.title)

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


def _plot_unswept_distribution(ax, result, render_config, x_label=None, y_label=None):
    distrib = result.only_distribution()
    outcomes, notes = _display_outcomes(distrib, x_label, clip_tails=True)
    positions, tick_labels = _category_positions(outcomes)
    values = [_scale_probability(distrib[outcome], render_config) for outcome in outcomes]
    ax.bar(positions, values, color=_PALETTE[0], alpha=0.9, edgecolor="white", linewidth=0.6)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if x_label is not None:
        ax.set_xlabel(x_label)
    ax.set_ylabel(y_label if y_label is not None else _probability_label(render_config))
    _format_percent_axis(ax)
    _add_plot_notes(ax, notes)


def _distribution_cdf(distrib):
    total = 0.0
    xs = _ordered_values(distrib.keys())
    ys = []
    for outcome in xs:
        total += distrib[outcome]
        ys.append(total)
    return xs, ys


def _distribution_surv(distrib):
    xs = _ordered_values(distrib.keys())
    total = 1.0
    ys = []
    for outcome in xs:
        ys.append(total - distrib[outcome])
        total -= distrib[outcome]
    return xs, ys


def _plot_distribution_curve(ax, result, render_config, mode, x_label=None, y_label=None):
    distrib = result.only_distribution()
    if mode == "cdf":
        xs, ys = _distribution_cdf(distrib)
    else:
        xs, ys = _distribution_surv(distrib)
    ys = [_scale_probability(value, render_config) for value in ys]
    positions, tick_labels = _category_positions(xs)
    ax.step(positions, ys, where="post", color=_PALETTE[0], linewidth=2.0)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if x_label is not None:
        ax.set_xlabel(x_label)
    ax.set_ylabel(y_label if y_label is not None else _probability_label(render_config))
    _format_percent_axis(ax)


def _plot_scalar_sweep(ax, result, render_config, x_label=None, y_label=None):
    axis = result.axes[0]
    x_values = axis.values
    positions, tick_labels = _category_positions(x_values)
    y_values = [_scalar_value(result.cells[(value,)]) for value in x_values]
    ax.plot(positions, y_values, color=_PALETTE[0], linewidth=2.2)
    ax.scatter(positions, y_values, color=_PALETTE[0], s=18)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    ax.set_xlabel(x_label if x_label is not None else (axis.name if not axis.name.startswith("sweep_") else "Sweep 1"))
    ax.set_ylabel(y_label if y_label is not None else "Value")


def _plot_distribution_sweep(ax, result, render_config, x_label=None, y_label=None):
    axis = result.axes[0]
    x_values = axis.values
    all_outcomes = []
    seen = set()
    for value in x_values:
        for outcome in _ordered_values(result.cells[(value,)].keys()):
            if outcome not in seen:
                all_outcomes.append(outcome)
                seen.add(outcome)
    matrix = []
    for outcome in all_outcomes:
        row = []
        for value in x_values:
            row.append(_scale_probability(result.cells[(value,)][outcome], render_config))
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower", cmap=_SEQUENTIAL_CMAP)
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels([str(value) for value in x_values])
    ax.set_yticks(range(len(all_outcomes)))
    ax.set_yticklabels([str(outcome) for outcome in all_outcomes])
    ax.set_xlabel(x_label if x_label is not None else (axis.name if not axis.name.startswith("sweep_") else "Sweep 1"))
    ax.set_ylabel(y_label if y_label is not None else "Outcome")
    return image


def _plot_scalar_heatmap(ax, result, render_config):
    row_axis, col_axis = result.axes
    matrix = []
    for row_value in row_axis.values:
        row = []
        for col_value in col_axis.values:
            row.append(_scalar_value(result.cells[(row_value, col_value)]))
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower", cmap=_SEQUENTIAL_CMAP)
    ax.set_xticks(range(len(col_axis.values)))
    ax.set_xticklabels([str(value) for value in col_axis.values])
    ax.set_yticks(range(len(row_axis.values)))
    ax.set_yticklabels([str(value) for value in row_axis.values])
    ax.set_xlabel(col_axis.name if not col_axis.name.startswith("sweep_") else "Sweep 2")
    ax.set_ylabel(row_axis.name if not row_axis.name.startswith("sweep_") else "Sweep 1")
    return image


def _draw_series_labels(ax, positions, series_data):
    for color, label, values in series_data:
        ax.text(
            positions[-1] + 0.15 if positions else 0,
            values[-1],
            label,
            color=color,
            fontsize=9,
            va="center",
        )


def _plot_compare_scalar(ax, entries, render_config, x_label=None, y_label=None):
    x_values = entries[0][1].axes[0].values
    positions, tick_labels = _category_positions(x_values)
    series_data = []
    for index, (label, result) in enumerate(entries):
        y_values = [_scalar_value(result.cells[(value,)]) for value in x_values]
        color = _PALETTE[index % len(_PALETTE)]
        ax.plot(positions, y_values, color=color, linewidth=2.0, label=label)
        ax.scatter(positions, y_values, color=color, s=16)
        series_data.append((color, label, y_values))
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    axis_name = entries[0][1].axes[0].name
    ax.set_xlabel(x_label if x_label is not None else (axis_name if not axis_name.startswith("sweep_") else "Sweep 1"))
    ax.set_ylabel(y_label if y_label is not None else "Value")
    if len(entries) <= 4:
        _draw_series_labels(ax, positions, series_data)
    else:
        ax.legend(frameon=False)


def _plot_compare_unswept(ax, entries, render_config, x_label=None, y_label=None):
    all_outcomes = []
    seen = set()
    notes = []
    remove_zero = False
    displayed_outcomes_by_label = {}
    zero_probabilities = {}
    for _, result in entries:
        distrib = result.only_distribution()
        outcomes, distrib_notes = _display_outcomes(distrib, x_label, clip_tails=False)
        notes.extend(
            note for note in distrib_notes if not note.startswith("0 dmg omitted from scale:")
        )
        displayed_outcomes_by_label[id(result)] = outcomes
    if _looks_like_damage_axis(x_label):
        for label, result in entries:
            distrib = result.only_distribution()
            zero_probability = _dominant_zero_probability(distrib, x_label)
            if zero_probability is not None:
                remove_zero = True
                zero_probabilities[label] = zero_probability
    for _, result in entries:
        outcomes = displayed_outcomes_by_label[id(result)]
        for outcome in outcomes:
            if remove_zero and outcome == 0:
                continue
            if outcome not in seen:
                all_outcomes.append(outcome)
                seen.add(outcome)
    positions, tick_labels = _category_positions(all_outcomes)
    for index, (label, result) in enumerate(entries):
        distrib = result.only_distribution()
        values = [_scale_probability(distrib[outcome], render_config) for outcome in all_outcomes]
        color = _PALETTE[index % len(_PALETTE)]
        display_label = label
        if label in zero_probabilities:
            display_label = "{} ({:.0f}% miss)".format(label, zero_probabilities[label] * 100)
        ax.step(positions, values, where="mid", color=color, linewidth=1.8, label=display_label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if x_label is not None:
        ax.set_xlabel(x_label)
    ax.set_ylabel(y_label if y_label is not None else _probability_label(render_config))
    _format_percent_axis(ax)
    ax.legend(frameon=False)
    deduped_notes = []
    for note in notes:
        if note not in deduped_notes:
            deduped_notes.append(note)
    if zero_probabilities:
        deduped_notes.insert(0, "0 dmg omitted from x-axis.")
    _add_plot_notes(ax, deduped_notes)


def _plot_diff(ax, entries, render_config, x_label=None, y_label=None):
    if len(entries) != 2:
        raise Exception("r_diff requires exactly two labeled entries")
    (left_label, left_result), (right_label, right_result) = entries
    if not (len(left_result.axes) == 1 and len(right_result.axes) == 1 and _all_scalar(left_result) and _all_scalar(right_result)):
        raise Exception("r_diff currently supports one-axis scalar sweeps")
    x_values = left_result.axes[0].values
    if right_result.axes[0].values != x_values:
        raise Exception("r_diff requires matching sweep values")
    positions, tick_labels = _category_positions(x_values)
    y_values = [
        _scalar_value(left_result.cells[(value,)]) - _scalar_value(right_result.cells[(value,)])
        for value in x_values
    ]
    ax.axhline(0, color="#718096", linewidth=1.0, linestyle="--")
    ax.plot(positions, y_values, color=_PALETTE[0], linewidth=2.2)
    ax.fill_between(positions, y_values, 0, color=_PALETTE[0], alpha=0.18)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    axis_name = left_result.axes[0].name
    ax.set_xlabel(x_label if x_label is not None else (axis_name if not axis_name.startswith("sweep_") else "Sweep 1"))
    ax.set_ylabel(y_label if y_label is not None else "{} - {}".format(left_label, right_label))


def _best_strategy_payload(result):
    if not (len(result.axes) == 2 and _all_scalar(result)):
        raise Exception("r_best expects a two-axis scalar sweep")
    strategy_axis, condition_axis = result.axes
    strategies = strategy_axis.values
    winner_indexes = []
    margins = []
    for condition in condition_axis.values:
        values = [_scalar_value(result.cells[(strategy, condition)]) for strategy in strategies]
        ordered = sorted(enumerate(values), key=lambda item: item[1], reverse=True)
        winner_indexes.append(ordered[0][0])
        margin = ordered[0][1] - ordered[1][1] if len(ordered) > 1 else 0
        margins.append(margin)
    winner_matrix = np.array([winner_indexes])
    return strategy_axis, condition_axis, winner_matrix, tuple(margins)


def _plot_best_strategy(axes, result, render_config):
    ax_winner, ax_margin = axes
    strategy_axis, condition_axis, winner_matrix, margins = _best_strategy_payload(result)
    cmap = ListedColormap(list(_PALETTE[: max(2, len(strategy_axis.values))]))
    image1 = ax_winner.imshow(winner_matrix, aspect="auto", origin="lower", cmap=cmap, vmin=0, vmax=max(0, len(strategy_axis.values) - 1))
    ax_winner.set_xticks(range(len(condition_axis.values)))
    ax_winner.set_xticklabels([str(value) for value in condition_axis.values])
    ax_winner.set_yticks([0])
    ax_winner.set_yticklabels(["Winner"])
    ax_winner.set_xlabel(condition_axis.name if not condition_axis.name.startswith("sweep_") else "Condition")
    ax_winner.set_title("Best strategy")
    colorbar = ax_winner.figure.colorbar(image1, ax=ax_winner, ticks=range(len(strategy_axis.values)))
    colorbar.ax.set_yticklabels([str(value) for value in strategy_axis.values])
    x_values = condition_axis.values
    positions, tick_labels = _category_positions(x_values)
    ax_margin.plot(positions, margins, color=_PALETTE[0], linewidth=2.2)
    ax_margin.fill_between(positions, margins, 0, color=_PALETTE[0], alpha=0.18)
    if tick_labels is not None:
        ax_margin.set_xticks(positions)
        ax_margin.set_xticklabels(tick_labels)
    ax_margin.set_xlabel(condition_axis.name if not condition_axis.name.startswith("sweep_") else "Condition")
    ax_margin.set_ylabel("Margin")
    ax_margin.set_title("Winner margin")


def render_chart_on_axes(figure, axes, plan, render_config):
    if plan.kind == "best_strategy":
        _plot_best_strategy(axes, plan.payload, render_config)
        return

    if isinstance(axes, np.ndarray):
        ax = axes.flat[0]
    elif isinstance(axes, (list, tuple)):
        ax = axes[0]
    else:
        ax = axes
    if plan.kind == "unswept_distribution":
        _plot_unswept_distribution(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "cdf":
        _plot_distribution_curve(ax, plan.payload, render_config, "cdf", x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "surv":
        _plot_distribution_curve(ax, plan.payload, render_config, "surv", x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "scalar_sweep":
        _plot_scalar_sweep(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "distribution_sweep":
        image = _plot_distribution_sweep(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
        figure.colorbar(image, ax=ax, label=_probability_label(render_config))
    elif plan.kind == "scalar_heatmap":
        image = _plot_scalar_heatmap(ax, plan.payload, render_config)
        figure.colorbar(image, ax=ax, label="Value")
    elif plan.kind == "compare_scalar":
        _plot_compare_scalar(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "compare_unswept":
        _plot_compare_unswept(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
    elif plan.kind == "compare_faceted":
        entries = plan.payload
        subplots = ax
        if not isinstance(subplots, np.ndarray):
            subplots = np.array([subplots])
        for subplot, (label, result) in zip(subplots.flat, entries):
            subplan = build_chart_plan(
                ChartSpec("auto", result, x_label=plan.x_label, y_label=plan.y_label, title=label)
            )
            render_chart_on_axes(figure, subplot, subplan, render_config)
        for subplot in subplots.flat[len(entries):]:
            subplot.axis("off")
    elif plan.kind == "diff":
        _plot_diff(ax, plan.payload, render_config, x_label=plan.x_label, y_label=plan.y_label)
    else:
        raise Exception("unsupported chart plan {}".format(plan.kind))
    if plan.title is not None and plan.kind != "compare_faceted":
        ax.set_title(plan.title)


def render_chart(chart_spec, *, render_config=None, path=None, output_format="png", dpi=None):
    _apply_house_style()
    render_config = render_config if render_config is not None else RenderConfig()
    plan = build_chart_plan(chart_spec)
    if plan.kind == "best_strategy":
        figure, axes = plt.subplots(2, 1, figsize=(11.5, 6.6), gridspec_kw={"height_ratios": [1.3, 1.0]})
    elif plan.kind == "compare_faceted":
        count = len(plan.payload)
        cols = 2
        rows = int(math.ceil(count / cols))
        figure, axes = plt.subplots(rows, cols, figsize=(12, 4.4 * rows))
    else:
        width = 6.6 if plan.width_class == PanelWidthClass.NARROW else 11.5
        figure, axes = plt.subplots(figsize=(width, 4.6))
    render_chart_on_axes(figure, axes, plan, render_config)
    _set_window_title(figure, plan.title)
    output_path = _save_or_show(
        figure,
        render_config=render_config,
        path=path,
        output_format=output_format or "png",
        dpi=dpi,
    )
    return RenderOutcome(plan, output_path)


def render_report(report_spec, *, render_config=None, path=None, output_format="png", dpi=None):
    _apply_house_style()
    render_config = render_config if render_config is not None else RenderConfig()
    plan = build_report_plan(report_spec)
    row_count = len(plan.rows) + (1 if plan.hero is not None else 0)
    figure = plt.figure(figsize=(12.5, max(5.5, 2.2 + row_count * 3.8 + len(plan.notes) * 0.5)))
    outer_rows = row_count if row_count else 1
    outer = figure.add_gridspec(outer_rows, 1, hspace=0.42)
    current_row = 0

    if plan.title is not None:
        figure.suptitle(plan.title, fontsize=16, fontweight="bold", x=0.05, y=0.99, ha="left")

    if plan.hero is not None:
        if plan.hero.kind == "best_strategy":
            subgrid = outer[current_row].subgridspec(2, 1, hspace=0.34, height_ratios=[1.3, 1.0])
            axes = [figure.add_subplot(subgrid[0, 0]), figure.add_subplot(subgrid[1, 0])]
        elif plan.hero.kind == "compare_faceted":
            entries = plan.hero.payload
            cols = 2
            rows = int(math.ceil(len(entries) / cols))
            subgrid = outer[current_row].subgridspec(rows, cols, wspace=0.22, hspace=0.32)
            axes = np.array([[figure.add_subplot(subgrid[r, c]) for c in range(cols)] for r in range(rows)])
        else:
            axes = figure.add_subplot(outer[current_row, 0])
        render_chart_on_axes(figure, axes, plan.hero, render_config)
        current_row += 1

    for row in plan.rows:
        if len(row) == 1:
            chart = row[0]
            if chart.kind == "best_strategy":
                subgrid = outer[current_row].subgridspec(2, 1, hspace=0.34, height_ratios=[1.3, 1.0])
                axes = [figure.add_subplot(subgrid[0, 0]), figure.add_subplot(subgrid[1, 0])]
            elif chart.kind == "compare_faceted":
                entries = chart.payload
                cols = 2
                rows_count = int(math.ceil(len(entries) / cols))
                subgrid = outer[current_row].subgridspec(rows_count, cols, wspace=0.22, hspace=0.32)
                axes = np.array([[figure.add_subplot(subgrid[r, c]) for c in range(cols)] for r in range(rows_count)])
            else:
                axes = figure.add_subplot(outer[current_row, 0])
            render_chart_on_axes(figure, axes, chart, render_config)
        else:
            subgrid = outer[current_row].subgridspec(1, len(row), wspace=0.24)
            for index, chart in enumerate(row):
                axes = figure.add_subplot(subgrid[0, index])
                render_chart_on_axes(figure, axes, chart, render_config)
        current_row += 1

    if plan.notes:
        figure.text(0.05, 0.02, "\n".join(plan.notes), ha="left", va="bottom", fontsize=9, color="#4A5568")

    output_path = _save_or_show(
        figure,
        render_config=render_config,
        path=path,
        output_format=output_format or "png",
        dpi=dpi,
    )
    return RenderOutcome(plan, output_path)
