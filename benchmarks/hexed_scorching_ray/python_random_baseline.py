"""Literal Python random-module Monte Carlo baseline."""

from __future__ import annotations

from collections import Counter
import random

from .workload import coordinate_space


def roll_die(rng: random.Random, sides: int) -> int:
    return rng.randint(1, sides)


def roll_sum(rng: random.Random, count: int, sides: int) -> int:
    return sum(roll_die(rng, sides) for _ in range(count))


def attack_roll(rng: random.Random, mode: str) -> int:
    if mode == "normal":
        return roll_die(rng, 20)
    if mode == "advantage":
        return max(roll_die(rng, 20), roll_die(rng, 20))
    if mode == "elven_accuracy":
        return max(roll_die(rng, 20), roll_die(rng, 20), roll_die(rng, 20))
    raise ValueError("unknown mode {!r}".format(mode))


def hexed_ray_damage(
    rng: random.Random,
    *,
    ac: int,
    attack_bonus: int,
    mode: str,
    bless: int,
    curse_bonus: int = 4,
) -> int:
    roll = attack_roll(rng, mode)
    hit_bonus = roll_die(rng, 4) if bless else 0
    if roll == 1:
        return 0
    if roll == 20:
        return roll_sum(rng, 6, 6) + curse_bonus
    if roll + attack_bonus + hit_bonus >= ac:
        return roll_sum(rng, 3, 6) + curse_bonus
    return 0


def hexed_scorching_ray_trial(
    rng: random.Random,
    *,
    slot_level: int,
    mode: str,
    attack_bonus: int,
    bless: int,
    ac: int,
) -> int:
    total = 0
    for _ in range(slot_level + 1):
        total += hexed_ray_damage(
            rng,
            ac=ac,
            attack_bonus=attack_bonus,
            mode=mode,
            bless=bless,
        )
    return total


def sample_coordinate_distribution(coordinate, trials: int, seed: int) -> dict[int, float]:
    slot_level, mode, attack_bonus, bless, ac = coordinate
    rng = random.Random(seed)
    counts: Counter[int] = Counter()
    for _ in range(trials):
        outcome = hexed_scorching_ray_trial(
            rng,
            slot_level=slot_level,
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
        )
        counts[outcome] += 1
    return {outcome: count / trials for outcome, count in counts.items()}


def evaluate_sweep(samples_per_cell: int, seed: int, **_unused) -> dict[tuple[object, ...], dict[int, float]]:
    rng = random.Random(seed)
    sampled = {}
    for slot_level, mode, attack_bonus, bless, ac in coordinate_space():
        counts: Counter[int] = Counter()
        for _ in range(samples_per_cell):
            outcome = hexed_scorching_ray_trial(
                rng,
                slot_level=slot_level,
                mode=mode,
                attack_bonus=attack_bonus,
                bless=bless,
                ac=ac,
            )
            counts[outcome] += 1
        sampled[(slot_level, mode, attack_bonus, bless, ac)] = {
            outcome: count / samples_per_cell for outcome, count in counts.items()
        }
    return sampled
