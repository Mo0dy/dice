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
    probability_values: bool = False


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
    if set_window_title is None:
        return
    set_window_title(title)


def _effective_render_config(render_config=None):
    return render_config if render_config is not None else RenderConfig()


def _scale_probability(value, render_config=None):
    config = _effective_render_config(render_config)
    return value * config.probability_scale(default="percent")


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
    explicit_names = []
    for result in results:
        axis = result.axes[0]
        if axis.name and not axis.name.startswith("sweep_"):
            explicit_names.append(axis.name)
    if explicit_names and len(set(explicit_names)) == 1:
        return explicit_names[0]
    return "Sweep 1"


def _validate_same_axis_values(results):
    values = results[0].axes[0].values
    for result in results[1:]:
        if result.axes[0].values != values:
            raise Exception("Viewer exception: render comparison requires matching sweep axis values")


def _validate_outcome_domains(distributions):
    outcome_types = set()
    for distribution in distributions:
        for outcome in distribution.keys():
            outcome_types.add(isinstance(outcome, (int, float)))
    if len(outcome_types) > 1:
        raise Exception("Viewer exception: render comparison requires consistent outcome domains")


def _iter_result_distributions(results):
    for result in results:
        for distribution in result.cells.values():
            yield distribution


def _all_bernoulli(results):
    return all(set(distribution.keys()).issubset({0, 1}) for distribution in _iter_result_distributions(results))


def build_render_spec(result, assume_probability=False):
    result = _coerce_to_distributions(result)
    if result.is_unswept():
        return RenderSpec("bar", "Outcome", "Probability", probability_values=True)
    if len(result.axes) == 1:
        axis_name = _fallback_axis_name(result.axes[0], 0)
        if _all_scalar(result):
            return RenderSpec(
                "bar_scalar" if assume_probability else "line",
                axis_name,
                "Probability" if assume_probability else "Value",
                probability_values=assume_probability,
            )
        return RenderSpec("heatmap_distribution", axis_name, "Outcome", probability_values=True)
    if len(result.axes) == 2 and _all_scalar(result):
        return RenderSpec(
            "heatmap_scalar",
            _fallback_axis_name(result.axes[1], 1),
            _fallback_axis_name(result.axes[0], 0),
            probability_values=assume_probability,
        )
    raise Exception("Viewer exception: render does not support this result shape yet")


def build_comparison_spec(entries, assume_probability=False):
    labels, raw_results = zip(*entries)
    results = [_coerce_to_distributions(result) for result in raw_results]

    if all(result.is_unswept() for result in results):
        _validate_outcome_domains(result.only_distribution() for result in results)
        return RenderSpec(
            "compare_bar",
            "Outcome",
            "Probability",
            tuple(labels),
            probability_values=True,
        ), results

    if all(len(result.axes) == 1 and _all_scalar(result) for result in results):
        _validate_same_axis_values(results)
        return RenderSpec(
            "compare_line",
            _common_axis_name(results),
            "Probability" if assume_probability else "Value",
            tuple(labels),
            probability_values=assume_probability,
        ), results

    if all(len(result.axes) == 1 for result in results):
        _validate_same_axis_values(results)
        _validate_outcome_domains(_iter_result_distributions(results))
        if _all_bernoulli(results):
            return RenderSpec(
                "compare_probability_line",
                _common_axis_name(results),
                "Probability",
                tuple(labels),
                probability_values=True,
            ), results
        return RenderSpec(
            "compare_distribution_line",
            _common_axis_name(results),
            "Probability",
            tuple(labels),
            probability_values=True,
        ), results

    raise Exception(
        "Viewer exception: render comparison only supports unswept distributions, one-sweep scalar results, or one-sweep distribution results"
    )


def _plot_unswept_bar(ax, result, label=None, render_config=None):
    distrib = result.only_distribution()
    outcomes = _ordered_values(distrib.keys())
    positions, tick_labels = _category_positions(outcomes)
    values = [
        _scale_probability(distrib[outcome], render_config=render_config)
        for outcome in outcomes
    ]
    ax.bar(positions, values, alpha=0.85, label=label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if label:
        ax.legend()


def _plot_scalar_line(ax, result, label=None, render_config=None, probability_values=False):
    axis = result.axes[0]
    x_values = axis.values
    positions, tick_labels = _category_positions(x_values)
    y_values = [
        _scale_probability(_scalar_value(result.cells[(value,)]), render_config=render_config)
        if probability_values
        else _scalar_value(result.cells[(value,)])
        for value in x_values
    ]
    ax.plot(positions, y_values, marker="o", label=label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if label:
        ax.legend()


def _plot_scalar_bar(ax, result, label=None, render_config=None, probability_values=False):
    axis = result.axes[0]
    x_values = axis.values
    positions, tick_labels = _category_positions(x_values)
    y_values = [
        _scale_probability(_scalar_value(result.cells[(value,)]), render_config=render_config)
        if probability_values
        else _scalar_value(result.cells[(value,)])
        for value in x_values
    ]
    ax.bar(positions, y_values, alpha=0.85, label=label)
    if tick_labels is not None:
        ax.set_xticks(positions)
        ax.set_xticklabels(tick_labels)
    if label:
        ax.legend()


def _plot_distribution_heatmap(ax, result, render_config=None):
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
            row.append(
                _scale_probability(
                    result.cells[(value,)][outcome],
                    render_config=render_config,
                )
            )
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower")
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels([str(value) for value in x_values])
    ax.set_yticks(range(len(all_outcomes)))
    ax.set_yticklabels([str(outcome) for outcome in all_outcomes])
    return image


def _plot_scalar_heatmap(ax, result, render_config=None, probability_values=False):
    y_values = result.axes[0].values
    x_values = result.axes[1].values
    matrix = []
    for y_value in y_values:
        row = []
        for x_value in x_values:
            value = _scalar_value(result.cells[(y_value, x_value)])
            row.append(
                _scale_probability(value, render_config=render_config)
                if probability_values
                else value
            )
        matrix.append(row)
    image = ax.imshow(matrix, aspect="auto", origin="lower")
    ax.set_xticks(range(len(x_values)))
    ax.set_xticklabels([str(value) for value in x_values])
    ax.set_yticks(range(len(y_values)))
    ax.set_yticklabels([str(value) for value in y_values])
    return image


def render_result(result, label=None, x_label=None, title=None, render_config=None, assume_probability=False):
    result = _coerce_to_distributions(result)
    spec = build_render_spec(result, assume_probability=assume_probability)
    render_config = _effective_render_config(render_config)
    figure, ax = plt.subplots()

    if spec.kind == "bar":
        _plot_unswept_bar(ax, result, label=label, render_config=render_config)
    elif spec.kind == "bar_scalar":
        _plot_scalar_bar(
            ax,
            result,
            label=label,
            render_config=render_config,
            probability_values=spec.probability_values,
        )
    elif spec.kind == "line":
        _plot_scalar_line(
            ax,
            result,
            label=label,
            render_config=render_config,
            probability_values=spec.probability_values,
        )
    elif spec.kind == "heatmap_distribution":
        image = _plot_distribution_heatmap(ax, result, render_config=render_config)
        figure.colorbar(
            image,
            ax=ax,
            label=render_config.probability_axis_label(default="percent"),
        )
    elif spec.kind == "heatmap_scalar":
        image = _plot_scalar_heatmap(
            ax,
            result,
            render_config=render_config,
            probability_values=spec.probability_values,
        )
        figure.colorbar(
            image,
            ax=ax,
            label=(
                render_config.probability_axis_label(default="percent")
                if spec.probability_values
                else "Value"
            ),
        )
    else:
        raise Exception("Viewer exception: unsupported render kind {}".format(spec.kind))

    if title is not None:
        ax.set_title(title)
        _set_window_title(figure, title)
    ax.set_xlabel(x_label if x_label is not None else spec.x_label)
    if spec.probability_values and spec.kind != "heatmap_scalar":
        ax.set_ylabel(render_config.probability_axis_label(default="percent"))
    elif spec.kind == "bar":
        ax.set_ylabel(render_config.probability_axis_label(default="percent"))
    else:
        ax.set_ylabel(spec.y_label)
    figure.tight_layout()
    output_path = _show_figure(figure, render_config=render_config)
    return RenderOutcome(spec, output_path)


def render_comparison(entries, x_label=None, title=None, render_config=None, assume_probability=False):
    spec, results = build_comparison_spec(entries, assume_probability=assume_probability)
    render_config = _effective_render_config(render_config)
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
            values = [
                _scale_probability(distrib[outcome], render_config=render_config)
                for outcome in all_outcomes
            ]
            ax.step(positions, values, where="mid", label=label)
            ax.plot(positions, values, marker="o")
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    elif spec.kind == "compare_line":
        x_values = results[0].axes[0].values
        positions, tick_labels = _category_positions(x_values)
        for label, result in zip(spec.series_labels, results):
            y_values = [
                _scale_probability(_scalar_value(result.cells[(value,)]), render_config=render_config)
                if spec.probability_values
                else _scalar_value(result.cells[(value,)])
                for value in x_values
            ]
            ax.plot(positions, y_values, marker="o", label=label)
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    elif spec.kind == "compare_probability_line":
        x_values = results[0].axes[0].values
        positions, tick_labels = _category_positions(x_values)
        for label, result in zip(spec.series_labels, results):
            y_values = [
                _scale_probability(result.cells[(value,)][1], render_config=render_config)
                for value in x_values
            ]
            ax.plot(positions, y_values, marker="o", label=label)
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    elif spec.kind == "compare_distribution_line":
        x_values = results[0].axes[0].values
        positions, tick_labels = _category_positions(x_values)
        all_outcomes = []
        seen = set()
        for result in results:
            for distribution in result.cells.values():
                for outcome in _ordered_values(distribution.keys()):
                    if outcome not in seen:
                        all_outcomes.append(outcome)
                        seen.add(outcome)
        for label, result in zip(spec.series_labels, results):
            for outcome in all_outcomes:
                y_values = [
                    _scale_probability(result.cells[(value,)][outcome], render_config=render_config)
                    for value in x_values
                ]
                ax.plot(positions, y_values, marker="o", label="{}: {}".format(label, outcome))
        if tick_labels is not None:
            ax.set_xticks(positions)
            ax.set_xticklabels(tick_labels)
    else:
        raise Exception("Viewer exception: unsupported comparison render kind {}".format(spec.kind))

    if title is not None:
        ax.set_title(title)
        _set_window_title(figure, title)
    ax.set_xlabel(x_label if x_label is not None else spec.x_label)
    if spec.probability_values:
        ax.set_ylabel(render_config.probability_axis_label(default="percent"))
    else:
        ax.set_ylabel(spec.y_label)
    ax.legend()
    figure.tight_layout()
    output_path = _show_figure(figure, render_config=render_config)
    return RenderOutcome(spec, output_path)
