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

from diceengine import Distributions, FALSE, TRUE
from diceparser import DiceParser
from interpreter import Interpreter
from lexer import Lexer


def interpret(text):
    parser = DiceParser(Lexer(text))
    ast = parser.parse() if (";" in text or "\n" in text) else parser.statement()
    return Interpreter(ast).interpret()


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class InterpreterFunctionScopeTest(unittest.TestCase):
    def test_function_scope_is_collected_before_execution(self):
        result = only_distribution(
            interpret("damage(ac): hit(ac) -> 5 | 0\nhit(ac): d20 >= ac\ndamage(11)")
        )
        self.assertAlmostEqual(result[5], 0.5)
        self.assertAlmostEqual(result[0], 0.5)

    def test_parameter_scope_shadows_global_scope(self):
        result = interpret("x = 100\nid(x): x\nid(3)")
        self.assertEqual(result, 3)

    def test_function_body_reads_globals_at_call_time(self):
        result = only_distribution(interpret("bonus = 2\nadd_bonus(x): x + bonus\nadd_bonus(3)"))
        self.assertEqual(result[5], 1)

    def test_variable_and_function_namespaces_stay_separate(self):
        result = only_distribution(interpret("damage = 3\ndamage(x): x + 1\ndamage(damage)"))
        self.assertEqual(result[4], 1)

    def test_function_can_return_swept_distribution(self):
        result = interpret("hit(ac): d20 >= ac\nhit([10:12])")
        self.assertEqual(result.axes[0].values, (10, 11, 12))
        self.assertAlmostEqual(result.cells[(10,)][TRUE], 0.55)
        self.assertAlmostEqual(result.cells[(12,)][FALSE], 0.55)

    def test_zero_argument_function_works_through_interpreter(self):
        result = interpret("always(): 5\nalways()")
        self.assertEqual(result, 5)

    def test_multiline_function_bodies_support_local_assignments(self):
        result = only_distribution(interpret("double_inc(x):\n    y = x + 1\n    y * 2\ndouble_inc(3)"))
        self.assertEqual(result[8], 1)

    def test_dsl_keyword_arguments_bind_by_name(self):
        result = only_distribution(interpret("sum2(a, b): a + b\nsum2(b=4, a=3)"))
        self.assertEqual(result[7], 1)

    def test_builtin_keyword_arguments_bind_by_name(self):
        result = only_distribution(interpret("repeat_sum(value=d2, count=2)"))
        self.assertAlmostEqual(result[2], 0.25)
        self.assertAlmostEqual(result[3], 0.5)
        self.assertAlmostEqual(result[4], 0.25)

    def test_wrong_arity_raises_from_interpreter(self):
        with self.assertRaises(Exception) as error:
            interpret("sum2(a, b): a + b\nsum2(1)")
        self.assertIn("missing required argument b", str(error.exception))
        self.assertIn("<input>:2:1", str(error.exception))
        self.assertIn("hint:", str(error.exception))

    def test_builtin_wrong_arity_uses_clean_hint(self):
        with self.assertRaises(Exception) as error:
            interpret("repeat_sum()")
        self.assertIn("function repeat_sum missing required argument count", str(error.exception))
        self.assertIn("Call it like repeat_sum(count, value).", str(error.exception))

    def test_render_remains_positional_variadic(self):
        with self.assertRaisesRegex(Exception, "does not accept keyword arguments"):
            interpret('render(expr=d20)')

    def test_unknown_function_raises_from_interpreter(self):
        with self.assertRaisesRegex(Exception, "Unknown function"):
            interpret("missing(1)")

    def test_recursion_is_rejected_from_interpreter(self):
        with self.assertRaisesRegex(Exception, "Recursion not supported"):
            interpret("a(x): b(x)\nb(x): a(x)\na(1)")

    def test_plain_identifier_still_uses_variable_scope(self):
        result = only_distribution(interpret("attack = d20 >= 11\nattack"))
        self.assertAlmostEqual(result[TRUE], 0.5)
        self.assertAlmostEqual(result[FALSE], 0.5)

    def test_unknown_name_can_suggest_function_call(self):
        with self.assertRaises(Exception) as error:
            interpret("mea + 1")
        self.assertIn("Did you mean mean?", str(error.exception))

    def test_exact_function_name_used_as_variable_gets_call_hint(self):
        with self.assertRaises(Exception) as error:
            interpret("repeat_sum")
        self.assertIn("unknown name repeat_sum", str(error.exception))
        self.assertIn("repeat_sum is a function. Did you mean repeat_sum(...)?", str(error.exception))

    def test_unknown_function_can_suggest_variable_name(self):
        with self.assertRaises(Exception) as error:
            interpret("bonus = 2\nbonu(1)")
        self.assertIn("Unknown function bonu", str(error.exception))
        self.assertIn("Did you mean bonus?", str(error.exception))

    def test_exact_variable_name_used_as_function_gets_namespace_hint(self):
        with self.assertRaises(Exception) as error:
            interpret("bonus = 2\nbonus(1)")
        self.assertIn("Unknown function bonus", str(error.exception))
        self.assertIn("bonus is a variable, not a function.", str(error.exception))


if __name__ == "__main__":
    unittest.main()
