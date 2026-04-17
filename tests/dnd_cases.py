from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RESULTS = ROOT / "tests" / "expected_results" / "dnd_cases"


@dataclass(frozen=True)
class DndCase:
    name: str
    source: str
    snapshot_path: Path


def _program(text: str) -> str:
    return dedent(text).strip() + "\n"


def _case(group: str, name: str, source: str) -> DndCase:
    return DndCase(
        name=f"tests/dnd_cases/{group}/{name}.dice",
        source=_program(source),
        snapshot_path=EXPECTED_RESULTS / group / f"{name}.json",
    )


DND_CASES = (
    _case(
        "at_table",
        "bless_longsword_attack",
        """
        import "std:dnd/weapons.dice"

        longsword_attack(16, 7, 4, hit_bonus=d4)
        """,
    ),
    _case(
        "at_table",
        "burning_hands_first_level",
        """
        import "std:dnd/spells.dice"

        burning_hands(14, 2, slot_level=1)
        """,
    ),
    _case(
        "at_table",
        "chromatic_orb_second_level",
        """
        import "std:dnd/spells.dice"

        chromatic_orb(15, 7, slot_level=2)
        """,
    ),
    _case(
        "at_table",
        "crit_longsword_attack",
        """
        import "std:dnd/weapons.dice"

        longsword_attack(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "eldritch_blast",
        """
        import "std:dnd/spells.dice"

        eldritch_blast(15, 7)
        """,
    ),
    _case(
        "at_table",
        "eldritch_blast_three_beams",
        """
        import "std:dnd/spells.dice"

        eldritch_blast_by_level(15, 7, level=11)
        """,
    ),
    _case(
        "at_table",
        "agonizing_eldritch_blast_three_beams",
        """
        import "std:dnd/spells.dice"

        agonizing_eldritch_blast_by_level(15, 7, 4, level=11)
        """,
    ),
    _case(
        "at_table",
        "fighter_extra_attack",
        """
        import "std:dnd/weapons.dice"

        fighter_attack_action(2, 16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "fire_bolt_level_11",
        """
        import "std:dnd/spells.dice"

        fire_bolt(15, 8, level=11)
        """,
    ),
    _case(
        "at_table",
        "fireball_save",
        """
        import "std:dnd/spells.dice"

        fireball(15, 2, slot_level=3)
        """,
    ),
    _case(
        "at_table",
        "great_weapon_master_attack",
        """
        import "std:dnd/weapons.dice"

        great_weapon_master(17, 8, 4)
        """,
    ),
    _case(
        "at_table",
        "greatsword_gwf_attack",
        """
        import "std:dnd/weapons.dice"

        greatsword_attack_gwf(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "guiding_bolt",
        """
        import "std:dnd/spells.dice"

        guiding_bolt(15, 7, slot_level=1)
        """,
    ),
    _case(
        "at_table",
        "hunters_mark_longbow_attack",
        """
        import "std:dnd/weapons.dice"

        hunters_mark_longbow(16, 9, 4)
        """,
    ),
    _case(
        "at_table",
        "ice_knife_first_level",
        """
        import "std:dnd/spells.dice"

        ice_knife(15, 7, 2, 14, slot_level=1)
        """,
    ),
    _case(
        "at_table",
        "inflict_wounds",
        """
        import "std:dnd/spells.dice"

        inflict_wounds(15, 7, slot_level=1)
        """,
    ),
    _case(
        "at_table",
        "lightning_bolt_third_level",
        """
        import "std:dnd/spells.dice"

        lightning_bolt(15, 2, slot_level=3)
        """,
    ),
    _case(
        "at_table",
        "longbow_sharpshooter_attack",
        """
        import "std:dnd/weapons.dice"

        longbow_sharpshooter(16, 9, 4)
        """,
    ),
    _case(
        "at_table",
        "longsword_attack",
        """
        import "std:dnd/weapons.dice"

        longsword_attack(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "magic_missile",
        """
        import "std:dnd/spells.dice"

        magic_missile(3)
        """,
    ),
    _case(
        "at_table",
        "paladin_smite_attack",
        """
        import "std:dnd/weapons.dice"

        paladin_smite(17, 8, 4, slot_level=3)
        """,
    ),
    _case(
        "at_table",
        "paladin_smite_vs_fiend",
        """
        import "std:dnd/weapons.dice"

        paladin_smite_vs_fiend(17, 8, 4, slot_level=5)
        """,
    ),
    _case(
        "at_table",
        "rogue_sneak_attack",
        """
        import "std:dnd/weapons.dice"

        rapier_sneak_attack(16, 7, 4, 3)
        """,
    ),
    _case(
        "at_table",
        "sacred_flame",
        """
        import "std:dnd/spells.dice"

        sacred_flame(15, 2, level=5)
        """,
    ),
    _case(
        "at_table",
        "scorching_ray_second_level",
        """
        import "std:dnd/spells.dice"

        scorching_ray(15, 7, slot_level=2)
        """,
    ),
    _case(
        "at_table",
        "shatter_second_level",
        """
        import "std:dnd/spells.dice"

        shatter(15, 1, slot_level=2)
        """,
    ),
    _case(
        "at_table",
        "spirit_guardians_third_level",
        """
        import "std:dnd/spells.dice"

        spirit_guardians(15, 2, slot_level=3)
        """,
    ),
    _case(
        "at_table",
        "toll_the_dead_wounded",
        """
        import "std:dnd/spells.dice"

        toll_the_dead_wounded(15, 2, level=11)
        """,
    ),
    _case(
        "analysis",
        "ability_scores_4d6h3",
        """
        import "std:dnd/core.dice"

        score = 4 d 6 h 3

        one_score_exact = score
        any_score_at_least_target = (((score >= [TARGET:3..18]) ^ 6) >= 1) $ mean
        total_modifier_sum = ability_mod(score) ^ 6
        at_least_one_exact_target = (((score == [TARGET:3..18]) ^ 6) >= 1) $ mean
        one_score_greater_than_x = (score > [X:3..18]) $ mean

        render(one_score_exact, "Ability score", "Single ability score distribution")
        renderp(any_score_at_least_target, "Target score", "Chance any of 6 scores reaches target")
        render(total_modifier_sum, "Total modifier sum", "Total modifier sum across 6 scores")
        renderp(at_least_one_exact_target, "Target score", "Chance any of 6 scores equals target")
        renderp(one_score_greater_than_x, "Threshold x", "Chance a single score is greater than x")
        """,
    ),
    _case(
        "analysis",
        "agonizing_eldritch_blast_three_beams_vs_ac",
        """
        import "std:dnd/spells.dice"

        ~agonizing_eldritch_blast_by_level([10..22], 7, 4, level=11)
        """,
    ),
    _case(
        "analysis",
        "bless_longsword_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~longsword_attack([10..22], 7, 4, hit_bonus=d4)
        """,
    ),
    _case(
        "analysis",
        "cantrip_showdown_by_level",
        """
        import "std:dnd/spells.dice"

        cantrip_damage(plan, level):
            split plan as name | name == "fire_bolt" -> fire_bolt(15, 8, level=level) $ mean | name == "sacred_flame" -> sacred_flame(15, 2, level=level) $ mean | name == "toll_the_dead" -> toll_the_dead_wounded(15, 2, level=level) $ mean | otherwise -> agonizing_eldritch_blast_by_level(15, 7, 4, level=level) $ mean

        cantrip_damage([PLAN:"fire_bolt", "sacred_flame", "toll_the_dead", "agonizing_eldritch_blast"], [LEVEL:1, 5, 11, 17])
        """,
    ),
    _case(
        "analysis",
        "crit_longsword_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~longsword_attack([10..22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "eldritch_blast_three_beams_vs_ac",
        """
        import "std:dnd/spells.dice"

        ~eldritch_blast_by_level([10..22], 7, level=11)
        """,
    ),
    _case(
        "analysis",
        "eldritch_blast_vs_ac",
        """
        import "std:dnd/spells.dice"

        ~eldritch_blast([10..22], 7)
        """,
    ),
    _case(
        "analysis",
        "fighter_longsword_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~longsword_attack([10..22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "fighter_two_attacks_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~fighter_attack_action(2, [10..22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "fireball_party_total",
        """
        import "std:dnd/spells.dice"

        sumover(~fireball(15, [party:0, 2, 5, 7], slot_level=3), "party")
        """,
    ),
    _case(
        "analysis",
        "fireball_vs_save_bonus",
        """
        import "std:dnd/spells.dice"

        ~fireball(15, [0..9], slot_level=3)
        """,
    ),
    _case(
        "analysis",
        "greatsword_gwf_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~greatsword_attack_gwf([10..22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "guiding_bolt_vs_ac",
        """
        import "std:dnd/spells.dice"

        ~guiding_bolt([10..22], 7, slot_level=1)
        """,
    ),
    _case(
        "analysis",
        "gwm_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~great_weapon_master([10..22], 8, 4)
        """,
    ),
    _case(
        "analysis",
        "hunters_mark_longbow_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~hunters_mark_longbow([10..22], 9, 4)
        """,
    ),
    _case(
        "analysis",
        "inflict_wounds_vs_ac",
        """
        import "std:dnd/spells.dice"

        ~inflict_wounds([10..22], 7, slot_level=1)
        """,
    ),
    _case(
        "analysis",
        "magic_missile_vs_slot",
        """
        import "std:dnd/spells.dice"

        ~magic_missile([1..9])
        """,
    ),
    _case(
        "analysis",
        "paladin_smite_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~paladin_smite([10..22], 8, 4, slot_level=3)
        """,
    ),
    _case(
        "analysis",
        "reckless_gwm_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~great_weapon_master([10..22], 8, 4, roll=d+20)
        """,
    ),
    _case(
        "analysis",
        "sacred_flame_vs_save_bonus",
        """
        import "std:dnd/spells.dice"

        ~sacred_flame(15, [0..9], level=11)
        """,
    ),
    _case(
        "analysis",
        "scorching_ray_vs_slot_level",
        """
        import "std:dnd/spells.dice"

        ~scorching_ray(15, 7, slot_level=[2..9])
        """,
    ),
    _case(
        "analysis",
        "sharpshooter_vs_ac",
        """
        import "std:dnd/weapons.dice"

        ~sharpshooter([10..22], 8, 4)
        """,
    ),
    _case(
        "analysis",
        "spell_slot_showdown",
        """
        import "std:dnd/spells.dice"

        slot_damage(plan, slot_level):
            split plan as name | name == "chromatic_orb" -> chromatic_orb(15, 7, slot_level=slot_level) $ mean | name == "guiding_bolt" -> guiding_bolt(15, 7, slot_level=slot_level) $ mean | name == "scorching_ray" -> scorching_ray(15, 7, slot_level=slot_level) $ mean | name == "magic_missile" -> magic_missile(slot_level=slot_level) $ mean | otherwise -> fireball(15, 2, slot_level=slot_level) $ mean

        slot_damage([PLAN:"chromatic_orb", "guiding_bolt", "scorching_ray", "magic_missile", "fireball"], [SLOT:3, 4, 5])
        """,
    ),
    _case(
        "analysis",
        "stat_roll_4d6h3",
        """
        stat_roll(): 4 d 6 h 3

        stat_roll()
        """,
    ),
)


def all_dnd_cases() -> list[DndCase]:
    return list(DND_CASES)
