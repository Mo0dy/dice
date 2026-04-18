"""Vectorized NumPy Monte Carlo backend that still rolls primitive dice directly."""

from __future__ import annotations

import numpy as np

from .workload import MAX_DAMAGE, MAX_RAYS, SLOTS, state_space


def _simulate_state_histograms(
    *,
    mode: str,
    attack_bonus: int,
    bless: int,
    ac: int,
    samples_per_cell: int,
    seed: int,
    batch_size: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    histograms = np.zeros((len(SLOTS), MAX_DAMAGE + 1), dtype=np.int64)
    remaining = samples_per_cell

    while remaining > 0:
        batch = min(batch_size, remaining)
        remaining -= batch

        if mode == "normal":
            attack_rolls = rng.integers(1, 21, size=(batch, MAX_RAYS), dtype=np.int16)
        elif mode == "advantage":
            attack_rolls = rng.integers(1, 21, size=(batch, MAX_RAYS, 2), dtype=np.int16).max(axis=2)
        elif mode == "elven_accuracy":
            attack_rolls = rng.integers(1, 21, size=(batch, MAX_RAYS, 3), dtype=np.int16).max(axis=2)
        else:
            raise ValueError("unknown mode {!r}".format(mode))

        if bless:
            bless_rolls = rng.integers(1, 5, size=(batch, MAX_RAYS), dtype=np.int16)
        else:
            bless_rolls = 0

        d6_rolls = rng.integers(1, 7, size=(batch, MAX_RAYS, 6), dtype=np.int16)
        hit_damage = d6_rolls[:, :, :3].sum(axis=2, dtype=np.int16) + 4
        crit_damage = d6_rolls.sum(axis=2, dtype=np.int16) + 4

        miss_mask = attack_rolls == 1
        crit_mask = attack_rolls == 20
        hit_mask = (~miss_mask) & (~crit_mask) & (attack_rolls + attack_bonus + bless_rolls >= ac)

        ray_damage = np.zeros((batch, MAX_RAYS), dtype=np.int16)
        ray_damage[hit_mask] = hit_damage[hit_mask]
        ray_damage[crit_mask] = crit_damage[crit_mask]

        slot_totals = np.cumsum(ray_damage, axis=1, dtype=np.int16)
        for slot_index, slot_level in enumerate(SLOTS):
            totals = slot_totals[:, slot_level]
            histograms[slot_index] += np.bincount(totals, minlength=MAX_DAMAGE + 1)

    return histograms


def sample_coordinate_distribution(coordinate, trials: int, seed: int, batch_size: int = 50000) -> dict[int, float]:
    slot_level, mode, attack_bonus, bless, ac = coordinate
    histograms = _simulate_state_histograms(
        mode=mode,
        attack_bonus=attack_bonus,
        bless=bless,
        ac=ac,
        samples_per_cell=trials,
        seed=seed,
        batch_size=batch_size,
    )
    row = histograms[SLOTS.index(slot_level)]
    nonzero = np.flatnonzero(row)
    return {int(outcome): int(row[outcome]) / trials for outcome in nonzero}


def evaluate_sweep(samples_per_cell: int, seed: int, batch_size: int = 50000) -> dict[tuple[object, ...], dict[int, float]]:
    sampled = {}
    for state_index, (mode, attack_bonus, bless, ac) in enumerate(state_space()):
        histograms = _simulate_state_histograms(
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
            samples_per_cell=samples_per_cell,
            seed=seed + state_index,
            batch_size=batch_size,
        )
        for slot_index, slot_level in enumerate(SLOTS):
            row = histograms[slot_index]
            nonzero = np.flatnonzero(row)
            sampled[(slot_level, mode, attack_bonus, bless, ac)] = {
                int(outcome): int(row[outcome]) / samples_per_cell for outcome in nonzero
            }
    return sampled
