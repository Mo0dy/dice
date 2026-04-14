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


if __name__ == "__main__":
    unittest.main()
