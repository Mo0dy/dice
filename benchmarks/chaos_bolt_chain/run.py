#!/usr/bin/env python3

"""Run the Chaos Bolt chain benchmark across exact and sampled backends."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys
from time import perf_counter


if __package__ in (None, ""):
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from benchmarks import common
    from benchmarks.chaos_bolt_chain import exact_dice, plotting, python_numpy, python_random_baseline, workload
else:
    from benchmarks import common
    from . import exact_dice, plotting, python_numpy, python_random_baseline, workload


BACKENDS = {
    "baseline": python_random_baseline,
    "numpy": python_numpy,
}

BACKEND_LABELS = {
    "baseline": "Naive Python Monte Carlo",
    "numpy": "Vectorized NumPy Monte Carlo",
}


@dataclass(frozen=True)
class BenchmarkConfig:
    sweep_config: workload.SweepConfig
    baseline_sample_counts: tuple[int, ...]
    numpy_sample_counts: tuple[int, ...]
    validation_trials: int
    seed: int
    skip_validation: bool
    plot_path: str | None
    numpy_batch_size: int
    numpy_processes: int


def parse_args() -> BenchmarkConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=tuple(workload.PRESETS),
        default=workload.DEFAULT_CONFIG.label,
        help="Configured full-sweep workload to benchmark.",
    )
    parser.add_argument(
        "--sample-counts",
        nargs="+",
        type=int,
        default=None,
        help="Shared sample counts for all sampled backends.",
    )
    parser.add_argument(
        "--baseline-sample-counts",
        nargs="+",
        type=int,
        default=None,
        help="Sample counts for the naive Python backend.",
    )
    parser.add_argument(
        "--numpy-sample-counts",
        nargs="+",
        type=int,
        default=None,
        help="Sample counts for the NumPy backend.",
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
    shared_counts = tuple(dict.fromkeys(args.sample_counts or ()))
    baseline_counts = tuple(dict.fromkeys(args.baseline_sample_counts or shared_counts or (4000,)))
    numpy_counts = tuple(dict.fromkeys(args.numpy_sample_counts or shared_counts or (4000, 32000)))
    return BenchmarkConfig(
        sweep_config=workload.get_config(args.preset),
        baseline_sample_counts=baseline_counts,
        numpy_sample_counts=numpy_counts,
        validation_trials=args.validation_trials,
        seed=args.seed,
        skip_validation=args.skip_validation,
        plot_path=args.plot_path,
        numpy_batch_size=args.numpy_batch_size,
        numpy_processes=max(1, args.numpy_processes),
    )


def backend_kwargs(config: BenchmarkConfig, backend_name: str) -> dict[str, object]:
    kwargs = {"config": config.sweep_config}
    if backend_name == "numpy":
        kwargs.update(
            {
                "batch_size": config.numpy_batch_size,
                "processes": config.numpy_processes,
            }
        )
    return kwargs


def validate_backend(exact_result, backend_name: str, config: BenchmarkConfig) -> None:
    backend = BACKENDS[backend_name]
    failures = []
    for index, coordinate in enumerate(workload.validation_cells(config.sweep_config)):
        sampled = backend.sample_coordinate_distribution(
            coordinate,
            config.validation_trials,
            seed=config.seed + index,
            **backend_kwargs(config, backend_name)
        )
        exact = common.cells_dict(exact_result)[coordinate]
        mean_error = abs(exact.average() - common.distribution_mean(sampled))
        tvd = common.total_variation_distance(exact, sampled)
        if mean_error > 0.6 or tvd > 0.10:
            failures.append((coordinate, mean_error, tvd))
    if failures:
        lines = ["validation failed for backend {}".format(backend_name)]
        for coordinate, mean_error, tvd in failures:
            lines.append("  {} mean_error={:.4f} tvd={:.4f}".format(coordinate, mean_error, tvd))
        raise SystemExit("\n".join(lines))


def benchmark_rows(config: BenchmarkConfig):
    return (
        ("baseline", config.baseline_sample_counts),
        ("numpy", config.numpy_sample_counts),
    )


def format_ratio(value: float) -> str:
    return "<0.01x" if value < 0.01 else "{:.2f}x".format(value)


def main() -> None:
    config = parse_args()
    coordinate_count = len(tuple(workload.coordinate_space(config.sweep_config)))
    representative_cells = workload.representative_cells(config.sweep_config)

    print("Benchmark: Chaos Bolt chain")
    print("Preset: {}".format(config.sweep_config.label))
    print("Axis order: {}".format(", ".join(workload.AXIS_ORDER)))
    print("Timing scope: full sweep across {:,} cells".format(coordinate_count))
    print(
        "Sample counts: baseline={} numpy={}".format(
            ", ".join("{:,}".format(count) for count in config.baseline_sample_counts) or "off",
            ", ".join("{:,}".format(count) for count in config.numpy_sample_counts) or "off",
        )
    )
    print(
        "NumPy config: processes={} batch_size={:,}".format(
            config.numpy_processes,
            config.numpy_batch_size,
        )
    )

    exact_start = perf_counter()
    exact_result = exact_dice.evaluate_exact_sweep(config.sweep_config)
    exact_elapsed = perf_counter() - exact_start

    if not config.skip_validation:
        for backend_name, _sample_counts in benchmark_rows(config):
            validate_backend(exact_result, backend_name, config)

    sampled_runs = {}
    table_rows = [
        (
            "dice exact",
            "-",
            "full sweep ({:,} cells)".format(coordinate_count),
            "{:.3f}".format(exact_elapsed),
            "1.00x",
            "0.0000",
        )
    ]

    for backend_index, (backend_name, sample_counts) in enumerate(benchmark_rows(config), start=1):
        backend = BACKENDS[backend_name]
        for sample_index, sample_count in enumerate(sample_counts, start=1):
            run_seed = config.seed + backend_index * 10000 + sample_index
            sampled_start = perf_counter()
            sampled_result = backend.evaluate_sweep(
                samples_per_cell=sample_count,
                seed=run_seed,
                **backend_kwargs(config, backend_name)
            )
            sampled_elapsed = perf_counter() - sampled_start
            label = "{} {:,}".format(backend_name, sample_count)
            sampled_runs[label] = sampled_result
            error = common.mean_absolute_error(exact_result, sampled_result, representative_cells)
            table_rows.append(
                (
                    BACKEND_LABELS[backend_name],
                    "{:,}".format(sample_count),
                    "full sweep ({:,} cells)".format(coordinate_count),
                    "{:.3f}".format(sampled_elapsed),
                    format_ratio(sampled_elapsed / exact_elapsed),
                    "{:.4f}".format(error),
                )
            )

    print()
    print(
        common.markdown_table(
            ("Backend", "Samples / cell", "Scope", "Time (s)", "vs dice", "Rep. mean abs err"),
            table_rows,
        )
    )

    print()
    print("Representative cells:")
    for label, sampled_result in sampled_runs.items():
        print("  {}:".format(label))
        for line in common.summarize_cells(exact_result, sampled_result, representative_cells):
            print("    " + line)

    if config.plot_path:
        headline_runs = {
            label: sampled_runs[label]
            for label in sampled_runs
            if label in {"numpy 4,000", "numpy 32,000"}
        }
        plotting.plot_representative_distributions(
            exact_result,
            headline_runs if headline_runs else sampled_runs,
            representative_cells,
            config.plot_path,
        )
        print()
        print("Plot written to {}".format(config.plot_path))


if __name__ == "__main__":
    main()
