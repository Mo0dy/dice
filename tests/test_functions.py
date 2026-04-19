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
from diceengine import Distribution, FiniteMeasure, Sweep, TRUE, FALSE
from interpreter import Interpreter


def only_distribution(result):
    if isinstance(result, Sweep):
        assert result.is_unswept()
        result = result.only_value()
    assert isinstance(result, (Distribution, FiniteMeasure))
    return result


class FunctionTest(unittest.TestCase):
    def test_single_argument_function_executes(self):
        result = only_distribution(interpret_file("hit(ac): d20 >= ac\nhit(11)"))
        self.assertAlmostEqual(result[TRUE], 0.5)
        self.assertAlmostEqual(result[FALSE], 0.5)

    def test_multi_argument_function_executes(self):
        result = only_distribution(interpret_file("sum2(a, b): a + b\nsum2(d2, d2)"))
        self.assertAlmostEqual(result[2], 0.25)
        self.assertAlmostEqual(result[3], 0.5)
        self.assertAlmostEqual(result[4], 0.25)

    def test_function_call_inside_larger_expression(self):
        result = only_distribution(interpret_file("inc(x): x + 1\ninc(2) * 3"))
        self.assertEqual(result[9], 1)

    def test_function_body_can_use_spaced_binary_roll(self):
        result = only_distribution(interpret_file("rolln(a, b): a d b\nrolln(2, 2)"))
        self.assertAlmostEqual(result[2], 0.25)
        self.assertAlmostEqual(result[3], 0.5)
        self.assertAlmostEqual(result[4], 0.25)

    def test_function_can_call_other_function(self):
        result = only_distribution(
            interpret_file("hit(ac): d20 >= ac\ndamage(ac): hit(ac) -> 5 | 0\ndamage(11)")
        )
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.5)

    def test_forward_reference_to_later_function_definition(self):
        result = only_distribution(
            interpret_file("damage(ac): hit(ac) -> 5 | 0\nhit(ac): d20 >= ac\ndamage(11)")
        )
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.5)

    def test_parameters_shadow_globals(self):
        result = interpret_file("x = 100\nid(x): x\nid(3)")
        self.assertEqual(result, 3)

    def test_functions_can_read_globals_at_call_time(self):
        result = only_distribution(interpret_file("bonus = 2\nadd_bonus(x): x + bonus\nadd_bonus(3)"))
        self.assertEqual(result[5], 1)

    def test_variable_and_function_can_share_name(self):
        result = only_distribution(interpret_file("damage = 3\ndamage(x): x + 1\ndamage(damage)"))
        self.assertEqual(result[4], 1)

    def test_functions_accept_swept_arguments(self):
        result = interpret_file("hit(ac): d20 >= ac\nhit([10..12])")
        self.assertEqual(result.axes[0].values, (10, 11, 12))
        self.assertAlmostEqual(result.cells[(10,)][TRUE], 0.55)
        self.assertAlmostEqual(result.cells[(12,)][FALSE], 0.55)

    def test_zero_argument_function_is_allowed(self):
        result = interpret_file("always(): 5\nalways()")
        self.assertEqual(result, 5)

    def test_multiline_function_body_uses_final_expression(self):
        result = only_distribution(interpret_file("double_inc(x):\n    y = x + 1\n    y * 2\ndouble_inc(3)"))
        self.assertEqual(result[8], 1)

    def test_multiline_function_body_can_end_with_split_on_following_line(self):
        result = only_distribution(
            interpret_file(
                "chaos_strike(leap_damage):\n"
                "    roll = d20\n"
                "    hit_bonus = 0\n"
                "    split roll as attack_roll\n"
                "    | attack_roll == 1 -> 0\n"
                "    | attack_roll == 20 -> 1\n"
                "    | attack_roll + 7 + hit_bonus >= 13 -> 2\n"
                "    ||\n"
                "chaos_strike(0)"
            )
        )
        self.assertAlmostEqual(result[0], 0.25)
        self.assertAlmostEqual(result[1], 0.05)
        self.assertAlmostEqual(result[2], 0.7)

    def test_local_rebinding_is_allowed_inside_function_body(self):
        result = only_distribution(interpret_file("rebind(x):\n    x = x + 1\n    x = x * 2\n    x\nrebind(3)"))
        self.assertEqual(result[8], 1)

    def test_reserved_operator_name_is_rejected_as_parameter(self):
        with self.assertRaisesRegex(Exception, r"reserved name 'd' cannot be used as a parameter name"):
            interpret_file("f(a, b, c, d): a + b + c + d\nf(1, 2, 3, 4)")

    def test_reserved_operator_name_is_rejected_as_assignment_target(self):
        with self.assertRaisesRegex(Exception, r"reserved name 'd' cannot be used as an assignment target"):
            interpret_file("d = 4\nd")

    def test_keyword_arguments_work_for_dsl_functions(self):
        result = only_distribution(interpret_file("sum2(a, b): a + b\nsum2(b=4, a=3)"))
        self.assertEqual(result[7], 1)

    def test_defaults_work_for_dsl_functions(self):
        result = only_distribution(interpret_file("default_bonus = 2\nadd_bonus(x, bonus=default_bonus): x + bonus\nadd_bonus(3)"))
        self.assertEqual(result[5], 1)

    def test_old_equals_function_definition_is_invalid(self):
        with self.assertRaises(Exception):
            interpret_file("hit(ac) = d20 >= ac\nhit(11)")

    def test_dsl_defaults_cannot_reference_parameters(self):
        with self.assertRaisesRegex(Exception, "defaults may only reference globals, not parameters"):
            interpret_file("bad(x, bonus=x): x + bonus\nbad(3)")

    def test_local_assignment_shadowing_global_emits_warning_once(self):
        session = Interpreter(None)
        interpret_statement("bonus = 2", interpreter=session)
        interpret_statement("f(x):\n    bonus = x\n    bonus = bonus + 1\n    bonus\nf(3)", interpreter=session)
        self.assertEqual(len(session.warnings), 1)
        self.assertIn("local assignment shadows global bonus", session.warnings[0].message)

    def test_duplicate_function_definition_raises(self):
        with self.assertRaisesRegex(Exception, "Duplicate function definition"):
            interpret_file("hit(x): x\nhit(y): y\nhit(1)")

    def test_wrong_arity_raises(self):
        with self.assertRaisesRegex(Exception, "missing required argument b"):
            interpret_file("sum2(a, b): a + b\nsum2(1)")

    def test_unknown_function_raises(self):
        with self.assertRaisesRegex(Exception, "Unknown function"):
            interpret_statement("missing(1)")

    def test_direct_recursion_raises(self):
        with self.assertRaisesRegex(Exception, "Recursion not supported"):
            interpret_file("loop(x): loop(x)\nloop(1)")

    def test_mutual_recursion_raises(self):
        with self.assertRaisesRegex(Exception, "Recursion not supported"):
            interpret_file("a(x): b(x)\nb(x): a(x)\na(1)")

    def test_function_definition_outside_top_level_is_rejected(self):
        with self.assertRaises(Exception):
            interpret_statement("x = (inner(y): y)")

    def test_interactive_session_persists_function_definitions(self):
        session = Interpreter(None)
        interpret_statement("f(a, b): a + b", interpreter=session)
        result = only_distribution(interpret_statement("f(1, 2)", interpreter=session))
        self.assertEqual(result[3], 1)

    def test_interactive_session_persists_variables(self):
        session = Interpreter(None)
        interpret_statement("x = 2", interpreter=session)
        result = only_distribution(interpret_statement("x + 1", interpreter=session))
        self.assertEqual(result[3], 1)


if __name__ == "__main__":
    unittest.main()
