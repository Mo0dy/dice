"""Vectorized NumPy Monte Carlo backend that still rolls primitive dice directly."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
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


def _split_trials_evenly(total_trials: int, parts: int) -> tuple[int, ...]:
    base, remainder = divmod(total_trials, parts)
    return tuple(base + (1 if index < remainder else 0) for index in range(parts))


def _simulate_state_histograms_task(args) -> tuple[int, np.ndarray]:
    state_index, mode, attack_bonus, bless, ac, samples_per_cell, seed, batch_size = args
    return (
        state_index,
        _simulate_state_histograms(
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
            samples_per_cell=samples_per_cell,
            seed=seed,
            batch_size=batch_size,
        ),
    )


def _state_histograms_for_single_state(
    *,
    mode: str,
    attack_bonus: int,
    bless: int,
    ac: int,
    samples_per_cell: int,
    seed: int,
    batch_size: int,
    processes: int,
) -> np.ndarray:
    if processes <= 1:
        return _simulate_state_histograms(
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
            samples_per_cell=samples_per_cell,
            seed=seed,
            batch_size=batch_size,
        )

    chunks = [chunk for chunk in _split_trials_evenly(samples_per_cell, processes) if chunk > 0]
    if len(chunks) == 1:
        return _simulate_state_histograms(
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
            samples_per_cell=chunks[0],
            seed=seed,
            batch_size=batch_size,
        )

    aggregate = np.zeros((len(SLOTS), MAX_DAMAGE + 1), dtype=np.int64)
    with ProcessPoolExecutor(max_workers=len(chunks), mp_context=mp.get_context("fork")) as executor:
        futures = [
            executor.submit(
                _simulate_state_histograms_task,
                (0, mode, attack_bonus, bless, ac, chunk, seed + chunk_index, batch_size),
            )
            for chunk_index, chunk in enumerate(chunks)
        ]
        for future in as_completed(futures):
            _unused_state_index, histograms = future.result()
            aggregate += histograms
    return aggregate


def sample_coordinate_distribution(
    coordinate,
    trials: int,
    seed: int,
    batch_size: int = 50000,
    processes: int = 1,
) -> dict[int, float]:
    slot_level, mode, attack_bonus, bless, ac = coordinate
    histograms = _state_histograms_for_single_state(
        mode=mode,
        attack_bonus=attack_bonus,
        bless=bless,
        ac=ac,
        samples_per_cell=trials,
        seed=seed,
        batch_size=batch_size,
        processes=processes,
    )
    row = histograms[SLOTS.index(slot_level)]
    nonzero = np.flatnonzero(row)
    return {int(outcome): int(row[outcome]) / trials for outcome in nonzero}


def evaluate_sweep(
    samples_per_cell: int,
    seed: int,
    batch_size: int = 50000,
    processes: int = 1,
) -> dict[tuple[object, ...], dict[int, float]]:
    sampled = {}
    states = tuple(state_space())

    if processes <= 1:
        for state_index, (mode, attack_bonus, bless, ac) in enumerate(states):
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

    chunks = [chunk for chunk in _split_trials_evenly(samples_per_cell, processes) if chunk > 0]
    aggregate_by_state = {
        state_index: np.zeros((len(SLOTS), MAX_DAMAGE + 1), dtype=np.int64)
        for state_index in range(len(states))
    }

    tasks = []
    for state_index, (mode, attack_bonus, bless, ac) in enumerate(states):
        for chunk_index, chunk in enumerate(chunks):
            tasks.append(
                (
                    state_index,
                    mode,
                    attack_bonus,
                    bless,
                    ac,
                    chunk,
                    seed + state_index * max(len(chunks), 1) + chunk_index,
                    batch_size,
                )
            )

    with ProcessPoolExecutor(max_workers=len(chunks), mp_context=mp.get_context("fork")) as executor:
        futures = [executor.submit(_simulate_state_histograms_task, task) for task in tasks]
        for future in as_completed(futures):
            state_index, histograms = future.result()
            aggregate_by_state[state_index] += histograms

    for state_index, (mode, attack_bonus, bless, ac) in enumerate(states):
        histograms = aggregate_by_state[state_index]
        for slot_index, slot_level in enumerate(SLOTS):
            row = histograms[slot_index]
            nonzero = np.flatnonzero(row)
            sampled[(slot_level, mode, attack_bonus, bless, ac)] = {
                int(outcome): int(row[outcome]) / samples_per_cell for outcome in nonzero
            }
    return sampled
