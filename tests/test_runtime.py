import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file, interpret_statement
from diceengine import TRUE, FALSE, Distributions


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class RuntimeTest(unittest.TestCase):
    def test_compare_returns_boolean_distribution(self):
        result = only_distribution(interpret_statement("d20 >= 11"))
        self.assertAlmostEqual(result[TRUE], 0.5)
        self.assertAlmostEqual(result[FALSE], 0.5)

    def test_sweep_creates_multiple_distributions(self):
        result = interpret_statement("d20 >= [5:7]")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].values, (5, 6, 7))
        self.assertAlmostEqual(result.cells[(5,)][TRUE], 0.8)
        self.assertAlmostEqual(result.cells[(7,)][FALSE], 0.3)

    def test_branching_returns_distribution_not_table(self):
        result = only_distribution(interpret_statement("d20 >= 11 -> 5 | 0"))
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.5)

    def test_summary_expectation_returns_degenerate_distribution(self):
        result = only_distribution(interpret_statement("~(d20 >= 11 -> 5 | 0)"))
        self.assertEqual(len(list(result.items())), 1)
        outcome, probability = next(iter(result.items()))
        self.assertAlmostEqual(outcome, 2.5)
        self.assertAlmostEqual(probability, 1)

    def test_probability_summary_preserves_sweeps(self):
        result = interpret_statement("!d20[19:20]")
        self.assertEqual(result.axes[0].values, (19, 20))
        self.assertAlmostEqual(result.cells[(19,)][0.05], 1)
        self.assertAlmostEqual(result.cells[(20,)][0.05], 1)

    def test_index_then_compare_keeps_partial_probability_mass(self):
        result = interpret_statement("d20[20] >= 14")
        self.assertEqual(result.axes[0].values, (20,))
        self.assertAlmostEqual(result.cells[(20,)][TRUE], 0.05)
        self.assertAlmostEqual(result.cells[(20,)][FALSE], 0)

    def test_multistatement_program_keeps_scope(self):
        result = only_distribution(interpret_file("attack = d20 >= 11\nattack -> 5"))
        self.assertAlmostEqual(result[5], 0.5)

    def test_elsediv_matches_explicit_else_branch(self):
        shorthand = interpret_statement("d20 < 14 -> 2d10 |/")
        explicit = interpret_statement("d20 < 14 -> 2d10 | 2d10 / 2")
        self.assertEqual(str(shorthand), str(explicit))

    def test_arithmetic_distribution_still_works(self):
        result = only_distribution(interpret_statement("d2 + d2"))
        self.assertAlmostEqual(result[2], 0.25)
        self.assertAlmostEqual(result[3], 0.5)
        self.assertAlmostEqual(result[4], 0.25)

    def test_variable_driven_binary_roll_works_with_spaces(self):
        result = only_distribution(interpret_file("a = 2\nb = 2\na d b"))
        self.assertAlmostEqual(result[2], 0.25)
        self.assertAlmostEqual(result[3], 0.5)
        self.assertAlmostEqual(result[4], 0.25)

    def test_variable_driven_unary_roll_works_with_spaces(self):
        result = only_distribution(interpret_file("sides = 2\nd sides"))
        self.assertAlmostEqual(result[1], 0.5)
        self.assertAlmostEqual(result[2], 0.5)

    def test_variable_driven_keep_high_works_with_spaces(self):
        result = only_distribution(interpret_file("n = 3\ns = 2\nk = 1\nn d s h k"))
        self.assertAlmostEqual(result[1], 0.125)
        self.assertAlmostEqual(result[2], 0.875)

    def test_variable_driven_keep_low_works_with_spaces(self):
        result = only_distribution(interpret_file("n = 3\ns = 2\nk = 1\nn d s l k"))
        self.assertAlmostEqual(result[1], 0.875)
        self.assertAlmostEqual(result[2], 0.125)

    def test_strings_preserve_spaces(self):
        result = interpret_statement('"fire bolt"')
        self.assertEqual(result, "fire bolt")


if __name__ == "__main__":
    unittest.main()
