"""Shared plotting helpers for benchmark comparisons."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def exact_distribution_dict(distribution) -> dict[int, float]:
    return dict(distribution.items())


def cumulative_distribution(distribution: dict[int, float]) -> tuple[list[int], list[float]]:
    xs = sorted(distribution)
    ys = []
    running = 0.0
    for x_value in xs:
        running += distribution[x_value]
        ys.append(running)
    return xs, ys


def plot_representative_distributions(
    exact_sweep,
    sampled_runs,
    coordinates,
    plot_path: str,
    *,
    format_coordinate,
) -> None:
    os.environ.setdefault("MPLBACKEND", "Agg")
    mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
    mpl_config.mkdir(exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

    import matplotlib.pyplot as plt

    colors = ("#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2")
    figure, axes = plt.subplots(len(coordinates), 2, figsize=(16, 4.5 * len(coordinates)))
    if len(coordinates) == 1:
        axes = [axes]

    for row_axes, coordinate in zip(axes, coordinates):
        pmf_axis, cdf_axis = row_axes
        exact = exact_distribution_dict(exact_sweep.cells[coordinate])
        exact_xs = sorted(exact)
        exact_ys = [exact[x_value] for x_value in exact_xs]

        pmf_axis.bar(
            exact_xs,
            exact_ys,
            width=0.95,
            alpha=0.35,
            color="#1f77b4",
            label="dice exact",
        )

        exact_cdf_xs, exact_cdf_ys = cumulative_distribution(exact)
        cdf_axis.step(
            exact_cdf_xs,
            exact_cdf_ys,
            where="post",
            color="#1f77b4",
            linewidth=2.0,
            label="dice exact",
        )

        for color, (label, sampled_sweep) in zip(colors, sampled_runs.items()):
            sampled = sampled_sweep[coordinate]
            sampled_xs = sorted(sampled)
            sampled_ys = [sampled[x_value] for x_value in sampled_xs]
            pmf_axis.step(
                sampled_xs,
                sampled_ys,
                where="mid",
                color=color,
                linewidth=1.4,
                label=label,
            )
            sampled_cdf_xs, sampled_cdf_ys = cumulative_distribution(sampled)
            cdf_axis.step(
                sampled_cdf_xs,
                sampled_cdf_ys,
                where="post",
                color=color,
                linewidth=1.4,
                alpha=0.95,
                label=label,
            )

        pmf_axis.set_title("PMF: " + format_coordinate(coordinate))
        pmf_axis.set_xlabel("Damage")
        pmf_axis.set_ylabel("Probability")
        pmf_axis.legend(loc="upper right")

        cdf_axis.set_title("CDF: " + format_coordinate(coordinate))
        cdf_axis.set_xlabel("Damage")
        cdf_axis.set_ylabel("P(X <= x)")
        cdf_axis.set_ylim(0.0, 1.0)
        cdf_axis.legend(loc="lower right")

    figure.tight_layout()
    output = Path(plot_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
