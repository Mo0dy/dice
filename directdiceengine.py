#!/usr/bin/env python3

"""Sampling-based reference engine and stochastic validation helpers."""

from collections import defaultdict
import random
import time

from diceengine import (
    FALSE,
    TRUE,
    Diceengine,
    Distrib,
    Distributions,
    Sweep,
    _sample_from_distribution,
    _require_keep_count,
    lift_sweeps,
)
from diceparser import DiceParser
from interpreter import Interpreter
from lexer import Lexer


class SampledDistrib(Distrib):
    """One sampled outcome plus the exact distribution it came from."""

    def __init__(self, sampled=None, exact=None):
        super().__init__(sampled)
        self.exact = exact if exact is not None else Distrib(dict(self.distrib))

def _degenerate(outcome):
    if outcome is None:
        return Distrib()
    return Distrib({outcome: 1})


def _exact_of(distrib):
    return distrib.exact if isinstance(distrib, SampledDistrib) else distrib


def _exact_call(function, *args):
    result = function(*args)
    if isinstance(result, Distributions):
        if not result.is_unswept():
            raise Exception("Direct backend expected unswept exact result")
        return result.only_distribution()
    return result


def _sampled_result(outcome, exact):
    return SampledDistrib(_degenerate(outcome).distrib, exact=exact)


class DirectDiceEngine(object):
    """Sampling backend mirroring the exact engine one execution at a time."""

    def __init__(self, seed=None, rng=None):
        self.rng = rng if rng is not None else random.Random(seed)

    def _lift_unary(self, value, operation):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_of(distrib)
            sampled = _sample_from_distribution(distrib, self.rng)
            return _sampled_result(operation(next(iter(sampled.keys()), None)), exact)

        return apply(value)

    def _lift_binary(self, left, right, operation, exact_operation=None):
        @lift_sweeps
        def apply(left_distrib, right_distrib):
            exact = (
                exact_operation(_exact_of(left_distrib), _exact_of(right_distrib))
                if exact_operation is not None
                else None
            )
            left_sample = next(iter(_sample_from_distribution(left_distrib, self.rng).keys()), None)
            right_sample = next(iter(_sample_from_distribution(right_distrib, self.rng).keys()), None)
            return _sampled_result(operation(left_sample, right_sample), exact)

        return apply(left, right)

    def _lift_ternary(self, left, middle, right, operation, exact_operation=None):
        @lift_sweeps
        def apply(left_distrib, middle_distrib, right_distrib):
            exact = (
                exact_operation(_exact_of(left_distrib), _exact_of(middle_distrib), _exact_of(right_distrib))
                if exact_operation is not None
                else None
            )
            left_sample = next(iter(_sample_from_distribution(left_distrib, self.rng).keys()), None)
            middle_sample = next(iter(_sample_from_distribution(middle_distrib, self.rng).keys()), None)
            right_sample = next(iter(_sample_from_distribution(right_distrib, self.rng).keys()), None)
            return _sampled_result(operation(left_sample, middle_sample, right_sample), exact)

        return apply(left, middle, right)

    def choose(self, left, right):
        @lift_sweeps
        def apply(left_distrib, right_distrib):
            exact = _exact_call(Diceengine.choose, _exact_of(left_distrib), _exact_of(right_distrib))
            sampled_left = next(iter(_sample_from_distribution(left_distrib, self.rng).keys()), None)
            sampled_right = next(iter(_sample_from_distribution(right_distrib, self.rng).keys()), None)
            if sampled_left is None or sampled_right is None:
                return _sampled_result(None, exact)
            return _sampled_result(sampled_left if sampled_left == sampled_right else None, exact)

        return apply(left, right)

    def choose_single(self, left, right):
        @lift_sweeps
        def apply(left_distrib, right_distrib):
            exact = _exact_call(Diceengine.choose_single, _exact_of(left_distrib), _exact_of(right_distrib))
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(left, right)

    def res(self, condition, distrib):
        return self._lift_binary(
            condition,
            distrib,
            lambda sampled_condition, sampled_value: sampled_value if sampled_condition == TRUE else None,
            exact_operation=lambda cond, dist: _exact_call(Diceengine.res, cond, dist),
        )

    def resunary(self, value):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.resunary, _exact_of(distrib))
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(value)

    def mean(self, value):
        return self.resunary(value)

    def prop(self, value):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.prop, _exact_of(distrib))
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(value)

    def mass(self, value):
        return self.prop(value)

    def variance(self, value):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.variance, _exact_of(distrib))
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(value)

    def stddev(self, value):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.stddev, _exact_of(distrib))
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(value)

    def sample(self, value):
        @lift_sweeps
        def apply(distrib):
            exact = _exact_of(distrib)
            sampled_value = next(iter(_sample_from_distribution(exact, self.rng).keys()), None)
            return _sampled_result(sampled_value, exact)

        return apply(value)

    def reselse(self, condition, distrib_if, distrib_else):
        def operation(sampled_condition, sampled_if, sampled_else):
            return sampled_if if sampled_condition == TRUE else sampled_else

        return self._lift_ternary(
            condition,
            distrib_if,
            distrib_else,
            operation,
            exact_operation=lambda cond, if_dist, else_dist: _exact_call(Diceengine.reselse, cond, if_dist, else_dist),
        )

    def reselsediv(self, condition, distrib):
        return self.reselse(condition, distrib, self.div(distrib, 2))

    def roll(self, n, s):
        def operation(sampled_n, sampled_s):
            if sampled_n is None or sampled_s is None:
                return None
            sampled_n = int(sampled_n)
            sampled_s = int(sampled_s)
            if sampled_n < 0 or sampled_s <= 0:
                Diceengine.exception("Roll expects positive sides and non-negative dice count")
            return sum(self.rng.randint(1, sampled_s) for _ in range(sampled_n))

        return self._lift_binary(
            n,
            s,
            operation,
            exact_operation=lambda left, right: _exact_call(Diceengine.roll, left, right),
        )

    def rollsingle(self, dice):
        return self.roll(1, dice)

    def rolladvantage(self, dice):
        def operation(sampled_sides):
            if sampled_sides is None:
                return None
            sampled_sides = int(sampled_sides)
            return max(self.rng.randint(1, sampled_sides), self.rng.randint(1, sampled_sides))

        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.rolladvantage, _exact_of(distrib))
            sampled = next(iter(_sample_from_distribution(distrib, self.rng).keys()), None)
            return _sampled_result(operation(sampled), exact)

        return apply(dice)

    def rolldisadvantage(self, dice):
        def operation(sampled_sides):
            if sampled_sides is None:
                return None
            sampled_sides = int(sampled_sides)
            return min(self.rng.randint(1, sampled_sides), self.rng.randint(1, sampled_sides))

        @lift_sweeps
        def apply(distrib):
            exact = _exact_call(Diceengine.rolldisadvantage, _exact_of(distrib))
            sampled = next(iter(_sample_from_distribution(distrib, self.rng).keys()), None)
            return _sampled_result(operation(sampled), exact)

        return apply(dice)

    def rollhigh(self, n, s, nh):
        def operation(sampled_n, sampled_s, sampled_keep):
            if sampled_n is None or sampled_s is None or sampled_keep is None:
                return None
            sampled_n = int(sampled_n)
            sampled_s = int(sampled_s)
            sampled_keep = int(sampled_keep)
            _require_keep_count(sampled_n, sampled_keep, "rollhigh")
            rolls = sorted((self.rng.randint(1, sampled_s) for _ in range(sampled_n)), reverse=True)
            return sum(rolls[:sampled_keep])

        return self._lift_ternary(
            n,
            s,
            nh,
            operation,
            exact_operation=lambda left, middle, right: _exact_call(Diceengine.rollhigh, left, middle, right),
        )

    def rolllow(self, n, s, nl):
        def operation(sampled_n, sampled_s, sampled_keep):
            if sampled_n is None or sampled_s is None or sampled_keep is None:
                return None
            sampled_n = int(sampled_n)
            sampled_s = int(sampled_s)
            sampled_keep = int(sampled_keep)
            _require_keep_count(sampled_n, sampled_keep, "rolllow")
            rolls = sorted(self.rng.randint(1, sampled_s) for _ in range(sampled_n))
            return sum(rolls[:sampled_keep])

        return self._lift_ternary(
            n,
            s,
            nl,
            operation,
            exact_operation=lambda left, middle, right: _exact_call(Diceengine.rolllow, left, middle, right),
        )

    def add(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else a + b,
            exact_operation=lambda l, r: _exact_call(Diceengine.add, l, r),
        )

    def sub(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else a - b,
            exact_operation=lambda l, r: _exact_call(Diceengine.sub, l, r),
        )

    def mul(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else a * b,
            exact_operation=lambda l, r: _exact_call(Diceengine.mul, l, r),
        )

    def div(self, left, right):
        def operation(sampled_left, sampled_right):
            if sampled_left is None or sampled_right is None:
                return None
            if sampled_right == 0:
                Diceengine.exception("Can't divide by zero")
            return sampled_left // sampled_right

        return self._lift_binary(left, right, operation, exact_operation=lambda l, r: _exact_call(Diceengine.div, l, r))

    def greaterorequal(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else (TRUE if a >= b else FALSE),
            exact_operation=lambda l, r: _exact_call(Diceengine.greaterorequal, l, r),
        )

    def greater(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else (TRUE if a > b else FALSE),
            exact_operation=lambda l, r: _exact_call(Diceengine.greater, l, r),
        )

    def equal(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else (TRUE if a == b else FALSE),
            exact_operation=lambda l, r: _exact_call(Diceengine.equal, l, r),
        )

    def lessorequal(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else (TRUE if a <= b else FALSE),
            exact_operation=lambda l, r: _exact_call(Diceengine.lessorequal, l, r),
        )

    def less(self, left, right):
        return self._lift_binary(
            left,
            right,
            lambda a, b: None if a is None or b is None else (TRUE if a < b else FALSE),
            exact_operation=lambda l, r: _exact_call(Diceengine.less, l, r),
        )


def _parse_text(text):
    parser = DiceParser(Lexer(text))
    return parser.parse() if (";" in text or "\n" in text) else parser.statement()


def _reset_sweeps():
    Sweep.counter = 0


def exact_evaluate(text):
    _reset_sweeps()
    ast = _parse_text(text)
    return Interpreter(ast).interpret()


def direct_sample(text, seed=None):
    _reset_sweeps()
    ast = _parse_text(text)
    engine = DirectDiceEngine(seed=seed)
    return Interpreter(ast, engine=engine).interpret()


def _accumulate_sample_counts(counts, sampled, samples_seen):
    if counts["axes"] is None:
        counts["axes"] = sampled.axes
    for coordinates, distrib in sampled.cells.items():
        cell_counts = counts["cells"][coordinates]
        for outcome, probability in distrib.items():
            cell_counts[outcome] += probability
    counts["samples"] = samples_seen


def _normalize_counts(counts):
    cells = {}
    sample_count = counts["samples"]
    for coordinates, cell_counts in counts["cells"].items():
        distrib = Distrib()
        for outcome, value in cell_counts.items():
            distrib[outcome] = value / sample_count
        cells[coordinates] = distrib
    if counts["axes"] is None:
        return Distributions.scalar(0)
    return Distributions(counts["axes"], cells if cells else {(): Distrib()})


def distribution_metrics(expected, empirical):
    max_abs = 0
    l1 = 0
    all_coordinates = set(expected.cells.keys()) | set(empirical.cells.keys())
    for coordinates in all_coordinates:
        expected_distrib = expected.cells.get(coordinates, Distrib())
        empirical_distrib = empirical.cells.get(coordinates, Distrib())
        outcomes = set(expected_distrib.keys()) | set(empirical_distrib.keys())
        for outcome in outcomes:
            diff = abs(expected_distrib[outcome] - empirical_distrib[outcome])
            max_abs = max(max_abs, diff)
            l1 += diff
    return {
        "max_abs": max_abs,
        "l1": l1,
        "tv": 0.5 * l1,
    }


def monte_carlo_validate(text, min_samples=2000, max_samples=40000, batch_size=2000, timeout_seconds=10, tolerance=0.05, seed=0):
    expected = exact_evaluate(text)
    counts = {
        "axes": None,
        "cells": defaultdict(lambda: defaultdict(float)),
        "samples": 0,
    }
    rng = random.Random(seed)
    start = time.monotonic()
    history = []
    samples_seen = 0

    while samples_seen < max_samples:
        if time.monotonic() - start > timeout_seconds:
            break

        batch_engine = DirectDiceEngine(rng=rng)
        batch_end = min(samples_seen + batch_size, max_samples)
        while samples_seen < batch_end:
            _reset_sweeps()
            ast = _parse_text(text)
            sampled = Interpreter(ast, engine=batch_engine).interpret()
            samples_seen += 1
            _accumulate_sample_counts(counts, sampled, samples_seen)

        empirical = _normalize_counts(counts)
        metrics = distribution_metrics(expected, empirical)
        history.append((samples_seen, metrics))
        if samples_seen >= min_samples and metrics["max_abs"] <= tolerance:
            return {
                "passed": True,
                "timed_out": False,
                "samples": samples_seen,
                "expected": expected,
                "empirical": empirical,
                "metrics": metrics,
                "history": history,
            }

    empirical = _normalize_counts(counts)
    metrics = distribution_metrics(expected, empirical)
    improving = len(history) >= 2 and history[-1][1]["max_abs"] < history[0][1]["max_abs"]
    return {
        "passed": False,
        "timed_out": time.monotonic() - start > timeout_seconds or samples_seen >= max_samples,
        "samples": samples_seen,
        "expected": expected,
        "empirical": empirical,
        "metrics": metrics,
        "history": history,
        "improving": improving,
    }
