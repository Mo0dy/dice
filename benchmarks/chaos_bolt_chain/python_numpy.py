"""Vectorized NumPy Monte Carlo backend for Chaos Bolt chains."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

import numpy as np

from .workload import DEFAULT_CONFIG, max_damage, max_slot, max_targets, state_space


def _simulate_state_histograms(
    *,
    slots: tuple[int, ...],
    target_counts: tuple[int, ...],
    max_slot_level: int,
    max_targets_count: int,
    max_total_damage: int,
    mode: str,
    attack_bonus: int,
    bless: int,
    ac: int,
    samples_per_cell: int,
    seed: int,
    batch_size: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    histograms = np.zeros((len(slots), len(target_counts), max_total_damage + 1), dtype=np.int64)
    remaining = samples_per_cell

    while remaining > 0:
        batch = min(batch_size, remaining)
        remaining -= batch

        if mode == "normal":
            attack_rolls = rng.integers(1, 21, size=(batch, max_targets_count), dtype=np.int16)
        elif mode == "advantage":
            attack_rolls = rng.integers(1, 21, size=(batch, max_targets_count, 2), dtype=np.int16).max(axis=2)
        elif mode == "elven_accuracy":
            attack_rolls = rng.integers(1, 21, size=(batch, max_targets_count, 3), dtype=np.int16).max(axis=2)
        else:
            raise ValueError("unknown mode {!r}".format(mode))

        if bless:
            bless_rolls = rng.integers(1, 5, size=(batch, max_targets_count), dtype=np.int16)
        else:
            bless_rolls = 0

        pair_d8 = rng.integers(1, 9, size=(batch, max_targets_count, 2), dtype=np.int16)
        pair_sums = pair_d8.sum(axis=2, dtype=np.int16)
        doubles = pair_d8[:, :, 0] == pair_d8[:, :, 1]

        base_d6 = rng.integers(1, 7, size=(batch, max_targets_count, max_slot_level), dtype=np.int16)
        crit_d8 = rng.integers(1, 9, size=(batch, max_targets_count, 2), dtype=np.int16)
        crit_d6 = rng.integers(1, 7, size=(batch, max_targets_count, max_slot_level), dtype=np.int16)

        base_d6_prefix = np.cumsum(base_d6, axis=2, dtype=np.int16)
        crit_d6_prefix = np.cumsum(crit_d6, axis=2, dtype=np.int16)
        crit_pair_sum = crit_d8.sum(axis=2, dtype=np.int16)

        misses = attack_rolls == 1
        crits = attack_rolls == 20
        hits = (~misses) & (crits | (attack_rolls + attack_bonus + bless_rolls >= ac))

        active = np.zeros((batch, max_targets_count), dtype=bool)
        active[:, 0] = True
        for target_index in range(1, max_targets_count):
            active[:, target_index] = active[:, target_index - 1] & hits[:, target_index - 1] & doubles[:, target_index - 1]

        for slot_index, slot_level in enumerate(slots):
            base_damage = pair_sums + base_d6_prefix[:, :, slot_level - 1]
            crit_damage = base_damage + crit_pair_sum + crit_d6_prefix[:, :, slot_level - 1]
            strike_damage = np.where(hits, np.where(crits, crit_damage, base_damage), 0)
            chain_damage = np.where(active, strike_damage, 0)
            chain_totals = np.cumsum(chain_damage, axis=1, dtype=np.int16)
            for target_count_index, target_count in enumerate(target_counts):
                totals = chain_totals[:, target_count - 1]
                histograms[slot_index, target_count_index] += np.bincount(totals, minlength=max_total_damage + 1)

    return histograms


def _split_trials_evenly(total_trials: int, parts: int) -> tuple[int, ...]:
    base, remainder = divmod(total_trials, parts)
    return tuple(base + (1 if index < remainder else 0) for index in range(parts))


def _simulate_state_histograms_task(args) -> tuple[int, np.ndarray]:
    state_index, slots, target_counts, max_slot_level, max_targets_count, max_total_damage, mode, attack_bonus, bless, ac, samples_per_cell, seed, batch_size = args
    return (
        state_index,
        _simulate_state_histograms(
            slots=slots,
            target_counts=target_counts,
            max_slot_level=max_slot_level,
            max_targets_count=max_targets_count,
            max_total_damage=max_total_damage,
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
    slots: tuple[int, ...],
    target_counts: tuple[int, ...],
    max_slot_level: int,
    max_targets_count: int,
    max_total_damage: int,
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
            slots=slots,
            target_counts=target_counts,
            max_slot_level=max_slot_level,
            max_targets_count=max_targets_count,
            max_total_damage=max_total_damage,
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
            slots=slots,
            target_counts=target_counts,
            max_slot_level=max_slot_level,
            max_targets_count=max_targets_count,
            max_total_damage=max_total_damage,
            mode=mode,
            attack_bonus=attack_bonus,
            bless=bless,
            ac=ac,
            samples_per_cell=chunks[0],
            seed=seed,
            batch_size=batch_size,
        )

    aggregate = np.zeros((len(slots), len(target_counts), max_total_damage + 1), dtype=np.int64)
    with ProcessPoolExecutor(max_workers=len(chunks), mp_context=mp.get_context("fork")) as executor:
        futures = [
            executor.submit(
                _simulate_state_histograms_task,
                (
                    0,
                    slots,
                    target_counts,
                    max_slot_level,
                    max_targets_count,
                    max_total_damage,
                    mode,
                    attack_bonus,
                    bless,
                    ac,
                    chunk,
                    seed + chunk_index,
                    batch_size,
                ),
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
    config=DEFAULT_CONFIG,
    batch_size: int = 50000,
    processes: int = 1,
) -> dict[int, float]:
    slot_level, mode, attack_bonus, bless, targets, ac = coordinate
    slots = tuple(config.slots)
    target_counts = tuple(config.target_counts)
    histograms = _state_histograms_for_single_state(
        slots=slots,
        target_counts=target_counts,
        max_slot_level=max_slot(config),
        max_targets_count=max_targets(config),
        max_total_damage=max_damage(config),
        mode=mode,
        attack_bonus=attack_bonus,
        bless=bless,
        ac=ac,
        samples_per_cell=trials,
        seed=seed,
        batch_size=batch_size,
        processes=processes,
    )
    row = histograms[slots.index(slot_level), target_counts.index(targets)]
    nonzero = np.flatnonzero(row)
    return {int(outcome): int(row[outcome]) / trials for outcome in nonzero}


def evaluate_sweep(
    samples_per_cell: int,
    seed: int,
    config=DEFAULT_CONFIG,
    batch_size: int = 50000,
    processes: int = 1,
) -> dict[tuple[object, ...], dict[int, float]]:
    sampled = {}
    slots = tuple(config.slots)
    target_counts = tuple(config.target_counts)
    max_slot_level = max_slot(config)
    max_targets_count = max_targets(config)
    max_total_damage = max_damage(config)
    states = tuple(state_space(config))

    if processes <= 1:
        for state_index, (mode, attack_bonus, bless, ac) in enumerate(states):
            histograms = _simulate_state_histograms(
                slots=slots,
                target_counts=target_counts,
                max_slot_level=max_slot_level,
                max_targets_count=max_targets_count,
                max_total_damage=max_total_damage,
                mode=mode,
                attack_bonus=attack_bonus,
                bless=bless,
                ac=ac,
                samples_per_cell=samples_per_cell,
                seed=seed + state_index,
                batch_size=batch_size,
            )
            for slot_index, slot_level in enumerate(slots):
                for target_count_index, target_count in enumerate(target_counts):
                    row = histograms[slot_index, target_count_index]
                    nonzero = np.flatnonzero(row)
                    sampled[(slot_level, mode, attack_bonus, bless, target_count, ac)] = {
                        int(outcome): int(row[outcome]) / samples_per_cell for outcome in nonzero
                    }
        return sampled

    chunks = [chunk for chunk in _split_trials_evenly(samples_per_cell, processes) if chunk > 0]
    aggregate_by_state = {
        state_index: np.zeros((len(slots), len(target_counts), max_total_damage + 1), dtype=np.int64)
        for state_index in range(len(states))
    }

    tasks = []
    for state_index, (mode, attack_bonus, bless, ac) in enumerate(states):
        for chunk_index, chunk in enumerate(chunks):
            tasks.append(
                (
                    state_index,
                    slots,
                    target_counts,
                    max_slot_level,
                    max_targets_count,
                    max_total_damage,
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
        for slot_index, slot_level in enumerate(slots):
            for target_count_index, target_count in enumerate(target_counts):
                row = histograms[slot_index, target_count_index]
                nonzero = np.flatnonzero(row)
                sampled[(slot_level, mode, attack_bonus, bless, target_count, ac)] = {
                    int(outcome): int(row[outcome]) / samples_per_cell for outcome in nonzero
                }
    return sampled
