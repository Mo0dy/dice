"""Exact dice backend for the Chaos Bolt chain workload."""

from __future__ import annotations

from dataclasses import dataclass

from dice import dice_interpreter

from .workload import ROOT, build_dice_prelude


@dataclass(frozen=True)
class ExactProbeResult:
    cells: dict[tuple[object, ...], object]


def evaluate_coordinates(coordinates):
    session = dice_interpreter(current_dir=str(ROOT))
    session(build_dice_prelude())
    cells = {}
    for slot_level, mode, attack_bonus, bless, targets, ac in coordinates:
        session.assign("slot_level", slot_level)
        session.assign("mode", mode)
        session.assign("attack_bonus", attack_bonus)
        session.assign("bless", bless)
        session.assign("targets", targets)
        session.assign("ac", ac)
        cells[(slot_level, mode, attack_bonus, bless, targets, ac)] = session("chaos_chain()").only_distribution()
    return ExactProbeResult(cells)
