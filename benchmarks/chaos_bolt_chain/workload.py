"""Shared workload definition for the Chaos Bolt chain benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
AXIS_ORDER = ("SLOT", "MODE", "ATTACK", "BLESS", "TARGETS", "AC")
CANONICAL_REPRESENTATIVE_CELLS = (
    (1, "normal", 5, 0, 2, 10),
    (4, "advantage", 11, 1, 5, 18),
    (7, "elven_accuracy", 15, 1, 8, 24),
)

CANONICAL_VALIDATION_CELLS = (
    (1, "normal", 5, 0, 2, 10),
    (1, "advantage", 5, 1, 3, 12),
    (3, "normal", 9, 0, 4, 16),
    (4, "advantage", 11, 1, 5, 18),
    (6, "elven_accuracy", 13, 0, 7, 22),
    (7, "elven_accuracy", 15, 1, 8, 24),
)


@dataclass(frozen=True)
class SweepConfig:
    slots: tuple[int, ...]
    modes: tuple[str, ...]
    attack_bonuses: tuple[int, ...]
    bless_values: tuple[int, ...]
    target_counts: tuple[int, ...]
    acs: tuple[int, ...]
    label: str = "custom"


PRESETS = {
    "small": SweepConfig(
        slots=(1, 4),
        modes=("normal", "advantage", "elven_accuracy"),
        attack_bonuses=(9,),
        bless_values=(0, 1),
        target_counts=(2, 5),
        acs=(12, 18),
        label="small",
    ),
    "medium": SweepConfig(
        slots=(1, 4),
        modes=("normal", "advantage", "elven_accuracy"),
        attack_bonuses=(5, 11),
        bless_values=(0, 1),
        target_counts=(2, 5),
        acs=(12, 18),
        label="medium",
    ),
    "large": SweepConfig(
        slots=(1, 2, 3, 4, 5, 6, 7),
        modes=("normal", "advantage", "elven_accuracy"),
        attack_bonuses=(5, 7, 9, 11, 13, 15),
        bless_values=(0, 1),
        target_counts=(2, 3, 4, 5, 6, 7, 8),
        acs=tuple(range(10, 25)),
        label="large",
    ),
}

DEFAULT_CONFIG = PRESETS["small"]


def get_config(name: str) -> SweepConfig:
    try:
        return PRESETS[name]
    except KeyError as error:
        raise ValueError("unknown Chaos Bolt benchmark preset {!r}".format(name)) from error


def max_slot(config: SweepConfig) -> int:
    return max(config.slots)


def max_targets(config: SweepConfig) -> int:
    return max(config.target_counts)


def max_damage(config: SweepConfig) -> int:
    return max_targets(config) * (4 * 8 + 2 * max_slot(config) * 6)


def build_dice_prelude(config: SweepConfig = DEFAULT_CONFIG) -> str:
    chain_lines = ["chaos_chain_1(): chaos_strike(0)"]
    for target_count in range(2, max_targets(config) + 1):
        chain_lines.append(
            "chaos_chain_{count}(): chaos_strike(chaos_chain_{prev}())".format(
                count=target_count,
                prev=target_count - 1,
            )
        )
    split_arms = [
        'count == {count} -> chaos_chain_{count}()'.format(count=target_count)
        for target_count in config.target_counts[:-1]
    ]
    chain_dispatch = "chaos_chain(): split targets as count | {} | otherwise -> chaos_chain_{}()".format(
        " | ".join(split_arms),
        config.target_counts[-1],
    )
    return (
        dedent(
            """
            import "std:dnd/core.dice"

            chain_roll_normal(): d20
            chain_roll_advantage(): d+20
            chain_roll_elven_accuracy(): 3d20h1

            chain_roll(): split mode as name | name == "normal" -> chain_roll_normal() | name == "advantage" -> chain_roll_advantage() | otherwise -> chain_roll_elven_accuracy()
            chaos_hit_bonus(): split bless | == 1 -> d4 | otherwise -> 0
            chaos_crit_bonus(crit): split crit | == 1 -> 2 d 8 + (d6 ^ slot_level) | otherwise -> 0
            chaos_resolve_pair(die1, leap_damage, crit_bonus): split d8 as die2 | die1 == die2 -> die1 + die2 + (d6 ^ slot_level) + crit_bonus + leap_damage | otherwise -> die1 + die2 + (d6 ^ slot_level) + crit_bonus
            chaos_resolve_damage(leap_damage, crit): chaos_resolve_pair(d8, leap_damage, chaos_crit_bonus(crit))
            chaos_strike(leap_damage): split chain_roll() as attack_roll | attack_roll == 1 -> 0 | attack_roll == 20 -> chaos_resolve_damage(leap_damage, 1) | attack_roll + attack_bonus + chaos_hit_bonus() >= ac -> chaos_resolve_damage(leap_damage, 0) ||
            """
        ).strip()
        + "\n"
        + "\n".join(chain_lines)
        + "\n"
        + chain_dispatch
        + "\n"
    )


def build_dice_program(config: SweepConfig = DEFAULT_CONFIG) -> str:
    slot_values = ", ".join(str(value) for value in config.slots)
    mode_values = ", ".join('"{}"'.format(value) for value in config.modes)
    attack_values = ", ".join(str(value) for value in config.attack_bonuses)
    bless_values = ", ".join(str(value) for value in config.bless_values)
    target_values = ", ".join(str(value) for value in config.target_counts)
    return build_dice_prelude(config) + (
        dedent(
            """
            slot_level = [SLOT:{slot_values}]
            mode = [MODE:{mode_values}]
            attack_bonus = [ATTACK:{attack_values}]
            bless = [BLESS:{bless_values}]
            targets = [TARGETS:{target_values}]
            ac = [AC:{ac_values}]

            chaos_chain()
            """
        ).format(
            slot_values=slot_values,
            mode_values=mode_values,
            attack_values=attack_values,
            bless_values=bless_values,
            target_values=target_values,
            ac_values=", ".join(str(value) for value in config.acs),
        ).strip()
        + "\n"
    )


def coordinate_space(config: SweepConfig = DEFAULT_CONFIG):
    return product(
        config.slots,
        config.modes,
        config.attack_bonuses,
        config.bless_values,
        config.target_counts,
        config.acs,
    )


def state_space(config: SweepConfig = DEFAULT_CONFIG):
    return product(config.modes, config.attack_bonuses, config.bless_values, config.acs)


def _cells_in_config(config: SweepConfig, coordinates):
    available = set(coordinate_space(config))
    return tuple(coordinate for coordinate in coordinates if coordinate in available)


def representative_cells(config: SweepConfig = DEFAULT_CONFIG):
    cells = _cells_in_config(config, CANONICAL_REPRESENTATIVE_CELLS)
    if cells:
        return cells
    coordinates = tuple(coordinate_space(config))
    return (coordinates[0], coordinates[len(coordinates) // 2], coordinates[-1])


def validation_cells(config: SweepConfig = DEFAULT_CONFIG):
    cells = _cells_in_config(config, CANONICAL_VALIDATION_CELLS)
    if cells:
        return cells
    coordinates = tuple(coordinate_space(config))
    if len(coordinates) <= 6:
        return coordinates
    indices = (0, len(coordinates) // 5, 2 * len(coordinates) // 5, 3 * len(coordinates) // 5, 4 * len(coordinates) // 5, len(coordinates) - 1)
    return tuple(dict.fromkeys(coordinates[index] for index in indices))


def format_coordinate(coordinate: tuple[object, ...]) -> str:
    return "slot={} mode={} atk={} bless={} targets={} ac={}".format(*coordinate)
