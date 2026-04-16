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

    def test_negative_explicit_sweep_values_are_allowed(self):
        result = interpret_statement("d1 + [bonus:-2, -1, 0]")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "bonus")
        self.assertEqual(result.axes[0].values, (-2, -1, 0))
        self.assertAlmostEqual(result.cells[(-2,)][-1], 1.0)
        self.assertAlmostEqual(result.cells[(0,)][1], 1.0)

    def test_negative_sweep_ranges_are_allowed(self):
        result = interpret_statement("d1 + [bonus:-2..0]")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "bonus")
        self.assertEqual(result.axes[0].values, (-2, -1, 0))
        self.assertAlmostEqual(result.cells[(-2,)][-1], 1.0)
        self.assertAlmostEqual(result.cells[(0,)][1], 1.0)

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

    def test_choice_distribution_mean_returns_true_probability(self):
        result = only_distribution(interpret_statement("d20 >= 11 $ mean"))
        outcome, probability = next(iter(result.items()))
        self.assertAlmostEqual(outcome, 0.5)
        self.assertAlmostEqual(probability, 1)

    def test_choice_distribution_var_and_std_use_bernoulli_projection(self):
        variance = only_distribution(interpret_statement("d20 >= 11 $ var"))
        stddev = only_distribution(interpret_statement("d20 >= 11 $ std"))
        self.assertAlmostEqual(next(iter(variance.keys())), 0.25)
        self.assertAlmostEqual(next(iter(stddev.keys())), 0.5)

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
        result = only_distribution(interpret_file("plus(x, y) = x + y\n1 $ plus(2)"))
        self.assertEqual(result[3], 1)

    def test_pipeline_chains_functions(self):
        result = only_distribution(interpret_file("double(x) = x * 2\ninc(x) = x + 1\n3 $ double $ inc"))
        self.assertEqual(result[7], 1)

    def test_var_and_std_functions_return_scalar_summaries(self):
        variance = only_distribution(interpret_statement("d2 $ var"))
        stddev = only_distribution(interpret_statement("std(d2)"))
        self.assertAlmostEqual(next(iter(variance.keys())), 0.25)
        self.assertAlmostEqual(next(iter(stddev.keys())), 0.5)

    def test_cum_function_returns_cumulative_distribution(self):
        result = only_distribution(interpret_statement("cum(d4)"))
        self.assertAlmostEqual(result[1], 0.25)
        self.assertAlmostEqual(result[2], 0.5)
        self.assertAlmostEqual(result[3], 0.75)
        self.assertAlmostEqual(result[4], 1.0)

    def test_surv_function_returns_survival_distribution(self):
        result = only_distribution(interpret_statement("surv(d4)"))
        self.assertAlmostEqual(result[1], 0.75)
        self.assertAlmostEqual(result[2], 0.5)
        self.assertAlmostEqual(result[3], 0.25)
        self.assertAlmostEqual(result[4], 0.0)

    def test_type_reports_outer_runtime_shape_for_distribution(self):
        result = interpret_statement("type(d20)")
        self.assertEqual(result, "Sweep[Distribution]")

    def test_type_reports_raw_scalar_literal_shape(self):
        result = interpret_statement("type(1)")
        self.assertEqual(result, "int")

    def test_shape_reports_empty_axes_for_unswept_expression(self):
        result = interpret_statement("shape(d20)")
        self.assertEqual(result, "[]")

    def test_shape_reports_named_sweep_axes_and_values(self):
        result = interpret_statement("shape(d20 >= [AC:10:12])")
        self.assertEqual(result, "[AC: (10, 11, 12)]")

    def test_shape_reports_sweep_literal_axes_and_values(self):
        result = interpret_statement("shape([party:1, 2, 3])")
        self.assertEqual(result, "[party: (1, 2, 3)]")

    def test_shape_reports_multiple_axis_names(self):
        result = interpret_statement("shape([AC:10, 11] + [BONUS:1, 2])")
        self.assertEqual(result, "[AC: (10, 11), BONUS: (1, 2)]")

    def test_cum_and_surv_preserve_existing_sweeps(self):
        result = interpret_statement("cum(d4 + [bonus:0, 1])")
        self.assertEqual(len(result.axes), 1)
        self.assertEqual(result.axes[0].name, "bonus")
        self.assertAlmostEqual(result.cells[(0,)][1], 0.25)
        self.assertAlmostEqual(result.cells[(0,)][4], 1.0)
        self.assertAlmostEqual(result.cells[(1,)][2], 0.25)
        self.assertAlmostEqual(result.cells[(1,)][5], 1.0)

    def test_membership_mean_supports_multi_value_events(self):
        result = only_distribution(interpret_statement("d20 in {19, 20} $ mean"))
        outcome, probability = next(iter(result.items()))
        self.assertAlmostEqual(outcome, 0.1)
        self.assertAlmostEqual(probability, 1)

    def test_multistatement_program_keeps_scope(self):
        result = only_distribution(interpret_file("attack = d20 >= 11\nattack -> 5"))
        self.assertAlmostEqual(result[5], 0.5)

    def test_elsediv_matches_explicit_else_branch(self):
        shorthand = interpret_statement("d20 < 14 -> 2d10 |/")
        explicit = interpret_statement("d20 < 14 -> 2d10 | 2d10 / 2")
        self.assertEqual(str(shorthand), str(explicit))

    def test_elsefloordiv_matches_explicit_else_branch(self):
        shorthand = interpret_statement("d20 < 14 -> 2d10 |//")
        explicit = interpret_statement("d20 < 14 -> 2d10 | 2d10 // 2")
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

    def test_repeat_sum_repeats_independent_evaluations(self):
        result = only_distribution(interpret_statement("repeat_sum(3, d2)"))
        self.assertAlmostEqual(result[3], 0.125)
        self.assertAlmostEqual(result[4], 0.375)
        self.assertAlmostEqual(result[5], 0.375)
        self.assertAlmostEqual(result[6], 0.125)

    def test_repeat_sum_preserves_sweeps_from_inner_expression(self):
        result = interpret_statement("repeat_sum(2, d20 >= [10:11] -> 1 | 0)")
        self.assertEqual(result.axes[0].values, (10, 11))
        self.assertAlmostEqual(result.cells[(10,)][0], 0.2025)
        self.assertAlmostEqual(result.cells[(10,)][1], 0.495)
        self.assertAlmostEqual(result.cells[(10,)][2], 0.3025)

    def test_repeat_sum_accepts_comparison_results_directly(self):
        result = interpret_statement("repeat_sum(2, d20 >= [10:11])")
        self.assertEqual(result.axes[0].values, (10, 11))
        self.assertAlmostEqual(result.cells[(10,)][0], 0.2025)
        self.assertAlmostEqual(result.cells[(10,)][1], 0.495)
        self.assertAlmostEqual(result.cells[(10,)][2], 0.3025)

    def test_repeat_sum_accepts_swept_counts(self):
        result = interpret_statement("repeat_sum([1:3], d2)")
        self.assertEqual(result.axes[0].values, (1, 2, 3))
        self.assertAlmostEqual(result.cells[(1,)][1], 0.5)
        self.assertAlmostEqual(result.cells[(3,)][6], 0.125)

    def test_repeat_sum_preserves_named_sweep_axes(self):
        result = interpret_statement("repeat_sum(2, d20 >= [AC:10:11] -> 1 | 0)")
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

    def test_sumover_accepts_comparison_results(self):
        result = only_distribution(interpret_statement('sumover("party", d20 >= [party:10, 11])'))
        self.assertAlmostEqual(result[0], 0.225)
        self.assertAlmostEqual(result[1], 0.5)
        self.assertAlmostEqual(result[2], 0.275)

    def test_repeat_sum_rejects_non_deterministic_count(self):
        with self.assertRaisesRegex(Exception, "deterministic scalar"):
            interpret_statement("repeat_sum(d2, d6)")

    def test_divide_by_zero_points_at_divisor(self):
        with self.assertRaises(Exception) as error:
            interpret_statement("1 / 0")
        self.assertIn("<input>:1:5", str(error.exception))

    def test_keep_count_error_points_at_keep_operand(self):
        with self.assertRaises(Exception) as error:
            interpret_statement("3 d 6 h 4")
        self.assertIn("<input>:1:3", str(error.exception))

    def test_match_guard_type_error_points_at_guard(self):
        with self.assertRaises(Exception) as error:
            interpret_statement("match d20 as roll | roll = 10 | otherwise = 0")
        self.assertIn("<input>:1:21", str(error.exception))
        self.assertIn("match guards must evaluate to Bernoulli outcomes 0 or 1", str(error.exception))

    def test_add_function_matches_operator(self):
        self.assertEqual(str(interpret_statement("1 + 2")), str(interpret_statement("add(1, 2)")))

    def test_comparison_function_matches_operator(self):
        self.assertEqual(
            str(interpret_statement("d20 >= 11")),
            str(interpret_statement("greaterorequal(d20, 11)")),
        )

    def test_rollhigh_function_matches_operator(self):
        self.assertEqual(
            str(interpret_statement("3d20h1")),
            str(interpret_statement("rollhigh(3, 20, 1)")),
        )

    def test_reselse_function_matches_operator(self):
        self.assertEqual(
            str(interpret_statement("d20 >= 11 -> 5 | 0")),
            str(interpret_statement("d20 >= 11 $ reselse(5, 0)")),
        )

    def test_interactive_parser_error_does_not_end_session(self):
        args = SimpleNamespace(roundlevel=0, verbose=False)
        with mock.patch("builtins.input", side_effect=["1 +", "1 + 1", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertIn("syntax error: expected an expression", stderr.getvalue())
        self.assertIn("<repl>:1:4", stderr.getvalue())
        self.assertIn("hint:", stderr.getvalue())
        self.assertIn("2", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
