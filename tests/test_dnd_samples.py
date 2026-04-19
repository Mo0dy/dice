import os
import sys
import tempfile
import unittest
from pathlib import Path

from tests.dnd_cases import all_dnd_cases


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples" / "01_dnd"

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file, interpret_statement
from diceengine import Distribution, FiniteMeasure, Sweep


def only_distribution(result):
    if isinstance(result, Sweep):
        assert result.is_unswept()
        result = result.only_value()
    assert isinstance(result, (Distribution, FiniteMeasure))
    return result


def sample_files():
    if not SAMPLES.exists():
        return []
    return sorted(SAMPLES.rglob("*.dice"))


class DndSampleLibraryTest(unittest.TestCase):
    def test_all_user_facing_sample_files_execute(self):
        files = sample_files()
        self.assertTrue(files, "expected at least one D&D sample file")

        for path in files:
            with self.subTest(sample=str(path.relative_to(ROOT))):
                result = interpret_file(path.read_text(encoding="utf-8"), current_dir=path.parent)
                self.assertIsNotNone(result)

    def test_all_dnd_test_cases_execute(self):
        cases = all_dnd_cases()
        self.assertTrue(cases, "expected at least one D&D test case")

        for case in cases:
            with self.subTest(sample=case.name):
                result = interpret_file(case.source, current_dir=ROOT, source_name=case.name)
                self.assertIsNotNone(result)

    def test_longsword_attack_matches_inline_split_logic(self):
        helper_result = interpret_file(
            'import "std:dnd/weapons.dice"\nlongsword_attack(16, 7, 4)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement(
            "split d20 | == 20 -> 2 d 8 + 4 | + 7 >= 16 -> 1 d 8 + 4 ||"
        )
        self.assertEqual(str(helper_result), str(inline_result))

    def test_paladin_smite_matches_inline_split_logic(self):
        helper_result = interpret_file(
            'import "std:dnd/weapons.dice"\npaladin_smite(17, 8, 4, slot_level=3)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement(
            "split d20 | == 20 -> 2 d 8 + 4 + ((d8 ^ 4) ^ 2) | + 8 >= 17 -> 1 d 8 + 4 + (d8 ^ 4) ||"
        )
        self.assertEqual(str(helper_result), str(inline_result))

    def test_attack_helpers_keep_natural_20_crit_against_impossible_ac(self):
        distribution = only_distribution(
            interpret_file(
                'import "std:dnd/weapons.dice"\nlongsword_attack(40, 0, 4)',
                current_dir=ROOT,
            )
        )
        crit_probability = sum(probability for outcome, probability in distribution.items() if outcome >= 6)
        self.assertAlmostEqual(crit_probability, 0.05)

    def test_magic_missile_uses_slot_level_scaling(self):
        helper_result = interpret_file(
            'import "std:dnd/spells.dice"\nmagic_missile(3)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement("(d4 + 1) ^ 5")
        self.assertEqual(str(helper_result), str(inline_result))

    def test_sacred_flame_uses_level_scaling(self):
        helper_result = interpret_file(
            'import "std:dnd/spells.dice"\nsacred_flame(15, 2, level=11)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement("d20 + 2 < 15 -> 3 d 8 | 0")
        self.assertEqual(str(helper_result), str(inline_result))

    def test_agonizing_blast_is_distinct_from_plain_eldritch_blast(self):
        plain = interpret_file(
            'import "std:dnd/spells.dice"\neldritch_blast_by_level(15, 7, level=11)',
            current_dir=ROOT,
        )
        agonizing = interpret_file(
            'import "std:dnd/spells.dice"\nagonizing_eldritch_blast_by_level(15, 7, 4, level=11)',
            current_dir=ROOT,
        )
        self.assertNotEqual(str(plain), str(agonizing))

    def test_keyword_attack_call_preserves_ac_sweep_shape(self):
        result = interpret_file(
            'import "std:dnd/weapons.dice"\n~longsword_attack([10..22], 7, 4, hit_bonus=d4)',
            current_dir=ROOT,
        )
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].values, tuple(range(10, 23)))

    def test_ability_score_target_counting_works_without_manual_indicator_branch(self):
        direct = interpret_statement("(((d20 >= [TARGET:10..12]) ^ 3) >= 1) $ mean")
        explicit = interpret_statement("(((d20 >= [TARGET:10..12] -> 1 | 0) ^ 3) >= 1) $ mean")
        self.assertEqual(len(direct.axes), len(explicit.axes))
        for direct_axis, explicit_axis in zip(direct.axes, explicit.axes):
            self.assertEqual(direct_axis.name, explicit_axis.name)
            self.assertEqual(direct_axis.values, explicit_axis.values)

        for direct_coordinates, direct_distrib in direct.cells.items():
            target_value = direct_coordinates[0]
            explicit_distrib = explicit.cells[(target_value,)]
            self.assertEqual(len(direct_distrib.keys()), len(explicit_distrib.keys()))
            for direct_outcome, explicit_outcome in zip(sorted(direct_distrib.keys()), sorted(explicit_distrib.keys())):
                self.assertAlmostEqual(direct_outcome, explicit_outcome)
                self.assertAlmostEqual(direct_distrib[direct_outcome], explicit_distrib[explicit_outcome])


if __name__ == "__main__":
    unittest.main()
