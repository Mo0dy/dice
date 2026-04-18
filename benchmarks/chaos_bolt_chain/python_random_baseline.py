"""Literal Python random-module Monte Carlo baseline for Chaos Bolt chains."""

from __future__ import annotations

from collections import Counter
import random

from .workload import coordinate_space


def roll_die(rng: random.Random, sides: int) -> int:
    return rng.randint(1, sides)


def attack_roll(rng: random.Random, mode: str) -> int:
    if mode == "normal":
        return roll_die(rng, 20)
    if mode == "advantage":
        return max(roll_die(rng, 20), roll_die(rng, 20))
    if mode == "elven_accuracy":
        return max(roll_die(rng, 20), roll_die(rng, 20), roll_die(rng, 20))
    raise ValueError("unknown mode {!r}".format(mode))


def chaos_strike(
    rng: random.Random,
    *,
    ac: int,
    attack_bonus: int,
    slot_level: int,
    mode: str,
    bless: int,
) -> tuple[int, bool]:
    roll = attack_roll(rng, mode)
    hit_bonus = roll_die(rng, 4) if bless else 0
    if roll == 1:
        return 0, False

    hit = roll == 20 or (roll + attack_bonus + hit_bonus >= ac)
    if not hit:
        return 0, False

    die1 = roll_die(rng, 8)
    die2 = roll_die(rng, 8)
    damage = die1 + die2 + sum(roll_die(rng, 6) for _ in range(slot_level))
    if roll == 20:
        damage += roll_die(rng, 8) + roll_die(rng, 8)
        damage += sum(roll_die(rng, 6) for _ in range(slot_level))
    return damage, die1 == die2


def chaos_bolt_trial(
    rng: random.Random,
    *,
    slot_level: int,
    mode: str,
    attack_bonus: int,
    bless: int,
    targets: int,
    ac: int,
) -> int:
    total = 0
    for target_index in range(targets):
        damage, doubles = chaos_strike(
            rng,
            ac=ac,
            attack_bonus=attack_bonus,
            slot_level=slot_level,
            mode=mode,
            bless=bless,
        )
        total += damage
        if damage == 0 or not doubles or target_index == targets - 1:
            break
    return total


def sample_coordinate_distribution(coordinate, trials: int, seed: int) -> dict[int, float]:
    slot_level, mode, attack_bonus, bless, targets, ac = coordinate
    rng = random.Random(seed)
    counts: Counter[int] = Counter()
    for _ in range(trials):
        outcome = chaos_bolt_trial(
            rng,
            slot_level=slot_level,
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            targets=targets,
            ac=ac,
        )
        counts[outcome] += 1
    return {outcome: count / trials for outcome, count in counts.items()}


def evaluate_sweep(samples_per_cell: int, seed: int, **_unused) -> dict[tuple[object, ...], dict[int, float]]:
    rng = random.Random(seed)
    sampled = {}
    for slot_level, mode, attack_bonus, bless, targets, ac in coordinate_space():
        counts: Counter[int] = Counter()
        for _ in range(samples_per_cell):
            outcome = chaos_bolt_trial(
                rng,
                slot_level=slot_level,
                mode=mode,
                attack_bonus=attack_bonus,
                bless=bless,
                targets=targets,
                ac=ac,
            )
            counts[outcome] += 1
        sampled[(slot_level, mode, attack_bonus, bless, targets, ac)] = {
            outcome: count / samples_per_cell for outcome, count in counts.items()
        }
    return sampled
