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

from dice import interpret_statement
from diceengine import Distributions


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class MathCorrectnessTest(unittest.TestCase):
    def test_exact_match_mean_returns_selected_probability(self):
        result = only_distribution(interpret_statement("d20 == 20 $ mean"))
        self.assertEqual(len(list(result.items())), 1)
        outcome, probability = next(iter(result.items()))
        self.assertAlmostEqual(outcome, 0.05)
        self.assertAlmostEqual(probability, 1)

    def test_advantage_keeps_expected_extreme_probability(self):
        result = only_distribution(interpret_statement("d+20"))
        self.assertAlmostEqual(result[20], 39 / 400)

    def test_disadvantage_keeps_expected_extreme_probability(self):
        result = only_distribution(interpret_statement("d-20"))
        self.assertAlmostEqual(result[1], 39 / 400)

    def test_rollhigh_rejects_keep_count_above_dice_count(self):
        with self.assertRaises(Exception):
            interpret_statement("2d6h3")

    def test_rolllow_rejects_keep_count_above_dice_count(self):
        with self.assertRaises(Exception):
            interpret_statement("2d6l3")


if __name__ == "__main__":
    unittest.main()
