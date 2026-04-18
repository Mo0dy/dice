#!/usr/bin/env python3

"""Run the Hexed Scorching Ray benchmark across exact and sampled backends."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from statistics import mean
import sys
from time import perf_counter


if __package__ in (None, ""):
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from benchmarks.hexed_scorching_ray import exact_dice, plotting, python_numpy, python_random_baseline, workload
else:
    from . import exact_dice, plotting, python_numpy, python_random_baseline, workload


BACKENDS = {
    "baseline": python_random_baseline,
    "numpy": python_numpy,
}


@dataclass(frozen=True)
class BenchmarkConfig:
    backends: tuple[str, ...]
    sample_counts: tuple[int, ...]
    validation_trials: int
    seed: int
    skip_validation: bool
    plot_path: str | None
    numpy_batch_size: int
    numpy_processes: int


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


def backend_kwargs(config: BenchmarkConfig, backend_name: str) -> dict[str, object]:
    if backend_name == "numpy":
        return {
            "batch_size": config.numpy_batch_size,
            "processes": config.numpy_processes,
        }
    return {}


def validate_backend(exact_sweep, backend_name: str, config: BenchmarkConfig) -> None:
    backend = BACKENDS[backend_name]
    failures = []
    for index, coordinate in enumerate(workload.VALIDATION_CELLS):
        sampled = backend.sample_coordinate_distribution(
            coordinate,
            config.validation_trials,
            seed=config.seed + index,
            **backend_kwargs(config, backend_name)
        )
        exact = exact_sweep.cells[coordinate]
        mean_error = abs(exact.average() - distribution_mean(sampled))
        tvd = total_variation_distance(exact, sampled)
        if mean_error > 0.35 or tvd > 0.075:
            failures.append((coordinate, mean_error, tvd))
    if failures:
        lines = ["validation failed for backend {}".format(backend_name)]
        for coordinate, mean_error, tvd in failures:
            lines.append("  {} mean_error={:.4f} tvd={:.4f}".format(coordinate, mean_error, tvd))
        raise SystemExit("\n".join(lines))


def parse_args() -> BenchmarkConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        action="append",
        choices=tuple(BACKENDS),
        default=None,
        help="Sampled backend to run. Repeat to compare more than one backend.",
    )
    parser.add_argument(
        "--sample-counts",
        nargs="+",
        type=int,
        default=(4000,),
        help="One or more Monte Carlo sample counts per cell.",
    )
    parser.add_argument(
        "--validation-trials",
        type=int,
        default=120000,
        help="Monte Carlo samples per validation cell.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1729,
        help="Base RNG seed for sampled backends.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip sampled-backend validation against the exact dice result.",
    )
    parser.add_argument(
        "--plot-path",
        default=None,
        help="Optional PNG output path for representative overlays.",
    )
    parser.add_argument(
        "--numpy-batch-size",
        type=int,
        default=50000,
        help="Batch size for the NumPy backend.",
    )
    parser.add_argument(
        "--numpy-processes",
        type=int,
        default=(os.cpu_count() or 1),
        help="Worker-process count for the NumPy backend. Trials are split evenly across workers.",
    )
    args = parser.parse_args()
    backends = tuple(dict.fromkeys(args.backend or ("numpy",)))
    sample_counts = tuple(dict.fromkeys(args.sample_counts))
    return BenchmarkConfig(
        backends=backends,
        sample_counts=sample_counts,
        validation_trials=args.validation_trials,
        seed=args.seed,
        skip_validation=args.skip_validation,
        plot_path=args.plot_path,
        numpy_batch_size=args.numpy_batch_size,
        numpy_processes=max(1, args.numpy_processes),
    )


def main() -> None:
    config = parse_args()

    print("Benchmark: hexed/blessed Scorching Ray sweep")
    print("Axis order: {}".format(", ".join(workload.AXIS_ORDER)))
    print(
        "Cells: {} (slots={} modes={} attack_bonuses={} bless_states={} ac_values={})".format(
            len(workload.SLOTS)
            * len(workload.MODES)
            * len(workload.ATTACK_BONUSES)
            * len(workload.BLESS_VALUES)
            * len(workload.ACS),
            len(workload.SLOTS),
            len(workload.MODES),
            len(workload.ATTACK_BONUSES),
            len(workload.BLESS_VALUES),
            len(workload.ACS),
        )
    )
    print("Sampled backends: {}".format(", ".join(config.backends)))
    print(
        "Python sample counts per cell: {}".format(
            ", ".join("{:,}".format(sample_count) for sample_count in config.sample_counts)
        )
    )
    if "numpy" in config.backends:
        print(
            "NumPy backend config: processes={} batch_size={:,}".format(
                config.numpy_processes,
                config.numpy_batch_size,
            )
        )

    exact_start = perf_counter()
    exact_sweep = exact_dice.evaluate_exact_sweep()
    exact_elapsed = perf_counter() - exact_start
    actual_axis_order = tuple(axis.name for axis in exact_sweep.axes)
    if actual_axis_order != workload.AXIS_ORDER:
        raise SystemExit(
            "unexpected exact axis order {} (expected {})".format(
                actual_axis_order,
                workload.AXIS_ORDER,
            )
        )
    print("Exact sweep time: {:.3f}s".format(exact_elapsed))

    if not config.skip_validation:
        for backend_name in config.backends:
            validation_start = perf_counter()
            validate_backend(exact_sweep, backend_name, config)
            validation_elapsed = perf_counter() - validation_start
            print(
                "Validation ({}) passed on {} cells with {} trials/cell in {:.3f}s".format(
                    backend_name,
                    len(workload.VALIDATION_CELLS),
                    config.validation_trials,
                    validation_elapsed,
                )
            )

    sampled_runs = {}
    for backend_index, backend_name in enumerate(config.backends, start=1):
        backend = BACKENDS[backend_name]
        for sample_index, sample_count in enumerate(config.sample_counts, start=1):
            run_seed = config.seed + backend_index * 10000 + sample_index
            sampled_start = perf_counter()
            sampled_sweep = backend.evaluate_sweep(
                samples_per_cell=sample_count,
                seed=run_seed,
                **backend_kwargs(config, backend_name)
            )
            sampled_elapsed = perf_counter() - sampled_start
            label = "{} {:,}".format(backend_name, sample_count)
            sampled_runs[label] = sampled_sweep

            print("Sampled sweep time ({}): {:.3f}s".format(label, sampled_elapsed))
            print("Sampled / exact slowdown ({}): {:.2f}x".format(label, sampled_elapsed / exact_elapsed))
            print("Representative cells ({}):".format(label))
            for line in summarize_cells(exact_sweep, sampled_sweep, workload.REPRESENTATIVE_CELLS):
                print("  " + line)

            mean_errors = []
            for coordinate in workload.REPRESENTATIVE_CELLS:
                exact = exact_sweep.cells[coordinate]
                sampled = sampled_sweep[coordinate]
                mean_errors.append(abs(exact.average() - distribution_mean(sampled)))
            print("Representative mean abs error ({}): {:.4f}".format(label, mean(mean_errors)))

    if config.plot_path:
        plotting.plot_representative_distributions(
            exact_sweep,
            sampled_runs,
            workload.REPRESENTATIVE_CELLS,
            config.plot_path,
        )
        print("Plot written to {}".format(config.plot_path))


if __name__ == "__main__":
    main()
