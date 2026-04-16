#!/usr/bin/env python3

"""Render runtime dice results directly with Matplotlib."""

from dataclasses import dataclass
import os
import tempfile

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "dice-mplconfig"))
from matplotlib.backends import BackendFilter, backend_registry
import matplotlib.pyplot as plt

from diceengine import Distributions, RenderConfig, _coerce_to_distributions


@dataclass(frozen=True)
class RenderSpec:
    kind: str
    x_label: str
    y_label: str
    series_labels: tuple = ()


@dataclass(frozen=True)
class RenderOutcome:
    spec: RenderSpec
    output_path: str | None = None


def _fallback_axis_name(axis, index):
    if axis.name and not axis.name.startswith("sweep_"):
        return axis.name
    return "Sweep {}".format(index + 1)


def _ordered_values(values):
    try:
        return tuple(sorted(values))
    except TypeError:
        return tuple(values)


def _is_interactive_backend(backend_name):
    normalized = backend_name.lower()
    interactive_backends = {
        name.lower() for name in backend_registry.list_builtin(BackendFilter.INTERACTIVE)
    }
    return normalized in interactive_backends


def _show_figure(figure, render_config=None):
    render_config = render_config if render_config is not None else RenderConfig()
    backend = plt.get_backend()
    if _is_interactive_backend(backend):
        if render_config.interactive_blocking:
            plt.show()
            plt.close(figure)
            return None
        plt.show(block=False)
        plt.pause(0.001)
        return None

    handle, path = tempfile.mkstemp(prefix="dice-render-", suffix=".png")
    os.close(handle)
    figure.savefig(path)
    plt.close(figure)
    return path


def _is_scalar_distribution(distrib):
    items = list(distrib.items())
    return (
        len(items) == 1
        and items[0][1] == 1
        and isinstance(items[0][0], (int, float))
    )


def _scalar_value(distrib):
    return next(iter(distrib.keys()))


def _all_scalar(result):
    return all(_is_scalar_distribution(distrib) for distrib in result.cells.values())


def _category_positions(values):
    numeric = all(isinstance(value, (int, float)) for value in values)
    if numeric:
        return list(values), None
    positions = list(range(len(values)))
    labels = [str(value) for value in values]
    return positions, labels


def _common_axis_name(results):
    if not results:
        return "Sweep 1"
    names = []
    for result in results:
        axis = result.axes[0]
        names.append(_fallback_axis_name(axis, 0))
    first = names[0]
    if all(name == first for name in names):
        return first
    raise Exception("Viewer exception: render comparison requires matching sweep axis names")


def _validate_same_axis_values(results):
    values = results[0].axes[0].values
    for result in results[1:]:
        if result.axes[0].values != values:
            raise Exception("Viewer exception: render comparison requires matching sweep axis values")


def _validate_outcome_domains(results):
    outcome_types = set()
    for result in results:
        for outcome in result.only_distribution().keys():
            outcome_types.add(isinstance(outcome, (int, float)))
    if len(outcome_types) > 1:
        raise Exception("Viewer exception: render comparison requires consistent outcome domains")


def build_render_spec(result):
    result = _coerce_to_distributions(result)
    if result.is_unswept():
        return RenderSpec("bar", "Outcome", "Probability")
    if len(result.axes) == 1:
        axis_name = _fallback_axis_name(result.axes[0], 0)
        if _all_scalar(result):
            return RenderSpec("line", axis_name, "Value")
        return RenderSpec("heatmap_distribution", axis_name, "Outcome")
    if len(result.axes) == 2 and _all_scalar(result):
        return RenderSpec(
            "heatmap_scalar",
            _fallback_axis_name(result.axes[1], 1),
            _fallback_axis_name(result.axes[0], 0),
        )
    raise Exception("Viewer exception: render does not support this result shape yet")


def build_comparison_spec(entries):
    labels, raw_results = zip(*entries)
    results = [_coerce_to_distributions(result) for result in raw_results]

    if all(result.is_unswept() for result in results):
        _validate_outcome_domains(results)
        return RenderSpec("compare_bar", "Outcome", "Probability", tuple(labels)), results

    if all(len(result.axes) == 1 and _all_scalar(result) for result in results):
        _validate_same_axis_values(results)
        return RenderSpec("compare_line", _common_axis_name(results), "Value", tuple(labels)), results

    raise Exception("Viewer exception: render comparison only supports unswept distributions or one-sweep scalar results")


def _plot_unswept_bar(ax, result, label=None):
    distrib = result.only_distribution()
    outcomes = _ordered_values(distrib.keys())
    positions, tick_labels = _category_positions(outcomes)
    values = [distrib[outcome] for outcome in outcomes]
    ax.bar(positions, values, alpha=0.85, label=label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if label:
        ax.legend()


def _plot_scalar_line(ax, result, label=None):
    axis = result.axes[0]
    x_values = axis.values
    positions, tick_labels = _category_positions(x_values)
    y_values = [_scalar_value(result.cells[(value,)]) for value in x_values]
    ax.plot(positions, y_values, marker="o", label=label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if label:
        ax.legend()


def _plot_distribution_heatmap(ax, result):
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
            row.append(result.cells[(value,)][outcome])
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower")
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels([str(value) for value in x_values])
    ax.set_yticks(range(len(all_outcomes)))
    ax.set_yticklabels([str(outcome) for outcome in all_outcomes])
    return image


def _plot_scalar_heatmap(ax, result):
    y_values = result.axes[0].values
    x_values = result.axes[1].values
    matrix = []
    for y_value in y_values:
        row = []
        for x_value in x_values:
            row.append(_scalar_value(result.cells[(y_value, x_value)]))
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower")
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels([str(value) for value in x_values])
    ax.set_yticks(range(len(y_values)))
    ax.set_yticklabels([str(value) for value in y_values])
    return image


def render_result(result, label=None, render_config=None):
    result = _coerce_to_distributions(result)
    spec = build_render_spec(result)
    figure, ax = plt.subplots()

    if spec.kind == "bar":
        _plot_unswept_bar(ax, result, label=label)
    elif spec.kind == "line":
        _plot_scalar_line(ax, result, label=label)
    elif spec.kind == "heatmap_distribution":
        image = _plot_distribution_heatmap(ax, result)
        figure.colorbar(image, ax=ax, label="Probability")
    elif spec.kind == "heatmap_scalar":
        image = _plot_scalar_heatmap(ax, result)
        figure.colorbar(image, ax=ax, label="Value")
    else:
        raise Exception("Viewer exception: unsupported render kind {}".format(spec.kind))

    ax.set_xlabel(spec.x_label)
    ax.set_ylabel(spec.y_label)
    figure.tight_layout()
    output_path = _show_figure(figure, render_config=render_config)
    return RenderOutcome(spec, output_path)


def render_comparison(entries, render_config=None):
    spec, results = build_comparison_spec(entries)
    figure, ax = plt.subplots()

    if spec.kind == "compare_bar":
        all_outcomes = []
        seen = set()
        for result in results:
            for outcome in _ordered_values(result.only_distribution().keys()):
                if outcome not in seen:
                    all_outcomes.append(outcome)
                    seen.add(outcome)
        positions, tick_labels = _category_positions(all_outcomes)
        for label, result in zip(spec.series_labels, results):
            distrib = result.only_distribution()
            values = [distrib[outcome] for outcome in all_outcomes]
            ax.step(positions, values, where="mid", label=label)
            ax.plot(positions, values, marker="o")
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    elif spec.kind == "compare_line":
        x_values = results[0].axes[0].values
        positions, tick_labels = _category_positions(x_values)
        for label, result in zip(spec.series_labels, results):
            y_values = [_scalar_value(result.cells[(value,)]) for value in x_values]
            ax.plot(positions, y_values, marker="o", label=label)
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    else:
        raise Exception("Viewer exception: unsupported comparison render kind {}".format(spec.kind))

    ax.set_xlabel(spec.x_label)
    ax.set_ylabel(spec.y_label)
    ax.legend()
    figure.tight_layout()
    output_path = _show_figure(figure, render_config=render_config)
    return RenderOutcome(spec, output_path)
