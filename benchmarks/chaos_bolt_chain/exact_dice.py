"""Exact dice backend for the Chaos Bolt chain workload."""

from __future__ import annotations

from dataclasses import dataclass

from dice import dice_interpreter

from .workload import AXIS_ORDER, DEFAULT_CONFIG, ROOT, build_dice_program


@dataclass(frozen=True)
class ExactSweepResult:
    sweep: object
    cells: dict[tuple[object, ...], object]


def evaluate_exact_sweep(config=DEFAULT_CONFIG):
    session = dice_interpreter(current_dir=str(ROOT))
    sweep = session(build_dice_program(config))
    axis_names = tuple(axis.name for axis in sweep.axes)
    index_by_name = {name: axis_names.index(name) for name in AXIS_ORDER}
    cells = {}
    for coordinates, distribution in sweep.items():
        normalized = tuple(coordinates[index_by_name[name]] for name in AXIS_ORDER)
        cells[normalized] = distribution
    return ExactSweepResult(sweep=sweep, cells=cells)
