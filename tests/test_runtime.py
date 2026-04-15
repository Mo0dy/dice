import os
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dice
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

    def test_named_range_sweep_carries_axis_name(self):
        result = interpret_statement("d20 >= [AC:5:7]")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "AC")
        self.assertEqual(result.axes[0].values, (5, 6, 7))
        self.assertAlmostEqual(result.cells[(5,)][TRUE], 0.8)

    def test_named_explicit_sweep_carries_axis_name(self):
        result = interpret_statement("d20 >= [AC:5, 7, 9]")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "AC")
        self.assertEqual(result.axes[0].values, (5, 7, 9))
        self.assertAlmostEqual(result.cells[(9,)][TRUE], 0.6)

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

    def test_mass_function_preserves_sweeps(self):
        result = interpret_statement("mass(d20[19:20])")
        self.assertEqual(result.axes[0].values, (19, 20))
        self.assertAlmostEqual(result.cells[(19,)][0.05], 1)
        self.assertAlmostEqual(result.cells[(20,)][0.05], 1)

    def test_sample_operator_returns_sampled_outcome(self):
        result = only_distribution(interpret_statement("!d20"))
        self.assertEqual(result.total_probability(), 1)
        sampled_outcomes = list(result.keys())
        self.assertEqual(len(sampled_outcomes), 1)
        self.assertIn(sampled_outcomes[0], range(1, 21))

    def test_pipeline_applies_function_to_whole_expression(self):
        result = only_distribution(interpret_statement("d20 >= 11 -> 5 | 0 $ mean"))
        outcome, probability = next(iter(result.items()))
        self.assertAlmostEqual(outcome, 2.5)
        self.assertAlmostEqual(probability, 1)

    def test_pipeline_inserts_value_as_first_argument(self):
        result = only_distribution(interpret_file("add(x, y) = x + y\n1 $ add(2)"))
        self.assertEqual(result[3], 1)

    def test_pipeline_chains_functions(self):
        result = only_distribution(interpret_file("double(x) = x * 2\ninc(x) = x + 1\n3 $ double $ inc"))
        self.assertEqual(result[7], 1)

    def test_var_and_std_functions_return_scalar_summaries(self):
        variance = only_distribution(interpret_statement("d2 $ var"))
        stddev = only_distribution(interpret_statement("std(d2)"))
        self.assertAlmostEqual(next(iter(variance.keys())), 0.25)
        self.assertAlmostEqual(next(iter(stddev.keys())), 0.5)

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

    def test_sum_repeats_independent_evaluations(self):
        result = only_distribution(interpret_statement("sum(3, d2)"))
        self.assertAlmostEqual(result[3], 0.125)
        self.assertAlmostEqual(result[4], 0.375)
        self.assertAlmostEqual(result[5], 0.375)
        self.assertAlmostEqual(result[6], 0.125)

    def test_sum_preserves_sweeps_from_inner_expression(self):
        result = interpret_statement("sum(2, d20 >= [10:11] -> 1 | 0)")
        self.assertEqual(result.axes[0].values, (10, 11))
        self.assertAlmostEqual(result.cells[(10,)][0], 0.2025)
        self.assertAlmostEqual(result.cells[(10,)][1], 0.495)
        self.assertAlmostEqual(result.cells[(10,)][2], 0.3025)

    def test_sum_accepts_swept_counts(self):
        result = interpret_statement("sum([1:3], d2)")
        self.assertEqual(result.axes[0].values, (1, 2, 3))
        self.assertAlmostEqual(result.cells[(1,)][1], 0.5)
        self.assertAlmostEqual(result.cells[(3,)][6], 0.125)

    def test_sum_preserves_named_sweep_axes(self):
        result = interpret_statement("sum(2, d20 >= [AC:10:11] -> 1 | 0)")
        self.assertEqual(result.axes[0].name, "AC")
        self.assertEqual(result.axes[0].values, (10, 11))

    def test_sumover_reduces_named_axis(self):
        result = only_distribution(interpret_statement('sumover("party", [party:1, 2, 3])'))
        self.assertEqual(result[6], 1)

    def test_sumover_preserves_other_axes(self):
        result = interpret_statement('sumover("party", [AC:10, 11] + [party:1, 2])')
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "AC")
        self.assertEqual(result.cells[(10,)][23], 1)
        self.assertEqual(result.cells[(11,)][25], 1)

    def test_total_reduces_single_named_axis(self):
        result = only_distribution(interpret_statement("total([party:1, 2, 3])"))
        self.assertEqual(result[6], 1)

    def test_sumover_rejects_missing_named_axis(self):
        with self.assertRaisesRegex(Exception, "could not find named axis"):
            interpret_statement('sumover("party", [1:3])')

    def test_total_rejects_unnamed_axis(self):
        with self.assertRaisesRegex(Exception, "exactly one named axis"):
            interpret_statement("total([1:3])")

    def test_total_rejects_multiple_axes(self):
        with self.assertRaisesRegex(Exception, "exactly one named axis"):
            interpret_statement("total([party:1, 2] + [AC:10, 11])")

    def test_sumover_rejects_non_numeric_results(self):
        with self.assertRaisesRegex(Exception, "numeric outcomes"):
            interpret_statement('sumover("party", d20 >= [party:10, 11])')

    def test_sum_rejects_non_deterministic_count(self):
        with self.assertRaisesRegex(Exception, "deterministic count"):
            interpret_statement("sum(d2, d6)")

    def test_interactive_parser_error_does_not_end_session(self):
        args = SimpleNamespace(roundlevel=0, grepable=False, verbose=False)
        with mock.patch("builtins.input", side_effect=["1 +", "1 + 1", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertIn("syntax error: Parser exception", stderr.getvalue())
        self.assertIn("2", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
