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
from diceengine import Distributions
from directdiceengine import DirectExecutor


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class MatchExpressionTest(unittest.TestCase):
    def test_one_line_match_can_model_crit_hit_miss(self):
        result = only_distribution(
            interpret_statement(
                "match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_multiline_match_can_model_crit_hit_miss(self):
        result = only_distribution(
            interpret_file(
                "match d20 as roll\n| roll == 20 = 10\n| roll + 5 >= 15 = 5\n| otherwise = 0"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_match_works_inside_function_body(self):
        result = only_distribution(
            interpret_file(
                "attack(ac, bonus) = match d20 as roll | roll == 20 = 10 | roll + bonus >= ac = 5 | otherwise = 0\nattack(15, 5)"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_match_preserves_sweeps_in_guards(self):
        result = interpret_file(
            "attack(ac, bonus) = match d20 as roll | roll == 20 = 10 | roll + bonus >= ac = 5 | otherwise = 0\n~attack([15:17], 5)"
        )
        self.assertEqual(result.axes[0].values, (15, 16, 17))
        for coordinates, expected in [((15,), 3.0), ((16,), 2.75), ((17,), 2.5)]:
            distrib = result.cells[coordinates]
            outcome, probability = next(iter(distrib.items()))
            self.assertAlmostEqual(outcome, expected)
            self.assertAlmostEqual(probability, 1)

    def test_match_requires_exhaustive_cases(self):
        with self.assertRaisesRegex(Exception, "left unmatched cases"):
            interpret_statement("match d20 as roll | roll == 20 = 10")

    def test_match_works_with_direct_backend(self):
        result = interpret_statement(
            "match d20 as roll | roll == 20 = 10 | roll + 5 >= 15 = 5 | otherwise = 0",
            executor=DirectExecutor(seed=123),
        )
        distrib = result.only_distribution()
        self.assertEqual(distrib.total_probability(), 1)
        self.assertTrue(set(distrib.keys()).issubset({0, 5, 10}))


if __name__ == "__main__":
    unittest.main()
