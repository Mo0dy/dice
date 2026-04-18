"""Shared benchmark reporting helpers."""

from __future__ import annotations


def distribution_mean(distribution: dict[int, float]) -> float:
    return sum(outcome * probability for outcome, probability in distribution.items())


def total_variation_distance(exact_distribution, sampled_distribution: dict[int, float]) -> float:
    outcomes = set(sampled_distribution)
    outcomes.update(exact_distribution.keys())
    total = 0.0
    for outcome in outcomes:
        total += abs(exact_distribution[outcome] - sampled_distribution.get(outcome, 0.0))
    return total / 2.0


def summarize_cells(exact_sweep, sampled_sweep, coordinates) -> list[str]:
    lines = []
    for coordinate in coordinates:
        exact = exact_sweep.cells[coordinate]
        sampled = sampled_sweep[coordinate]
        lines.append(
            "{} exact_mean={:.3f} sampled_mean={:.3f} exact_support={} sampled_support={}".format(
                coordinate,
                exact.average(),
                distribution_mean(sampled),
                len(exact.items()),
                len(sampled),
            )
        )
    return lines
