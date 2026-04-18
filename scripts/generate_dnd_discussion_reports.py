#!/usr/bin/env python3

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "dnd" / "discussions"
REPORT_ROOT = ROOT / "reports" / "dnd_discussions"
DATA_DIR = REPORT_ROOT / "data"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file, _serialize_result


def _scalar_value(distrib) -> float:
    items = list(distrib.items())
    if len(items) != 1:
        raise ValueError("expected deterministic distribution")
    return float(items[0][0])


def _clamp_probability(value: float) -> float:
    if abs(value) < 1e-12:
        return 0.0
    if abs(value - 1.0) < 1e-12:
        return 1.0
    return value


def _one_axis(result) -> dict[object, float]:
    return {coords[0]: _scalar_value(distrib) for coords, distrib in result.cells.items()}


def _two_axis(result) -> dict[object, dict[object, float]]:
    values: dict[object, dict[object, float]] = {}
    for coords, distrib in result.cells.items():
        first, second = coords
        values.setdefault(first, {})[second] = _scalar_value(distrib)
    return values


def _render_percent(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _render_number(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


@dataclass(frozen=True)
class CaseSummary:
    name: str
    sample: str
    source_url: str
    online_claim: str
    comparison: str
    notes: list[str]
    extracted: dict[str, object]


def _load_result(relative_path: str):
    path = ROOT / relative_path
    return interpret_file(path.read_text(encoding="utf-8"), current_dir=path.parent)


def _write_raw_data(relative_path: str, result) -> None:
    output_path = DATA_DIR / Path(relative_path).with_suffix(".json").name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_result(result, probability_mode="raw")
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize_advantage(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = {key: _clamp_probability(value) for key, value in _one_axis(result).items()}
    return CaseSummary(
        name="Advantage Rules Of Thumb",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/labqox/some_helpful_probability_rules_of_thumb_for/",
        online_claim="Advantage should put nat 20 at about 9.75%, nat 1 at about 0.25%, 15+ at about 51%, and 7+ at about 91%.",
        comparison="Exact match to the thread's headline numbers after ordinary rounding.",
        notes=[
            f"Plain nat 20: {_render_percent(values['nat20_plain'])}",
            f"Advantage nat 20: {_render_percent(values['nat20_adv'])}",
            f"Advantage nat 1: {_render_percent(values['nat1_adv'])}",
            f"Advantage 15+: {_render_percent(values['at_least_15_adv'])}",
            f"Advantage 7+: {_render_percent(values['at_least_7_adv'])}",
            f"Disadvantage nat 1: {_render_percent(values['nat1_disadv'])}",
        ],
        extracted=values,
    )


def summarize_elven_accuracy(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = {key: _clamp_probability(value) for key, value in _one_axis(result).items()}
    return CaseSummary(
        name="Elven Accuracy Crit-Fishing",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/mm3zb0/elven_accuracy_is_it_really_that_good/",
        online_claim="Crit rate should move from 5.00% to 9.75% with advantage and 14.26% with Elven Accuracy.",
        comparison="Exact match on the crit-rate claims; hit-rate gains versus AC 15 are also easy to inspect in the sample output.",
        notes=[
            f"Plain crit: {_render_percent(values['crit_plain'], 3)}",
            f"Advantage crit: {_render_percent(values['crit_adv'], 3)}",
            f"Elven Accuracy crit: {_render_percent(values['crit_elven'], 4)}",
            f"Hit chance vs AC 15 at +8: plain {_render_percent(values['hit_plain_ac15'])}, advantage {_render_percent(values['hit_adv_ac15'])}, Elven Accuracy {_render_percent(values['hit_elven_ac15'])}",
        ],
        extracted=values,
    )


def summarize_gwf(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _one_axis(result)
    return CaseSummary(
        name="Great Weapon Fighting Average Damage",
        sample=relative_path,
        source_url="https://rpg.stackexchange.com/questions/47172/how-much-damage-does-great-weapon-fighting-add-on-average",
        online_claim="Great Weapon Fighting should add about +1.33 damage to 2d6 weapons and about +0.83 damage to 1d12 weapons.",
        comparison="Exact match after rounding.",
        notes=[
            f"2d6 mean: {_render_number(values['mean_2d6'])} -> {_render_number(values['mean_2d6_gwf'])} (delta {_render_number(values['delta_2d6'])})",
            f"1d12 mean: {_render_number(values['mean_1d12'])} -> {_render_number(values['mean_1d12_gwf'])} (delta {_render_number(values['delta_1d12'])})",
        ],
        extracted=values,
    )


def summarize_gwm_vs_asi(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    no_adv_wins = []
    adv_wins = []
    for ac, asi_damage in values["asi"].items():
        gwm_best = max(values["gwm_plain"][ac], values["gwm_power"][ac])
        if gwm_best > asi_damage:
            no_adv_wins.append(ac)
    for ac, asi_damage in values["asi_adv"].items():
        gwm_best = max(values["gwm_plain_adv"][ac], values["gwm_power_adv"][ac])
        if gwm_best > asi_damage:
            adv_wins.append(ac)
    comparison = (
        "Matches the thread qualitatively: under these level-4 assumptions the feat build needs to lean on the power-attack mode, "
        "and advantage dramatically expands the AC range where it beats the ASI build."
    )
    return CaseSummary(
        name="Great Weapon Master Versus ASI",
        sample=relative_path,
        source_url="https://rpg.stackexchange.com/questions/202251/does-great-weapon-master-deal-more-expected-damage-than-an-asi",
        online_claim="Without reliable advantage, an early ASI is often the safer damage pick; with advantage, Great Weapon Master becomes much more attractive.",
        comparison=comparison,
        notes=[
            f"GWM build beats ASI without advantage at AC values {no_adv_wins}.",
            f"GWM build beats ASI with advantage at AC values {adv_wins}.",
            "The sample exposes both the plain swing and the power-attack swing so the report layer can choose the better mode per AC.",
        ],
        extracted={"no_adv_wins": no_adv_wins, "adv_wins": adv_wins},
    )


def summarize_pam_vs_asi(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    no_adv_wins = [ac for ac in values["asi"] if values["pam"][ac] > values["asi"][ac]]
    adv_wins = [ac for ac in values["asi_adv"] if values["pam_adv"][ac] > values["asi_adv"][ac]]
    return CaseSummary(
        name="Polearm Master Versus ASI",
        sample=relative_path,
        source_url="https://rpg.stackexchange.com/questions/202307/when-does-polearm-master-deal-more-damage-than-an-asi",
        online_claim="The extra butt-end attack can outperform an early +2 Strength, depending on assumptions about weapon, attack count, and accuracy.",
        comparison="Under this one-attack level-4 halberd model, Polearm Master wins across the whole tested AC range with and without advantage.",
        notes=[
            f"Polearm Master beats the ASI build without advantage at AC values {no_adv_wins}.",
            f"Polearm Master beats the ASI build with advantage at AC values {adv_wins}.",
            "This is strongly assumption-sensitive because the sample intentionally models the narrow early-level one-attack case that favors extra bonus-action attacks.",
        ],
        extracted={"no_adv_wins": no_adv_wins, "adv_wins": adv_wins},
    )


def summarize_bless(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    gap_closed = values["gap_closed"]
    ac16_gap = gap_closed[16]
    ac20_gap = gap_closed[20]
    return CaseSummary(
        name="Bless As Party DPR",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/1of3fyk/how_to_calculate_how_much_extra_damage_the_bless/",
        online_claim="Bless moves party DPR about 12.5% closer to its theoretical maximum, and its relative value rises when accuracy is bad.",
        comparison=(
            "The second part matches clearly: Bless matters much more as AC climbs. "
            "The exact '12.5% closer to max' phrasing does not hold under this party model because the benefit is concentrated near the low-probability tail of missed attacks."
        ),
        notes=[
            f"Gap closed at AC 16: {_render_percent(ac16_gap)}",
            f"Gap closed at AC 20: {_render_percent(ac20_gap)}",
            f"Gap closed ranges from {_render_percent(min(gap_closed.values()))} to {_render_percent(max(gap_closed.values()))} across AC 10..22.",
        ],
        extracted={"gap_closed": gap_closed, "plain": values["plain"], "blessed": values["blessed"]},
    )


def summarize_hunters_mark(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    gap = {rounds: values["hunters_mark"][rounds] - values["plain"][rounds] for rounds in values["plain"]}
    break_even = next((rounds for rounds, diff in sorted(gap.items()) if diff > 1e-9), None)
    return CaseSummary(
        name="Hunter's Mark Versus Crossbow Expert Bonus Action",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/n1c381/hunters_mark_sucks_but_rangers_are_awesome/",
        online_claim="Hunter's Mark often needs around two rounds just to repay the lost Crossbow Expert bonus-action attack.",
        comparison="Matches under the simplified single-target model here: the mark build is still slightly behind on round 1 and clearly ahead by round 2.",
        notes=[
            f"Round 1 cumulative DPR gap: {_render_number(gap[1])}",
            f"Round 2 cumulative DPR gap: {_render_number(gap[2])}",
            f"Break-even round: {break_even}",
        ],
        extracted={"gap_by_round": gap, "break_even_round": break_even},
    )


def summarize_spiritual_weapon(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    gap = {rounds: values["spiritual_weapon"][rounds] - values["guiding_bolt"][rounds] for rounds in values["guiding_bolt"]}
    break_even = next((rounds for rounds, diff in sorted(gap.items()) if diff > 1e-9), None)
    return CaseSummary(
        name="Spiritual Weapon Versus Guiding Bolt",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/k0vw32/spiritual_weapon_is_not_a_good_spell_an_essay_cmv/",
        online_claim="Spiritual Weapon may need multiple rounds to catch up to immediate-damage alternatives, especially once Guiding Bolt's granted advantage is counted.",
        comparison=(
            "The sample reaches break-even by round 2 on direct caster damage alone, which is faster than the thread's skepticism. "
            "That difference is expected because this model omits the allied attack that could cash in Guiding Bolt's advantage."
        ),
        notes=[
            f"Round 1 cumulative DPR gap: {_render_number(gap[1])}",
            f"Round 2 cumulative DPR gap: {_render_number(gap[2])}",
            f"Break-even round in the simplified self-damage model: {break_even}",
        ],
        extracted={"gap_by_round": gap, "break_even_round": break_even},
    )


def summarize_burst_turns(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _one_axis(result)
    return CaseSummary(
        name="Burst Turns, Action Surge, And Haste",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/y6k9az/metamagic_quickened_spell/",
        online_claim="Quickened Spell at level 11 enables six Eldritch Blast beams in one turn; Action Surge allows two leveled action spells; Haste adds one attack, not another full attack routine.",
        comparison="Matches the structural online claims exactly; this sample turns them into explicit expected-damage deltas.",
        notes=[
            f"Quickened Agonizing Eldritch Blast doubles expected damage from {_render_number(values['standard_agonizing_eb'])} to {_render_number(values['quickened_agonizing_eb'])}.",
            f"Action Surge doubles the single-fireball expectation from {_render_number(values['single_fireball'])} to {_render_number(values['double_fireball_action_surge'])}.",
            f"Haste raises the fighter turn from {_render_number(values['fighter_two_attacks'])} to {_render_number(values['fighter_hasted_three_attacks'])}, which is one extra attack rather than another full two-attack action.",
        ],
        extracted=values,
    )


def summarize_magic_missile(relative_path: str) -> CaseSummary:
    result = _load_result(relative_path)
    _write_raw_data(relative_path, result)
    values = _two_axis(result)
    con2 = {rule: _clamp_probability(data[2]) for rule, data in values.items()}
    con5 = {rule: _clamp_probability(data[5]) for rule, data in values.items()}
    return CaseSummary(
        name="Magic Missile Concentration Pressure",
        sample=relative_path,
        source_url="https://www.reddit.com/r/dndnext/comments/164jepm/magic_missile_and_concentration/",
        online_claim="If concentration requires one check per dart, Magic Missile becomes a much stronger concentration breaker than under the one-check ruling.",
        comparison="Matches strongly and numerically: the per-dart interpretation radically increases failure rates, especially at higher slot levels.",
        notes=[
            f"At Con +2, fail chance is {_render_percent(con2['one_check'])} for one total check, {_render_percent(con2['per_dart_slot1'])} for 3 darts, and {_render_percent(con2['per_dart_slot3'])} for 5 darts.",
            f"At Con +5, fail chance is {_render_percent(con5['one_check'])} for one total check, {_render_percent(con5['per_dart_slot1'])} for 3 darts, and {_render_percent(con5['per_dart_slot3'])} for 5 darts.",
        ],
        extracted={"con2": con2, "con5": con5},
    )


SUMMARIZERS = [
    summarize_advantage,
    summarize_elven_accuracy,
    summarize_gwf,
    summarize_gwm_vs_asi,
    summarize_pam_vs_asi,
    summarize_bless,
    summarize_hunters_mark,
    summarize_spiritual_weapon,
    summarize_burst_turns,
    summarize_magic_missile,
]

CASE_PATHS = {
    summarize_advantage: "samples/dnd/discussions/advantage_rules_of_thumb.dice",
    summarize_elven_accuracy: "samples/dnd/discussions/elven_accuracy_crit.dice",
    summarize_gwf: "samples/dnd/discussions/great_weapon_fighting_average.dice",
    summarize_gwm_vs_asi: "samples/dnd/discussions/gwm_vs_asi.dice",
    summarize_pam_vs_asi: "samples/dnd/discussions/polearm_master_vs_asi.dice",
    summarize_bless: "samples/dnd/discussions/bless_party_dpr.dice",
    summarize_hunters_mark: "samples/dnd/discussions/hunters_mark_xbe_rounds.dice",
    summarize_spiritual_weapon: "samples/dnd/discussions/spiritual_weapon_rounds.dice",
    summarize_burst_turns: "samples/dnd/discussions/burst_turns.dice",
    summarize_magic_missile: "samples/dnd/discussions/magic_missile_concentration.dice",
}


def _write_summary_json(summaries: list[CaseSummary]) -> None:
    output_path = REPORT_ROOT / "summary.json"
    payload = [
        {
            "name": summary.name,
            "sample": summary.sample,
            "source_url": summary.source_url,
            "online_claim": summary.online_claim,
            "comparison": summary.comparison,
            "notes": summary.notes,
            "extracted": summary.extracted,
        }
        for summary in summaries
    ]
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_report(summaries: list[CaseSummary]) -> None:
    report_path = REPORT_ROOT / "REPORT.md"
    lines = [
        "# D&D Discussion Comparison Report",
        "",
        "This report is generated from the `samples/dnd/discussions/` programs.",
        "Raw serialized outputs live under `reports/dnd_discussions/data/`.",
        "",
        "## Coverage",
        "",
        f"- Samples executed: {len(summaries)}",
        "- Focus: D&D online discussion claims that are useful as exactness or ergonomics benchmarks",
        "",
        "## Findings",
        "",
    ]
    for summary in summaries:
        lines.extend(
            [
                f"### {summary.name}",
                "",
                f"- Sample: `{summary.sample}`",
                f"- Source: {summary.source_url}",
                f"- Online claim: {summary.online_claim}",
                f"- Comparison: {summary.comparison}",
            ]
        )
        for note in summary.notes:
            lines.append(f"- {note}")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summaries = [summarizer(CASE_PATHS[summarizer]) for summarizer in SUMMARIZERS]
    _write_summary_json(summaries)
    _write_report(summaries)
    print((REPORT_ROOT / "REPORT.md").relative_to(ROOT))
    print((REPORT_ROOT / "summary.json").relative_to(ROOT))


if __name__ == "__main__":
    main()
