"""Shared workload definition for the Chaos Bolt chain benchmark."""

from __future__ import annotations

from itertools import product
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]

SLOTS = (1, 2, 3, 4, 5)
MODES = ("normal", "advantage", "elven_accuracy")
ATTACK_BONUSES = (5, 7, 9, 11, 13)
BLESS_VALUES = (0, 1)
ACS = tuple(range(12, 23))
TARGET_COUNTS = (2, 3, 4, 5, 6)
AXIS_ORDER = ("SLOT", "MODE", "ATTACK", "BLESS", "TARGETS", "AC")
MAX_SLOT = max(SLOTS)
MAX_TARGETS = max(TARGET_COUNTS)
MAX_DAMAGE = MAX_TARGETS * (4 * 8 + 2 * MAX_SLOT * 6)

REPRESENTATIVE_CELLS = (
    (1, "normal", 5, 0, 2, 12),
    (3, "advantage", 9, 1, 4, 17),
    (5, "elven_accuracy", 13, 1, 6, 22),
)

VALIDATION_CELLS = (
    (1, "normal", 5, 0, 2, 12),
    (1, "advantage", 5, 1, 3, 14),
    (2, "normal", 7, 0, 4, 16),
    (3, "advantage", 9, 1, 4, 17),
    (4, "elven_accuracy", 11, 0, 5, 20),
    (5, "elven_accuracy", 13, 1, 6, 22),
)


def build_dice_prelude() -> str:
    chain_lines = ["chaos_chain_1(): chaos_strike(0)"]
    for target_count in range(2, MAX_TARGETS + 1):
        chain_lines.append(
            "chaos_chain_{count}(): chaos_strike(chaos_chain_{prev}())".format(
                count=target_count,
                prev=target_count - 1,
            )
        )
    split_arms = [
        'count == {count} -> chaos_chain_{count}()'.format(count=target_count)
        for target_count in TARGET_COUNTS[:-1]
    ]
    chain_dispatch = "chaos_chain(): split targets as count | {} | otherwise -> chaos_chain_{}()".format(
        " | ".join(split_arms),
        TARGET_COUNTS[-1],
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


def build_dice_program() -> str:
    slot_values = ", ".join(str(value) for value in SLOTS)
    mode_values = ", ".join('"{}"'.format(value) for value in MODES)
    attack_values = ", ".join(str(value) for value in ATTACK_BONUSES)
    bless_values = ", ".join(str(value) for value in BLESS_VALUES)
    target_values = ", ".join(str(value) for value in TARGET_COUNTS)
    return build_dice_prelude() + (
        dedent(
            """
            slot_level = [SLOT:{slot_values}]
            mode = [MODE:{mode_values}]
            attack_bonus = [ATTACK:{attack_values}]
            bless = [BLESS:{bless_values}]
            targets = [TARGETS:{target_values}]
            ac = [AC:{ac_min}..{ac_max}]

            chaos_chain()
            """
        ).format(
            slot_values=slot_values,
            mode_values=mode_values,
            attack_values=attack_values,
            bless_values=bless_values,
            target_values=target_values,
            ac_min=min(ACS),
            ac_max=max(ACS),
        ).strip()
        + "\n"
    )


def coordinate_space():
    return product(SLOTS, MODES, ATTACK_BONUSES, BLESS_VALUES, TARGET_COUNTS, ACS)


def state_space():
    return product(MODES, ATTACK_BONUSES, BLESS_VALUES, ACS)


def format_coordinate(coordinate: tuple[object, ...]) -> str:
    return "slot={} mode={} atk={} bless={} targets={} ac={}".format(*coordinate)
