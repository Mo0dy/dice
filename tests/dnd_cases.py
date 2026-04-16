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
        # Fighter with bless attacking AC 16.
        import "std:dnd/weapons.dice"

        bless_longsword(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "crit_longsword_attack",
        """
        # Shared-roll crit logic using match.
        import "std:dnd/weapons.dice"

        crit_longsword(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "eldritch_blast",
        """
        # Eldritch blast against a moderate AC target.
        import "std:dnd/spells.dice"

        eldritch_blast(15, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "eldritch_blast_three_beams",
        """
        # High-level eldritch blast with three beams.
        import "std:dnd/spells.dice"

        eldritch_blast_action(3, 15, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "fighter_extra_attack",
        """
        # Fighter making two longsword attacks.
        import "std:dnd/weapons.dice"

        fighter_attack_action(2, 16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "fireball_save",
        """
        # Fireball against a creature with +2 Dexterity save.
        import "std:dnd/spells.dice"

        fireball(15, 2)
        """,
    ),
    _case(
        "at_table",
        "great_weapon_master_attack",
        """
        # Great weapon master swing into AC 17.
        import "std:dnd/weapons.dice"

        great_weapon_master(17, 8, 4)
        """,
    ),
    _case(
        "at_table",
        "guiding_bolt",
        """
        # Guiding bolt against AC 15.
        import "std:dnd/spells.dice"

        guiding_bolt(15, 7)
        """,
    ),
    _case(
        "at_table",
        "inflict_wounds",
        """
        # Inflict wounds against AC 15.
        import "std:dnd/spells.dice"

        inflict_wounds(15, 7)
        """,
    ),
    _case(
        "at_table",
        "longsword_attack",
        """
        # Fighter with a longsword attacking AC 16.
        import "std:dnd/weapons.dice"

        longsword_attack(16, 7, 4)
        """,
    ),
    _case(
        "at_table",
        "magic_missile",
        """
        # Third-level magic missile represented as three darts.
        import "std:dnd/spells.dice"

        magic_missile(3)
        """,
    ),
    _case(
        "at_table",
        "paladin_smite_attack",
        """
        # Paladin smite into AC 17 with a third-level slot.
        import "std:dnd/weapons.dice"

        paladin_smite(17, 8, 4, 3)
        """,
    ),
    _case(
        "at_table",
        "rogue_sneak_attack",
        """
        # Rapier sneak attack with 3d6 bonus damage.
        import "std:dnd/weapons.dice"

        rapier_sneak_attack(16, 7, 4, 3)
        """,
    ),
    _case(
        "at_table",
        "sacred_flame",
        """
        # Sacred flame against a creature with +2 Dexterity save.
        import "std:dnd/spells.dice"

        sacred_flame(15, 2)
        """,
    ),
    _case(
        "analysis",
        "ability_scores_4d6h3",
        """
        # D&D ability score analysis using classic 4d6 drop lowest.
        #
        # This fixture keeps the richer analysis that used to live in the sample tree,
        # but it now belongs to the tests because it mainly exists to pin semantics.

        score = 4 d 6 h 3
        mod(x) = (x - 10) / 2

        one_score_exact = score
        any_score_at_least_target = ((repeat_sum(6, score >= [TARGET:3:18])) >= 1) $ mean
        total_modifier_sum = repeat_sum(6, mod(score))
        at_least_one_exact_target = ((repeat_sum(6, score == [TARGET:3:18])) >= 1) $ mean
        one_score_greater_than_x = (score > [X:3:18]) $ mean

        render(one_score_exact, "Ability score", "Single ability score distribution")
        render(any_score_at_least_target, "Target score", "Chance any of 6 scores reaches target")
        render(total_modifier_sum, "Total modifier sum", "Total modifier sum across 6 scores")
        render(at_least_one_exact_target, "Target score", "Chance any of 6 scores equals target")
        render(one_score_greater_than_x, "Threshold x", "Chance a single score is greater than x")
        """,
    ),
    _case(
        "analysis",
        "bless_longsword_vs_ac",
        """
        # Expected blessed longsword damage across armor classes.
        import "std:dnd/weapons.dice"

        ~bless_longsword([10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "crit_longsword_vs_ac",
        """
        # Expected crit-aware longsword damage across armor classes.
        import "std:dnd/weapons.dice"

        ~crit_longsword([10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "eldritch_blast_three_beams_vs_ac",
        """
        # Expected three-beam eldritch blast damage across armor classes.
        import "std:dnd/spells.dice"

        ~eldritch_blast_action(3, [10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "eldritch_blast_vs_ac",
        """
        # Expected eldritch blast damage across armor classes.
        import "std:dnd/spells.dice"

        ~eldritch_blast([10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "fighter_longsword_vs_ac",
        """
        # Expected longsword damage across armor classes.
        import "std:dnd/weapons.dice"

        ~longsword_attack([10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "fighter_two_attacks_vs_ac",
        """
        # Expected two-attack fighter damage across armor classes.
        import "std:dnd/weapons.dice"

        ~fighter_attack_action(2, [10:22], 7, 4)
        """,
    ),
    _case(
        "analysis",
        "fireball_party_total",
        """
        # Party total expected fireball damage across four save bonuses.
        import "std:dnd/spells.dice"

        sumover("party", ~fireball(15, [party:0, 2, 5, 7]))
        """,
    ),
    _case(
        "analysis",
        "fireball_vs_save_bonus",
        """
        # Expected fireball damage across save bonuses.
        import "std:dnd/spells.dice"

        ~fireball(15, [0:9])
        """,
    ),
    _case(
        "analysis",
        "guiding_bolt_vs_ac",
        """
        # Expected guiding bolt damage across armor classes.
        import "std:dnd/spells.dice"

        ~guiding_bolt([10:22], 7)
        """,
    ),
    _case(
        "analysis",
        "gwm_vs_ac",
        """
        # Expected great weapon master damage across armor classes.
        import "std:dnd/weapons.dice"

        ~great_weapon_master([10:22], 8, 4)
        """,
    ),
    _case(
        "analysis",
        "inflict_wounds_vs_ac",
        """
        # Expected inflict wounds damage across armor classes.
        import "std:dnd/spells.dice"

        ~inflict_wounds([10:22], 7)
        """,
    ),
    _case(
        "analysis",
        "magic_missile_vs_darts",
        """
        # Expected magic missile damage as the dart count rises.
        import "std:dnd/spells.dice"

        ~magic_missile([1:6])
        """,
    ),
    _case(
        "analysis",
        "paladin_smite_vs_ac",
        """
        # Expected paladin smite damage across armor classes.
        import "std:dnd/weapons.dice"

        ~paladin_smite([10:22], 8, 4, 3)
        """,
    ),
    _case(
        "analysis",
        "reckless_gwm_vs_ac",
        """
        # Expected reckless great weapon master damage across armor classes.
        import "std:dnd/weapons.dice"

        ~reckless_great_weapon_master([10:22], 8, 4)
        """,
    ),
    _case(
        "analysis",
        "sacred_flame_vs_save_bonus",
        """
        # Expected sacred flame damage across save bonuses.
        import "std:dnd/spells.dice"

        ~sacred_flame(15, [0:9])
        """,
    ),
    _case(
        "analysis",
        "sharpshooter_vs_ac",
        """
        # Expected sharpshooter damage across armor classes.
        import "std:dnd/weapons.dice"

        ~sharpshooter([10:22], 8, 4)
        """,
    ),
    _case(
        "analysis",
        "stat_roll_4d6h3",
        """
        # Single 4d6 drop-lowest stat roll distribution.
        stat_roll() = 4 d 6 h 3

        stat_roll()
        """,
    ),
)


def all_dnd_cases() -> list[DndCase]:
    return list(DND_CASES)
