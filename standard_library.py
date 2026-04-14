#!/usr/bin/env python3

"""Standard library callables registered into the dice interpreter."""

from itertools import product

from diceengine import Distrib, _coerce_to_distributions, _union_axes
import viewer


def register_standard_library(interpreter, callable_entry_type):
    interpreter._register_callable(
        callable_entry_type("sum", "host", arity=2, function=lambda count, value: builtin_sum(interpreter, count, value))
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
