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

from directdiceengine import DirectExecutor, direct_sample
from dice import interpret_statement
from diceengine import FALSE, TRUE, Distributions


class DirectEngineSmokeTest(unittest.TestCase):
    def test_direct_backend_can_evaluate_branching_expression(self):
        result = direct_sample("d20 >= 11 -> 5 | 0", seed=123)
        self.assertIsInstance(result, Distributions)
        self.assertTrue(result.is_unswept())
        distrib = result.only_distribution()
        self.assertEqual(distrib.total_probability(), 1)
        self.assertTrue(set(distrib.keys()).issubset({0, 5}))

    def test_direct_backend_preserves_sweep_shape(self):
        result = direct_sample("d20 >= [5:7]", seed=123)
        self.assertEqual(result.axes[0].values, (5, 6, 7))
        for distrib in result.cells.values():
            self.assertIn(distrib.total_probability(), (0, 1))
            self.assertTrue(set(distrib.keys()).issubset({TRUE, FALSE}))

    def test_direct_backend_matches_dot_semantics(self):
        result = direct_sample("d20.20", seed=123)
        distrib = result.only_distribution()
        self.assertEqual(len(list(distrib.items())), 1)
        outcome, probability = next(iter(distrib.items()))
        self.assertAlmostEqual(outcome, 0.05)
        self.assertAlmostEqual(probability, 1)

    def test_direct_backend_keeps_deterministic_summary_semantics(self):
        avg_result = direct_sample("2d6 $ mean", seed=123).only_distribution()
        prop_result = direct_sample("mass(d20[20])", seed=123)
        outcome, probability = next(iter(avg_result.items()))
        self.assertAlmostEqual(outcome, 7.0)
        self.assertEqual(probability, 1)
        self.assertEqual(prop_result.axes[0].values, (20,))
        self.assertEqual(prop_result.cells[(20,)][0.05], 1)

    def test_direct_backend_sample_operator_returns_one_outcome(self):
        result = direct_sample("!d20", seed=123).only_distribution()
        self.assertEqual(result.total_probability(), 1)
        sampled_outcomes = list(result.keys())
        self.assertEqual(len(sampled_outcomes), 1)
        self.assertIn(sampled_outcomes[0], range(1, 21))

    def test_interpret_statement_accepts_direct_engine_backend(self):
        result = interpret_statement("d20 >= 11", executor=DirectExecutor(seed=123))
        self.assertTrue(result.is_unswept())
        distrib = result.only_distribution()
        self.assertIn(distrib.total_probability(), (0, 1))
        self.assertTrue(set(distrib.keys()).issubset({TRUE, FALSE}))


if __name__ == "__main__":
    unittest.main()
