import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "dnd"

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file, interpret_statement


def sample_files():
    roots = [SAMPLES / "at_table", SAMPLES / "analysis"]
    return sorted(path for root in roots for path in root.rglob("*.dice"))


class DndSampleLibraryTest(unittest.TestCase):
    def test_all_sample_files_execute(self):
        files = sample_files()
        self.assertTrue(files, "expected at least one D&D sample file")

        for path in files:
            with self.subTest(sample=str(path.relative_to(ROOT))):
                result = interpret_file(path.read_text(encoding="utf-8"), current_dir=path.parent)
                self.assertIsNotNone(result)

    def test_crit_longsword_matches_inline_match_logic(self):
        helper_result = interpret_file(
            'import "std:dnd/weapons.dice"\ncrit_longsword(16, 7, 4)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement(
            "match d20 as roll | roll == 20 = 2 d 8 + 4 | roll + 7 >= 16 = 1 d 8 + 4 | otherwise = 0"
        )
        self.assertEqual(str(helper_result), str(inline_result))

    def test_paladin_smite_matches_inline_match_logic(self):
        helper_result = interpret_file(
            'import "std:dnd/weapons.dice"\npaladin_smite(17, 8, 4, 3)',
            current_dir=ROOT,
        )
        inline_result = interpret_statement(
            "match d20 as roll | roll == 20 = 2 d 8 + 4 + 6 d 8 | roll + 8 >= 17 = 1 d 8 + 4 + 3 d 8 | otherwise = 0"
        )
        self.assertEqual(str(helper_result), str(inline_result))

    def test_crit_helper_preserves_ac_sweep_shape(self):
        result = interpret_file(
            'import "std:dnd/weapons.dice"\n~crit_longsword([10:22], 7, 4)',
            current_dir=ROOT,
        )
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].values, tuple(range(10, 23)))

    def test_ability_score_target_counting_works_without_manual_indicator_branch(self):
        direct = interpret_statement("((repeat_sum(3, d20 >= [TARGET:10:12])) >= 1) $ mean")
        explicit = interpret_statement("((repeat_sum(3, d20 >= [TARGET:10:12] -> 1 | 0)) >= 1) $ mean")
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
