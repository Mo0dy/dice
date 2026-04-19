"""Shared benchmark reporting helpers."""

from __future__ import annotations


def cells_dict(result) -> dict[tuple[object, ...], object]:
    return result.cells if hasattr(result, "cells") else result


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
    exact_cells = cells_dict(exact_sweep)
    sampled_cells = cells_dict(sampled_sweep)
    for coordinate in coordinates:
        exact = exact_cells[coordinate]
        sampled = sampled_cells[coordinate]
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


def mean_absolute_error(exact_result, sampled_result, coordinates) -> float:
    exact_cells = cells_dict(exact_result)
    sampled_cells = cells_dict(sampled_result)
    errors = [
        abs(exact_cells[coordinate].average() - distribution_mean(sampled_cells[coordinate]))
        for coordinate in coordinates
    ]
    return sum(errors) / len(errors)


def sample_coordinates(backend, coordinates, trials: int, seed: int, **backend_kwargs) -> dict[tuple[object, ...], dict[int, float]]:
    sampled = {}
    for index, coordinate in enumerate(coordinates):
        sampled[coordinate] = backend.sample_coordinate_distribution(
            coordinate,
            trials,
            seed=seed + index,
            **backend_kwargs
        )
    return sampled


def markdown_table(headers, rows) -> str:
    widths = [len(header) for header in headers]
    string_rows = [[str(value) for value in row] for row in rows]
    for row in string_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    header_line = "| " + " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)) + " |"
    separator_line = "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |"
    row_lines = [
        "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |"
        for row in string_rows
    ]
    return "\n".join([header_line, separator_line] + row_lines)
