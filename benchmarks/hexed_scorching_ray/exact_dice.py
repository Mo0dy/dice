"""Exact dice backend for the benchmark workload."""

from __future__ import annotations

from dice import dice_interpreter

from .workload import ROOT, build_dice_program


def evaluate_exact_sweep():
    session = dice_interpreter(current_dir=str(ROOT))
    return session(build_dice_program())
