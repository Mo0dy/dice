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

from diceengine import Sweep, Distributions, add, greaterorequal, repeat_sum, rollsingle, total, var


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class DiceengineLibraryTest(unittest.TestCase):
    def test_add_is_usable_directly_from_python(self):
        result = only_distribution(add(1, 2))
        self.assertEqual(result[3], 1)

    def test_comparison_is_usable_directly_from_python(self):
        result = only_distribution(greaterorequal(rollsingle(20), 11))
        self.assertAlmostEqual(result["true"], 0.5)
        self.assertAlmostEqual(result["false"], 0.5)

    def test_repeat_sum_is_usable_directly_from_python(self):
        result = only_distribution(repeat_sum(3, rollsingle(2)))
        self.assertAlmostEqual(result[3], 0.125)
        self.assertAlmostEqual(result[4], 0.375)
        self.assertAlmostEqual(result[5], 0.375)
        self.assertAlmostEqual(result[6], 0.125)

    def test_total_reduces_named_python_sweep(self):
        result = only_distribution(total(Sweep([1, 2, 3], name="party")))
        self.assertEqual(result[6], 1)

    def test_var_is_usable_directly_from_python(self):
        result = only_distribution(var(rollsingle(2)))
        self.assertAlmostEqual(next(iter(result.keys())), 0.25)


if __name__ == "__main__":
    unittest.main()
