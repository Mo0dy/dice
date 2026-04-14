#!/usr/bin/env python3

"""Sweep-aware probability primitives for the dice language."""

from dataclasses import dataclass
from itertools import product
from math import inf

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
                raise Exception("Distrib average expects numeric outcomes, got {}".format(type(outcome)))
            total += outcome * probability
        return total


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
            raise Exception("Sweep requires at least one value")
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
            raise Exception("Expected an unswept Distributions value")
        return value.only_distribution()
    if isinstance(value, (int, float, str)):
        return Distrib({value: 1})
    raise Exception("Can't convert {} to Distrib".format(type(value)))


def _coerce_to_distributions(value):
    if isinstance(value, Distributions):
        return value
    if isinstance(value, Sweep):
        return Distributions.from_sweep(value)
    return Distributions.scalar(value)


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
        raise Exception("{} expects numeric outcomes, got {}".format(opname, type(value)))


def _require_int(value, opname):
    if not isinstance(value, int):
        raise Exception("{} expects integer outcomes, got {}".format(opname, type(value)))


def _require_keep_count(n, keep, opname):
    _require_int(n, opname)
    _require_int(keep, opname)
    if keep < 0 or keep > n:
        raise Exception("{} expects keep count between 0 and number of dice".format(opname))


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
        raise Exception("Branching expects boolean outcomes, got {}".format(invalid))
    return condition[TRUE], condition[FALSE]


class Diceengine(object):
    """Arithmetic and sweep-aware helpers for dice semantics."""

    @staticmethod
    def exception(message):
        raise Exception("Diceengine exception: {}".format(message))

    @staticmethod
    def _roll_plain(n, s):
        _require_int(n, "roll")
        _require_int(s, "roll")
        if n < 0 or s <= 0:
            Diceengine.exception("Roll expects positive sides and non-negative dice count")
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

    @staticmethod
    @lift_sweeps
    def choose(left, right):
        result = Distrib()
        for selected_value, selection_probability in right.items():
            if selected_value in left.keys():
                result[selected_value] += left[selected_value] * selection_probability
        return result

    @staticmethod
    @lift_sweeps
    def choose_single(left, right):
        result = Distrib()
        for selected_value, selection_probability in right.items():
            result[left[selected_value]] += selection_probability
        return result

    @staticmethod
    @lift_sweeps
    def res(condition, distrib):
        true_mass, _ = _bool_mass(condition)
        result = Distrib()
        for outcome, probability in distrib.items():
            result[outcome] += true_mass * probability
        return result

    @staticmethod
    @lift_sweeps
    def resunary(value):
        return Distrib({value.average(): 1})

    @staticmethod
    @lift_sweeps
    def prop(value):
        return Distrib({value.total_probability(): 1})

    @staticmethod
    @lift_sweeps
    def reselse(condition, distrib_if, distrib_else):
        true_mass, false_mass = _bool_mass(condition)
        result = Distrib()
        for outcome, probability in distrib_if.items():
            result[outcome] += true_mass * probability
        for outcome, probability in distrib_else.items():
            result[outcome] += false_mass * probability
        return result

    @staticmethod
    def reselsediv(condition, distrib):
        return Diceengine.reselse(condition, distrib, Diceengine.div(distrib, 2))

    @staticmethod
    @lift_sweeps
    def roll(n, s):
        result = Distrib()
        for dice_count, dice_count_probability in n.items():
            _require_int(dice_count, "roll")
            for sides, sides_probability in s.items():
                _require_int(sides, "roll")
                rolled = Diceengine._roll_plain(dice_count, sides)
                weight = dice_count_probability * sides_probability
                for outcome, probability in rolled.items():
                    result[outcome] += weight * probability
        return result

    @staticmethod
    def rollsingle(dice):
        return Diceengine.roll(1, dice)

    @staticmethod
    @lift_sweeps
    def rolladvantage(dice):
        result = Distrib()
        for dice_sides, dice_probability in dice.items():
            _require_int(dice_sides, "advantage")
            if dice_sides <= 0:
                Diceengine.exception("Can't roll advantage with non-positive dice sides")
            for outcome in range(1, dice_sides + 1):
                advantage_probability = 2 / dice_sides ** 2 * (outcome - 1) + (1 / dice_sides) ** 2
                result[outcome] += dice_probability * advantage_probability
        return result

    @staticmethod
    @lift_sweeps
    def rolldisadvantage(dice):
        result = Distrib()
        for dice_sides, dice_probability in dice.items():
            _require_int(dice_sides, "disadvantage")
            if dice_sides <= 0:
                Diceengine.exception("Can't roll disadvantage with non-positive dice sides")
            for outcome in range(1, dice_sides + 1):
                disadvantage_probability = 2 / dice_sides ** 2 * (dice_sides - outcome) + (1 / dice_sides) ** 2
                result[outcome] += dice_probability * disadvantage_probability
        return result

    @staticmethod
    def _rollhigh_plain(n, s, nh):
        _require_int(n, "rollhigh")
        _require_int(s, "rollhigh")
        _require_keep_count(n, nh, "rollhigh")
        if n < 0 or s <= 0 or nh < 0:
            Diceengine.exception("rollhigh expects positive sides and non-negative counts")

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

    @staticmethod
    def _rolllow_plain(n, s, nl):
        _require_int(n, "rolllow")
        _require_int(s, "rolllow")
        _require_keep_count(n, nl, "rolllow")
        if n < 0 or s <= 0 or nl < 0:
            Diceengine.exception("rolllow expects positive sides and non-negative counts")

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

    @staticmethod
    @lift_sweeps
    def rollhigh(n, s, nh):
        result = Distrib()
        for dice_count, dice_count_probability in n.items():
            for sides, sides_probability in s.items():
                for keep_count, keep_probability in nh.items():
                    rolled = Diceengine._rollhigh_plain(dice_count, sides, keep_count)
                    weight = dice_count_probability * sides_probability * keep_probability
                    for outcome, probability in rolled.items():
                        result[outcome] += weight * probability
        return result

    @staticmethod
    @lift_sweeps
    def rolllow(n, s, nl):
        result = Distrib()
        for dice_count, dice_count_probability in n.items():
            for sides, sides_probability in s.items():
                for keep_count, keep_probability in nl.items():
                    rolled = Diceengine._rolllow_plain(dice_count, sides, keep_count)
                    weight = dice_count_probability * sides_probability * keep_probability
                    for outcome, probability in rolled.items():
                        result[outcome] += weight * probability
        return result

    @staticmethod
    @lift_sweeps
    def add(left, right):
        return _pairwise_numeric(left, right, lambda a, b: a + b, "add")

    @staticmethod
    @lift_sweeps
    def sub(left, right):
        return _pairwise_numeric(left, right, lambda a, b: a - b, "sub")

    @staticmethod
    @lift_sweeps
    def mul(left, right):
        return _pairwise_numeric(left, right, lambda a, b: a * b, "mul")

    @staticmethod
    @lift_sweeps
    def div(left, right):
        result = Distrib()
        for left_value, left_probability in left.items():
            _require_numeric(left_value, "div")
            for right_value, right_probability in right.items():
                _require_numeric(right_value, "div")
                if right_value == 0:
                    Diceengine.exception("Can't divide by zero")
                result[left_value // right_value] += left_probability * right_probability
        return result

    @staticmethod
    def _compare_plain(left, right, operator):
        if operator not in ["<=", ">=", "<", ">", "=="]:
            Diceengine.exception("Unknown operator {}".format(operator))

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

    @staticmethod
    def greaterorequal(left, right):
        @lift_sweeps
        def apply(distrib_left, distrib_right):
            return Diceengine._compare_plain(distrib_left, distrib_right, ">=")

        return apply(left, right)

    @staticmethod
    def greater(left, right):
        @lift_sweeps
        def apply(distrib_left, distrib_right):
            return Diceengine._compare_plain(distrib_left, distrib_right, ">")

        return apply(left, right)

    @staticmethod
    def equal(left, right):
        @lift_sweeps
        def apply(distrib_left, distrib_right):
            return Diceengine._compare_plain(distrib_left, distrib_right, "==")

        return apply(left, right)

    @staticmethod
    def lessorequal(left, right):
        @lift_sweeps
        def apply(distrib_left, distrib_right):
            return Diceengine._compare_plain(distrib_left, distrib_right, "<=")

        return apply(left, right)

    @staticmethod
    def less(left, right):
        @lift_sweeps
        def apply(distrib_left, distrib_right):
            return Diceengine._compare_plain(distrib_left, distrib_right, "<")

        return apply(left, right)


if __name__ == "__main__":
    print(Diceengine.rollhigh(3, 20, 1))
