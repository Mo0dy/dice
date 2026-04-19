"""Plotting helpers for benchmark comparisons."""

from __future__ import annotations

from benchmarks.plotting_common import (
    plot_representative_distributions as _plot_representative_distributions,
    plot_single_coordinate_pmf as _plot_single_coordinate_pmf,
)

from .workload import format_coordinate


def plot_representative_distributions(exact_sweep, sampled_runs, coordinates, plot_path: str) -> None:
    _plot_representative_distributions(
        exact_sweep,
        sampled_runs,
        coordinates,
        plot_path,
        format_coordinate=format_coordinate,
    )


def plot_single_coordinate_pmf(exact_sweep, sampled_runs, coordinate, plot_path: str) -> None:
    _plot_single_coordinate_pmf(
        exact_sweep,
        sampled_runs,
        coordinate,
        plot_path,
        format_coordinate=format_coordinate,
    )
