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
from interpreter import Interpreter


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class SplitExpressionTest(unittest.TestCase):
    def test_one_line_split_can_model_crit_hit_miss(self):
        result = only_distribution(
            interpret_statement(
                "split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_multiline_split_can_model_crit_hit_miss(self):
        result = only_distribution(
            interpret_file(
                "split d20\n| == 20 -> 10\n| + 5 >= 15 -> 5 ||"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_split_works_inside_function_body(self):
        result = only_distribution(
            interpret_file(
                "attack(ac, bonus): split d20 | == 20 -> 10 | + bonus >= ac -> 5 ||\nattack(15, 5)"
            )
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)

    def test_split_preserves_sweeps_in_guards(self):
        result = interpret_file(
            "attack(ac, bonus): split d20 | == 20 -> 10 | + bonus >= ac -> 5 ||\n~attack([15:17], 5)"
        )
        self.assertEqual(result.axes[0].values, (15, 16, 17))
        for coordinates, expected in [((15,), 3.0), ((16,), 2.75), ((17,), 2.5)]:
            distrib = result.cells[coordinates]
            outcome, probability = next(iter(distrib.items()))
            self.assertAlmostEqual(outcome, expected)
            self.assertAlmostEqual(probability, 1)

    def test_split_allows_implicit_zero_tail_with_warning(self):
        interpreter = Interpreter(None)
        result = only_distribution(
            interpret_statement("split d20 | == 20 -> 10 | + 5 >= 15 -> 5", interpreter=interpreter)
        )
        self.assertAlmostEqual(result[10], 0.05)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.45)
        self.assertEqual(len(interpreter.warnings), 1)
        self.assertIn("default remaining cases to 0", interpreter.warnings[0].message)

    def test_split_supports_mixed_anonymous_and_relative_guards(self):
        result = only_distribution(
            interpret_statement(
                'split d20 | @ in {1, 20} -> 10 | + 5 >= 15 -> 5 ||'
            )
        )
        self.assertAlmostEqual(result[10], 0.1)
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.4)

    def test_split_disallows_anonymous_sugar_with_explicit_binding(self):
        with self.assertRaisesRegex(Exception, "explicit split bindings cannot use '@' or relative guards"):
            interpret_statement("split d20 as roll | @ == 20 -> 10 | otherwise -> 0")

    def test_split_works_with_direct_backend(self):
        result = interpret_statement(
            "split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||",
            executor=DirectExecutor(seed=123),
        )
        distrib = result.only_distribution()
        self.assertEqual(distrib.total_probability(), 1)
        self.assertTrue(set(distrib.keys()).issubset({0, 5, 10}))


if __name__ == "__main__":
    unittest.main()
