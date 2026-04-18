"""Shared workload definition for the Hexed Scorching Ray benchmark."""

from __future__ import annotations

from itertools import product
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]

SLOTS = tuple(range(2, 9))
MODES = ("normal", "advantage", "elven_accuracy")
ATTACK_BONUSES = (7, 9, 11)
BLESS_VALUES = (0, 1)
ACS = tuple(range(13, 23))
AXIS_ORDER = ("SLOT", "MODE", "ATTACK", "BLESS", "AC")
CURSE_BONUS = 4
MAX_RAYS = max(slot_level + 1 for slot_level in SLOTS)
MAX_DAMAGE = MAX_RAYS * (6 * 6 + CURSE_BONUS)

REPRESENTATIVE_CELLS = (
    (2, "normal", 7, 0, 13),
    (5, "advantage", 9, 1, 17),
    (8, "elven_accuracy", 11, 1, 22),
)

VALIDATION_CELLS = (
    (2, "normal", 7, 0, 13),
    (2, "advantage", 7, 1, 13),
    (4, "normal", 9, 0, 18),
    (5, "elven_accuracy", 9, 1, 17),
    (7, "advantage", 11, 0, 21),
    (8, "elven_accuracy", 11, 1, 22),
)


def build_dice_program() -> str:
    return (
        dedent(
            """
            import "std:dnd/core.dice"

            ray_roll_normal(): d20
            ray_roll_advantage(): d+20
            ray_roll_elven_accuracy(): 3d20h1

            ray_roll(mode):
                split mode as name
                | name == "normal" -> ray_roll_normal()
                | name == "advantage" -> ray_roll_advantage()
                | otherwise -> ray_roll_elven_accuracy()

            hexed_scorching_ray(ac, attack_bonus, slot_level=2, mode="normal", bless=0):
                roll = ray_roll(mode)
                hit_bonus = bless == 1 -> d4 | 0
                ray = attack(ac, attack_bonus, 2 d 6 + 1 d 6, 4, roll=roll, hit_bonus=hit_bonus)
                ray ^ (slot_level + 1)

            hexed_scorching_ray([AC:13..22], [ATTACK:7, 9, 11], slot_level=[SLOT:2..8], mode=[MODE:"normal", "advantage", "elven_accuracy"], bless=[BLESS:0, 1])
            """
        ).strip()
        + "\n"
    )


def coordinate_space():
    return product(SLOTS, MODES, ATTACK_BONUSES, BLESS_VALUES, ACS)


def state_space():
    return product(MODES, ATTACK_BONUSES, BLESS_VALUES, ACS)


def format_coordinate(coordinate: tuple[object, ...]) -> str:
    return "slot={} mode={} atk={} bless={} ac={}".format(*coordinate)
