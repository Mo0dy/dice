#!/usr/bin/env python3

"""Sweep-aware probability primitives for dice semantics and Python use."""

from dataclasses import dataclass
from functools import wraps
import importlib
from itertools import product
from math import inf, sqrt
import random

from diagnostics import RuntimeError as DiceRuntimeError

# note that comb only exists in python 3.8
# but it's faster then just calculating factorials
try:
    from math import comb
except ImportError:
    from math import factorial

    def comb(n, k):
        return factorial(n) / factorial(k) / factorial(n - k)


TRUE = "true"
FALSE = "false"
_viewer_module = None


def exception(message):
    raise DiceRuntimeError(message)


def runtime_error(message, hint=None):
    raise DiceRuntimeError(message, hint=hint)


def _get_viewer():
    global _viewer_module
    if _viewer_module is None:
        _viewer_module = importlib.import_module("viewer")
    return _viewer_module


class Distrib(object):
    """Probability distribution of outcomes to probability mass."""

    def __init__(self, distrib=None):
        self.distrib = distrib if distrib else {}

    def __repr__(self):
        return str(self.distrib)

    def __getitem__(self, key):
        return self.distrib[key] if key in self.distrib else 0

    def __setitem__(self, key, value):
        self.distrib[key] = value

    def items(self):
        return self.distrib.items()

    def keys(self):
        return self.distrib.keys()

    def probabilities(self):
        return self.distrib.values()

    def total_probability(self):
        return sum(self.probabilities())

    def average(self):
        total = 0
        for outcome, probability in self.items():
            if not isinstance(outcome, (int, float)):
                runtime_error(
                    "mean expects numeric outcomes, got {}".format(type(outcome)),
                    hint="Apply mean only to numeric distributions.",
                )
            total += outcome * probability
        return total

    def variance(self):
        mean = self.average()
        total = 0
        for outcome, probability in self.items():
            if not isinstance(outcome, (int, float)):
                runtime_error(
                    "variance expects numeric outcomes, got {}".format(type(outcome)),
                    hint="Apply variance only to numeric distributions.",
                )
            total += ((outcome - mean) ** 2) * probability
        return total

    def stddev(self):
        return sqrt(self.variance())


@dataclass(frozen=True)
class SweepAxis:
    key: str
    name: str
    values: tuple


class Sweep(object):
    """Finite sweep of candidate values, optionally named."""

    counter = 0

    def __init__(self, values, name=None):
        deduped = tuple(dict.fromkeys(values))
        if not deduped:
            runtime_error("sweeps require at least one value")
        self.values = deduped
        self.name = name
        self.key = "sweep_{}".format(Sweep.counter)
        Sweep.counter += 1

    def axis(self):
        axis_name = self.name if self.name else self.key
        return SweepAxis(self.key, axis_name, self.values)

    def __repr__(self):
        label = "{}:".format(self.name) if self.name else ""
        return "[{}{}]".format(label, ", ".join(str(value) for value in self.values))


class Distributions(object):
    """Set of distributions indexed by zero or more sweep axes."""

    def __init__(self, axes=None, cells=None):
        self.axes = tuple(axes or ())
        self.cells = cells if cells else {(): Distrib()}

    @staticmethod
    def scalar(value):
        return Distributions((), {(): _coerce_to_distrib(value)})

    @staticmethod
    def from_sweep(sweep):
        axis = sweep.axis()
        cells = {(value,): _coerce_to_distrib(value) for value in axis.values}
        return Distributions((axis,), cells)

    def is_unswept(self):
        return len(self.axes) == 0

    def only_distribution(self):
        return self.cells[()]

    def lookup(self, combined_axes, coordinates):
        if self.is_unswept():
            return self.only_distribution()

        index_by_key = {axis.key: idx for idx, axis in enumerate(combined_axes)}
        local_coordinates = tuple(coordinates[index_by_key[axis.key]] for axis in self.axes)
        return self.cells[local_coordinates]

    def round_probabilities(self, digits):
        if not digits:
            return self
        for distrib in self.cells.values():
            for outcome, probability in list(distrib.items()):
                distrib[outcome] = round(probability, digits)
        return self

    def _display_key(self, coordinates):
        if len(self.axes) == 1:
            axis = self.axes[0]
            value = coordinates[0]
            if axis.name.startswith("sweep_"):
                return value
            return "{}={}".format(axis.name, value)
        parts = []
        for axis, value in zip(self.axes, coordinates):
            label = axis.name if not axis.name.startswith("sweep_") else axis.key
            parts.append("{}={}".format(label, value))
        return tuple(parts)

    def __repr__(self):
        if self.is_unswept():
            return repr(self.only_distribution())
        rendered = {}
        for coordinates, distrib in self.cells.items():
            rendered[self._display_key(coordinates)] = distrib.distrib
        return str(rendered)


def _coerce_to_distrib(value):
    if isinstance(value, Distrib):
        return value
    if isinstance(value, Distributions):
        if not value.is_unswept():
            runtime_error("expected an unswept value here")
        return value.only_distribution()
    if isinstance(value, (int, float, str)):
        return Distrib({value: 1})
    runtime_error("can't convert {} to a distribution".format(type(value)))


def _coerce_to_distributions(value):
    if isinstance(value, Distributions):
        return value
    if isinstance(value, Sweep):
        return Distributions.from_sweep(value)
    return Distributions.scalar(value)


def _ordered_numeric_outcomes(distrib, opname):
    outcomes = list(distrib.keys())
    for outcome in outcomes:
        _require_numeric(outcome, opname)
    return tuple(sorted(outcomes))


def _union_axes(distribution_sets):
    axes = []
    seen = set()
    for distribution_set in distribution_sets:
        for axis in distribution_set.axes:
            if axis.key not in seen:
                axes.append(axis)
                seen.add(axis.key)
    return tuple(axes)


def lift_sweeps(function):
    """Lift a plain distribution operator over all sweep assignments."""

    @wraps(function)
    def wrapped(*args):
        distribution_sets = [_coerce_to_distributions(arg) for arg in args]
        combined_axes = _union_axes(distribution_sets)
        coordinates_space = [()] if not combined_axes else product(*(axis.values for axis in combined_axes))
        cells = {}
        for coordinates in coordinates_space:
            plain_args = [distribution_set.lookup(combined_axes, coordinates) for distribution_set in distribution_sets]
            cells[coordinates] = _coerce_to_distrib(function(*plain_args))
        return Distributions(combined_axes, cells)

    return wrapped


def _require_numeric(value, opname):
    if not isinstance(value, (int, float)):
        runtime_error(
            "{} expects numeric outcomes, got {}".format(opname, type(value)),
            hint="Convert the expression to numbers before using {}.".format(opname),
        )


def _require_int(value, opname):
    if not isinstance(value, int):
        runtime_error(
            "{} expects integer outcomes, got {}".format(opname, type(value)),
            hint="Dice counts, sides, and indexes must be integers.",
        )


def _require_keep_count(n, keep, opname):
    _require_int(n, opname)
    _require_int(keep, opname)
    if keep < 0 or keep > n:
        runtime_error(
            "{} expects keep count between 0 and number of dice".format(opname),
            hint="Use a keep count between 0 and {}.".format(n),
        )


def _pairwise_numeric(left, right, operator, opname):
    result = Distrib()
    for left_value, left_probability in left.items():
        _require_numeric(left_value, opname)
        for right_value, right_probability in right.items():
            _require_numeric(right_value, opname)
            result[operator(left_value, right_value)] += left_probability * right_probability
    return result


def _bool_mass(condition):
    invalid = [outcome for outcome in condition.keys() if outcome not in (TRUE, FALSE)]
    if invalid:
        runtime_error(
            "branching expects boolean outcomes, got {}".format(invalid),
            hint="Use a comparison like 'd20 >= 15' before '->'.",
        )
    return condition[TRUE], condition[FALSE]


def _sample_from_distribution(distrib, rng=None):
    total = sum(distrib.probabilities())
    if total < 0:
        runtime_error("distribution has negative total probability")
    if total == 0:
        return Distrib()
    if total > 1 + 1e-9:
        runtime_error("sampling expects probability mass <= 1, got {}".format(total))

    rng = rng if rng is not None else random
    threshold = rng.random()
    if threshold > total:
        return Distrib()

    cumulative = 0
    last_outcome = None
    for outcome, probability in distrib.items():
        last_outcome = outcome
        cumulative += probability
        if threshold <= cumulative:
            return Distrib({outcome: 1})
    return Distrib({last_outcome: 1}) if last_outcome is not None else Distrib()


def _lookup_projected(axes, cells, combined_axes, coordinates, default):
    if not axes:
        return cells.get((), default)
    index_by_key = {axis.key: idx for idx, axis in enumerate(combined_axes)}
    local_coordinates = tuple(coordinates[index_by_key[axis.key]] for axis in axes)
    return cells.get(local_coordinates, default)


def _fixed_axis_distribution(axes, coordinates):
    return Distributions(axes, {coordinates: Distrib({0: 1})})


def _accumulate_distribution_contributions(contributions):
    if not contributions:
        return Distributions.scalar(Distrib())

    combined_axes = _union_axes([Distributions(axes, cells) for axes, cells in contributions])
    coordinates_space = [()] if not combined_axes else product(*(axis.values for axis in combined_axes))
    cells = {}
    for coordinates in coordinates_space:
        distrib = Distrib()
        for axes, contribution_cells in contributions:
            projected = _lookup_projected(axes, contribution_cells, combined_axes, coordinates, None)
            if not projected:
                continue
            for outcome, probability in projected.items():
                distrib[outcome] = distrib[outcome] + probability
        cells[coordinates] = distrib
    return Distributions(combined_axes, cells if cells else {(): Distrib()})


def _resolve_target_axis(value, axis_name):
    if not isinstance(axis_name, str):
        runtime_error(
            "sumover expects a string axis name",
            hint='Pass the axis name as a string, for example sumover("party", value).',
        )

    matches = [axis for axis in value.axes if axis.name == axis_name and axis.name != axis.key]
    if not matches:
        runtime_error(
            "sumover could not find named axis {}".format(axis_name),
            hint="Create a named sweep like [party:1, 2, 3] before calling sumover.",
        )
    if len(matches) > 1:
        runtime_error("sumover found multiple axes named {}".format(axis_name))
    return matches[0]


def _resolve_total_axis(value):
    if not value.axes or len(value.axes) != 1:
        runtime_error(
            "total expects exactly one named axis",
            hint="Call total on a single named sweep like [party:1, 2, 3].",
        )

    axis = value.axes[0]
    if axis.name == axis.key:
        runtime_error(
            "total expects exactly one named axis",
            hint="Name the sweep first, for example [party:1, 2, 3].",
        )
    return axis


def _coordinates_without_axis(axes, coordinates, target_key):
    return tuple(
        coordinate
        for axis, coordinate in zip(axes, coordinates)
        if axis.key != target_key
    )


def _sum_axis(add_function, value, target_axis):
    distributions = _coerce_to_distributions(value)
    remaining_axes = tuple(axis for axis in distributions.axes if axis.key != target_axis.key)
    grouped = {}

    for coordinates, distrib in distributions.cells.items():
        remaining_coordinates = _coordinates_without_axis(distributions.axes, coordinates, target_axis.key)
        grouped.setdefault(remaining_coordinates, []).append(distrib)

    cells = {}
    for remaining_coordinates, distribs in grouped.items():
        reduced = 0
        for distrib in distribs:
            reduced = add_function(reduced, distrib)
        reduced_value = _coerce_to_distributions(reduced)
        if not reduced_value.is_unswept():
            runtime_error("sumover reduction produced an unexpected sweep")
        cells[remaining_coordinates] = reduced_value.only_distribution()

    if not cells:
        return Distributions.scalar(0)
    return Distributions(remaining_axes, cells)


def _roll_plain(n, s):
    _require_int(n, "roll")
    _require_int(s, "roll")
    if n < 0 or s <= 0:
        runtime_error(
            "roll expects positive sides and a non-negative dice count",
            hint="Examples: 2d6, 1d20, or 0d6.",
        )
    if n == 0:
        return Distrib({0: 1})

    results = Distrib()
    for p in range(1, s * n + 1):
        c = (p - n) // s
        probability = sum(
            [(-1) ** k * comb(n, k) * comb(p - s * k - 1, n - 1) for k in range(0, c + 1)]
        ) / s ** n
        if probability != 0:
            results[p] = probability
    return results


@lift_sweeps
def choose(left, right):
    result = Distrib()
    for selected_value, selection_probability in right.items():
        if selected_value in left.keys():
            result[selected_value] += left[selected_value] * selection_probability
    return result


@lift_sweeps
def choose_single(left, right):
    result = Distrib()
    for selected_value, selection_probability in right.items():
        result[left[selected_value]] += selection_probability
    return result


@lift_sweeps
def res(condition, distrib):
    true_mass, _ = _bool_mass(condition)
    result = Distrib()
    for outcome, probability in distrib.items():
        result[outcome] += true_mass * probability
    return result


@lift_sweeps
def mean(value):
    return Distrib({value.average(): 1})


@lift_sweeps
def mass(value):
    return Distrib({value.total_probability(): 1})


@lift_sweeps
def var(value):
    return Distrib({value.variance(): 1})


@lift_sweeps
def std(value):
    return Distrib({value.stddev(): 1})


@lift_sweeps
def sample(value):
    return _sample_from_distribution(value)


@lift_sweeps
def cum(value):
    result = Distrib()
    cumulative = 0
    for outcome in _ordered_numeric_outcomes(value, "cum"):
        cumulative += value[outcome]
        result[outcome] = cumulative
    return result


@lift_sweeps
def surv(value):
    result = Distrib()
    remaining = value.total_probability()
    for outcome in _ordered_numeric_outcomes(value, "surv"):
        remaining -= value[outcome]
        result[outcome] = remaining
    return result


@lift_sweeps
def reselse(condition, distrib_if, distrib_else):
    true_mass, false_mass = _bool_mass(condition)
    result = Distrib()
    for outcome, probability in distrib_if.items():
        result[outcome] += true_mass * probability
    for outcome, probability in distrib_else.items():
        result[outcome] += false_mass * probability
    return result


def reselsediv(condition, distrib):
    return reselse(condition, distrib, div(distrib, 2))


@lift_sweeps
def roll(n, s):
    result = Distrib()
    for dice_count, dice_count_probability in n.items():
        _require_int(dice_count, "roll")
        for sides, sides_probability in s.items():
            _require_int(sides, "roll")
            rolled = _roll_plain(dice_count, sides)
            weight = dice_count_probability * sides_probability
            for outcome, probability in rolled.items():
                result[outcome] += weight * probability
    return result


def rollsingle(dice):
    return roll(1, dice)


@lift_sweeps
def rolladvantage(dice):
    result = Distrib()
    for dice_sides, dice_probability in dice.items():
        _require_int(dice_sides, "advantage")
        if dice_sides <= 0:
            runtime_error("can't roll advantage with non-positive dice sides")
        for outcome in range(1, dice_sides + 1):
            advantage_probability = 2 / dice_sides ** 2 * (outcome - 1) + (1 / dice_sides) ** 2
            result[outcome] += dice_probability * advantage_probability
    return result


@lift_sweeps
def rolldisadvantage(dice):
    result = Distrib()
    for dice_sides, dice_probability in dice.items():
        _require_int(dice_sides, "disadvantage")
        if dice_sides <= 0:
            runtime_error("can't roll disadvantage with non-positive dice sides")
        for outcome in range(1, dice_sides + 1):
            disadvantage_probability = 2 / dice_sides ** 2 * (dice_sides - outcome) + (1 / dice_sides) ** 2
            result[outcome] += dice_probability * disadvantage_probability
    return result


def _rollhigh_plain(n, s, nh):
    _require_int(n, "rollhigh")
    _require_int(s, "rollhigh")
    _require_keep_count(n, nh, "rollhigh")
    if n < 0 or s <= 0 or nh < 0:
        runtime_error("rollhigh expects positive sides and non-negative counts")

    def count_children(sides, n_left, results, distrib):
        if n_left == 0:
            distrib[sum(results)] += 1
            return
        for value in range(1, sides + 1):
            results_min = min(results)
            new_results = results.copy()
            if value > results_min:
                new_results[results.index(results_min)] = value
            count_children(sides, n_left - 1, new_results, distrib)

    combinations = Distrib()
    count_children(s, n, [0] * nh, combinations)
    total = s ** n
    for key, value in list(combinations.items()):
        combinations[key] = value / total
    return combinations


def _rolllow_plain(n, s, nl):
    _require_int(n, "rolllow")
    _require_int(s, "rolllow")
    _require_keep_count(n, nl, "rolllow")
    if n < 0 or s <= 0 or nl < 0:
        runtime_error("rolllow expects positive sides and non-negative counts")

    def count_children(sides, n_left, results, distrib):
        if n_left == 0:
            distrib[sum(results)] += 1
            return
        for value in range(1, sides + 1):
            results_max = max(results)
            new_results = results.copy()
            if value < results_max:
                new_results[results.index(results_max)] = value
            count_children(sides, n_left - 1, new_results, distrib)

    combinations = Distrib()
    count_children(s, n, [inf] * nl, combinations)
    total = s ** n
    for key, value in list(combinations.items()):
        combinations[key] = value / total
    return combinations


@lift_sweeps
def rollhigh(n, s, nh):
    result = Distrib()
    for dice_count, dice_count_probability in n.items():
        for sides, sides_probability in s.items():
            for keep_count, keep_probability in nh.items():
                rolled = _rollhigh_plain(dice_count, sides, keep_count)
                weight = dice_count_probability * sides_probability * keep_probability
                for outcome, probability in rolled.items():
                    result[outcome] += weight * probability
    return result


@lift_sweeps
def rolllow(n, s, nl):
    result = Distrib()
    for dice_count, dice_count_probability in n.items():
        for sides, sides_probability in s.items():
            for keep_count, keep_probability in nl.items():
                rolled = _rolllow_plain(dice_count, sides, keep_count)
                weight = dice_count_probability * sides_probability * keep_probability
                for outcome, probability in rolled.items():
                    result[outcome] += weight * probability
    return result


@lift_sweeps
def add(left, right):
    return _pairwise_numeric(left, right, lambda a, b: a + b, "add")


@lift_sweeps
def sub(left, right):
    return _pairwise_numeric(left, right, lambda a, b: a - b, "sub")


@lift_sweeps
def mul(left, right):
    return _pairwise_numeric(left, right, lambda a, b: a * b, "mul")


@lift_sweeps
def div(left, right):
    result = Distrib()
    for left_value, left_probability in left.items():
        _require_numeric(left_value, "div")
        for right_value, right_probability in right.items():
            _require_numeric(right_value, "div")
            if right_value == 0:
                runtime_error("can't divide by zero")
            result[left_value // right_value] += left_probability * right_probability
    return result


def _compare_plain(left, right, operator):
    if operator not in ["<=", ">=", "<", ">", "=="]:
        runtime_error("unknown operator {}".format(operator))

    result = Distrib()
    for left_value, left_probability in left.items():
        for right_value, right_probability in right.items():
            comparison_true = False
            if operator == "<=":
                comparison_true = left_value <= right_value
            elif operator == ">=":
                comparison_true = left_value >= right_value
            elif operator == "<":
                comparison_true = left_value < right_value
            elif operator == ">":
                comparison_true = left_value > right_value
            elif operator == "==":
                comparison_true = left_value == right_value
            outcome = TRUE if comparison_true else FALSE
            result[outcome] += left_probability * right_probability
    return result


def greaterorequal(left, right):
    @lift_sweeps
    def apply(distrib_left, distrib_right):
        return _compare_plain(distrib_left, distrib_right, ">=")

    return apply(left, right)


def greater(left, right):
    @lift_sweeps
    def apply(distrib_left, distrib_right):
        return _compare_plain(distrib_left, distrib_right, ">")

    return apply(left, right)


def equal(left, right):
    @lift_sweeps
    def apply(distrib_left, distrib_right):
        return _compare_plain(distrib_left, distrib_right, "==")

    return apply(left, right)


def lessorequal(left, right):
    @lift_sweeps
    def apply(distrib_left, distrib_right):
        return _compare_plain(distrib_left, distrib_right, "<=")

    return apply(left, right)


def less(left, right):
    @lift_sweeps
    def apply(distrib_left, distrib_right):
        return _compare_plain(distrib_left, distrib_right, "<")

    return apply(left, right)


def repeat_sum_with(add_function, count, value):
    count_value = _coerce_to_distributions(count)
    contributions = []

    for count_coordinates, count_distrib in count_value.cells.items():
        count_items = list(count_distrib.items())
        if len(count_items) != 1:
            runtime_error(
                "repeat_sum expects a deterministic count per sweep point",
                hint="Use a fixed integer count or a sweep of fixed counts, not a random distribution like d6.",
            )

        count_outcome, count_probability = count_items[0]
        if count_probability != 1:
            runtime_error(
                "repeat_sum expects a deterministic count per sweep point",
                hint="Use a fixed integer count or a sweep of fixed counts, not a random distribution like d6.",
            )
        if not isinstance(count_outcome, int) or count_outcome < 0:
            runtime_error(
                "repeat_sum expects a non-negative integer count",
                hint="Use 0 or a positive integer count.",
            )

        repeated = 0
        for _ in range(count_outcome):
            repeated = add_function(repeated, value)

        repeated_value = _coerce_to_distributions(repeated)
        count_selection = _fixed_axis_distribution(count_value.axes, count_coordinates)
        combined_axes = _union_axes([count_selection, repeated_value])
        coordinates_space = [()] if not combined_axes else product(*(axis.values for axis in combined_axes))
        cells = {}
        for coordinates in coordinates_space:
            if _lookup_projected(count_value.axes, {count_coordinates: 1}, combined_axes, coordinates, 0) != 1:
                continue
            cells[coordinates] = repeated_value.lookup(combined_axes, coordinates)
        contributions.append((combined_axes, cells))

    return _accumulate_distribution_contributions(contributions)


def repeat_sum(count, value):
    return repeat_sum_with(add, count, value)


def sumover_with(add_function, axis_name, value):
    distributions = _coerce_to_distributions(value)
    target_axis = _resolve_target_axis(distributions, axis_name)
    return _sum_axis(add_function, distributions, target_axis)


def sumover(axis_name, value):
    return sumover_with(add, axis_name, value)


def total_with(add_function, value):
    distributions = _coerce_to_distributions(value)
    target_axis = _resolve_total_axis(distributions)
    return _sum_axis(add_function, distributions, target_axis)


def total(value):
    return total_with(add, value)


def render(*args):
    viewer = _get_viewer()

    if not args:
        runtime_error("render expects at least one expression")

    if len(args) == 1:
        try:
            render_outcome = viewer.render_result(args[0])
        except Exception as error:
            message = str(error)
            if message.startswith("Viewer exception: "):
                message = message[len("Viewer exception: "):]
            runtime_error(message)
        return render_outcome.output_path

    if len(args) % 2 != 0:
        runtime_error(
            "render comparisons require a label for every expression",
            hint='Call render(value1, "Label 1", value2, "Label 2").',
        )

    entries = []
    for index in range(0, len(args), 2):
        label = args[index + 1]
        if not isinstance(label, str):
            runtime_error("render comparison labels must be strings")
        entries.append((label, args[index]))

    if len(entries) < 2:
        runtime_error("render comparisons need at least two expressions")

    try:
        render_outcome = viewer.render_comparison(entries)
    except Exception as error:
        message = str(error)
        if message.startswith("Viewer exception: "):
            message = message[len("Viewer exception: "):]
        runtime_error(message)
    return render_outcome.output_path
