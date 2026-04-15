#!/usr/bin/env python3

"""Standard library callables registered into the dice interpreter.

New builtins must be added here and registered in ``register_standard_library``.
The interpreter only exposes standard-library functions that are wired through
that registration path.
"""

from itertools import product

from diceengine import Distrib, Distributions, _coerce_to_distributions, _union_axes
import viewer


def register_standard_library(interpreter, callable_entry_type):
    interpreter._register_callable(
        callable_entry_type("mean", "host", arity=1, function=lambda value: builtin_mean(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("sample", "host", arity=1, function=lambda value: builtin_sample(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("mass", "host", arity=1, function=lambda value: builtin_mass(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("var", "host", arity=1, function=lambda value: builtin_var(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("std", "host", arity=1, function=lambda value: builtin_std(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("sum", "host", arity=2, function=lambda count, value: builtin_sum(interpreter, count, value))
    )
    interpreter._register_callable(
        callable_entry_type("sumover", "host", arity=2, function=lambda axis_name, value: builtin_sumover(interpreter, axis_name, value))
    )
    interpreter._register_callable(
        callable_entry_type("total", "host", arity=1, function=lambda value: builtin_total(interpreter, value))
    )
    interpreter._register_callable(
        callable_entry_type("render", "host", variadic=True, function=lambda *args: builtin_render(interpreter, *args))
    )


def builtin_sum(interpreter, count, value):
    count_value = _coerce_to_distributions(count)
    contributions = []

    for count_coordinates, count_distrib in count_value.cells.items():
        count_items = list(count_distrib.items())
        if len(count_items) != 1:
            interpreter.exception("sum expects a deterministic count per sweep point")

        count_outcome, count_probability = count_items[0]
        if count_probability != 1:
            interpreter.exception("sum expects a deterministic count per sweep point")
        if not isinstance(count_outcome, int) or count_outcome < 0:
            interpreter.exception("sum expects a non-negative integer count")

        repeated = 0
        for _ in range(count_outcome):
            repeated = interpreter.engine.add(repeated, value)

        repeated_value = _coerce_to_distributions(repeated)
        count_selection = interpreter._fixed_axis_distribution(count_value.axes, count_coordinates)
        combined_axes = _union_axes([count_selection, repeated_value])
        coordinates_space = [()] if not combined_axes else product(*(axis.values for axis in combined_axes))
        cells = {}
        for coordinates in coordinates_space:
            if interpreter._lookup_projected(count_value.axes, {count_coordinates: 1}, combined_axes, coordinates, 0) != 1:
                continue
            cells[coordinates] = repeated_value.lookup(combined_axes, coordinates)
        contributions.append((combined_axes, cells))

    return interpreter._accumulate_distribution_contributions(contributions)


def builtin_mean(interpreter, value):
    return interpreter.engine.mean(value)


def builtin_sample(interpreter, value):
    return interpreter.engine.sample(value)


def builtin_mass(interpreter, value):
    return interpreter.engine.mass(value)


def builtin_var(interpreter, value):
    return interpreter.engine.variance(value)


def builtin_std(interpreter, value):
    return interpreter.engine.stddev(value)


def builtin_render(interpreter, *args):
    if not args:
        interpreter.exception("render expects at least one expression")

    if len(args) == 1:
        render_outcome = viewer.render_result(args[0])
        return render_outcome.output_path

    if len(args) % 2 != 0:
        interpreter.exception("render comparisons require a label for every expression")

    entries = []
    for index in range(0, len(args), 2):
        label = args[index + 1]
        if not isinstance(label, str):
            interpreter.exception("render comparison labels must be strings")
        entries.append((label, args[index]))

    if len(entries) < 2:
        interpreter.exception("render comparisons need at least two expressions")

    render_outcome = viewer.render_comparison(entries)
    return render_outcome.output_path


def _resolve_target_axis(interpreter, value, axis_name):
    if not isinstance(axis_name, str):
        interpreter.exception("sumover expects a string axis name")

    matches = [axis for axis in value.axes if axis.name == axis_name and axis.name != axis.key]
    if not matches:
        interpreter.exception("sumover could not find named axis {}".format(axis_name))
    if len(matches) > 1:
        interpreter.exception("sumover found multiple axes named {}".format(axis_name))
    return matches[0]


def _resolve_total_axis(interpreter, value):
    if not value.axes:
        interpreter.exception("total expects exactly one named axis")
    if len(value.axes) != 1:
        interpreter.exception("total expects exactly one named axis")

    axis = value.axes[0]
    if axis.name == axis.key:
        interpreter.exception("total expects exactly one named axis")
    return axis


def _coordinates_without_axis(axes, coordinates, target_key):
    return tuple(
        coordinate
        for axis, coordinate in zip(axes, coordinates)
        if axis.key != target_key
    )


def _sum_axis(interpreter, value, target_axis):
    remaining_axes = tuple(axis for axis in value.axes if axis.key != target_axis.key)
    grouped = {}

    for coordinates, distrib in value.cells.items():
        remaining_coordinates = _coordinates_without_axis(value.axes, coordinates, target_axis.key)
        grouped.setdefault(remaining_coordinates, []).append(distrib)

    cells = {}
    for remaining_coordinates, distribs in grouped.items():
        reduced = 0
        for distrib in distribs:
            reduced = interpreter.engine.add(reduced, distrib)
        reduced_value = _coerce_to_distributions(reduced)
        if not reduced_value.is_unswept():
            interpreter.exception("sumover reduction produced an unexpected sweep")
        cells[remaining_coordinates] = reduced_value.only_distribution()

    if not cells:
        return Distributions.scalar(0)
    return Distributions(remaining_axes, cells)


def builtin_sumover(interpreter, axis_name, value):
    distributions = _coerce_to_distributions(value)
    target_axis = _resolve_target_axis(interpreter, distributions, axis_name)
    return _sum_axis(interpreter, distributions, target_axis)


def builtin_total(interpreter, value):
    distributions = _coerce_to_distributions(value)
    target_axis = _resolve_total_axis(interpreter, distributions)
    return _sum_axis(interpreter, distributions, target_axis)
