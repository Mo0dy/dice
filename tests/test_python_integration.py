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

from dice import D, dice_interpreter, dicefunction
from diceengine import Distribution, FiniteMeasure, TRUE, FALSE, Sweep
from executor import ExactExecutor


def only_distribution(result):
    if isinstance(result, Sweep):
        assert result.is_unswept()
        result = result.only_value()
    assert isinstance(result, (Distribution, FiniteMeasure))
    return result


class PythonIntegrationTest(unittest.TestCase):
    def test_session_accepts_explicit_executor(self):
        session = dice_interpreter(executor=ExactExecutor())
        result = only_distribution(session("1 + 1"))
        self.assertEqual(result[2], 1)

    def test_session_persists_assigned_runtime_values(self):
        session = dice_interpreter()
        result = session("d20 >= 11")
        session.assign("cached", result)
        cached = only_distribution(session("cached"))
        self.assertAlmostEqual(cached[TRUE], 0.5)
        self.assertAlmostEqual(cached[FALSE], 0.5)

    def test_session_assign_rejects_global_reassignment(self):
        session = dice_interpreter()
        session.assign("cached", 1)
        with self.assertRaisesRegex(Exception, "global reassignment"):
            session.assign("cached", 2)

    def test_registers_decorated_python_function(self):
        session = dice_interpreter()

        @dicefunction
        def add_bonus(value, bonus=2):
            return value + bonus

        session.register_function(add_bonus)
        self.assertEqual(session("add_bonus(3)"), 5)
        self.assertEqual(session("add_bonus(bonus=4, value=3)"), 7)

    def test_registers_decorated_distribution_function(self):
        session = dice_interpreter()

        @dicefunction
        def increment(value: Distribution) -> Distribution:
            return Distribution((outcome + 1, probability) for outcome, probability in value.items())

        session.register_function(increment)
        result = session("increment([1..2])")
        self.assertEqual(result.axes[0].values, (1, 2))
        self.assertEqual(result.cells[(1,)][2], 1)
        self.assertEqual(result.cells[(2,)][3], 1)

    def test_decorated_function_lifts_when_called_directly_from_python(self):
        session = dice_interpreter()

        @dicefunction
        def add_two(value):
            return value + 2

        result = add_two(session("[1..3]"))
        self.assertEqual(result.axes[0].values, (1, 2, 3))
        self.assertEqual(result.cells[(1,)], 3)
        self.assertEqual(result.cells[(2,)], 4)
        self.assertEqual(result.cells[(3,)], 5)

    def test_direct_python_and_dice_calls_match_for_decorated_function(self):
        session = dice_interpreter()

        @dicefunction
        def add_two(value):
            return value + 2

        session.register_function(add_two)
        dice_result = session("add_two([1..3])")
        direct_result = add_two(session("[1..3]"))
        self.assertEqual(str(dice_result), str(direct_result))

    def test_duplicate_registered_name_raises(self):
        session = dice_interpreter()

        @dicefunction(name="alias")
        def first(value):
            return value

        @dicefunction(name="alias")
        def second(value):
            return value

        session.register_function(first)
        with self.assertRaisesRegex(Exception, "Duplicate function definition"):
            session.register_function(second)

    def test_register_function_rejects_undecorated_callable(self):
        session = dice_interpreter()

        def add_bonus(value):
            return value + 2

        with self.assertRaisesRegex(Exception, "@dicefunction"):
            session.register_function(add_bonus)

    def test_decorator_name_override_registers_alias(self):
        session = dice_interpreter()

        @dicefunction(name="alias")
        def add_bonus(value):
            return value + 2

        session.register_function(add_bonus)
        self.assertEqual(session("alias(3)"), 5)

    def test_assign_rejects_unsupported_python_values(self):
        session = dice_interpreter()
        with self.assertRaisesRegex(Exception, "Unsupported host value type"):
            session.assign("bad", object())

    def test_registered_function_rejects_unsupported_return_type(self):
        session = dice_interpreter()

        @dicefunction
        def bad():
            return object()

        session.register_function(bad)
        with self.assertRaisesRegex(Exception, "Unsupported host value type"):
            session("bad()")

    def test_registered_function_supports_dice_expression_defaults(self):
        session = dice_interpreter()
        session.assign("default_bonus", 3)

        @dicefunction
        def add_default_bonus(value, bonus=D("default_bonus")):
            return value + bonus

        session.register_function(add_default_bonus)
        self.assertEqual(session("add_default_bonus(4)"), 7)

    def test_decorated_function_rejects_d_defaults_that_reference_parameters(self):
        with self.assertRaisesRegex(Exception, "D\\(\\.\\.\\.\\) defaults may only reference globals, not parameters"):
            @dicefunction
            def bad(value, bonus=D("value + 1")):
                return value + bonus

    def test_decorated_function_rejects_keyword_only_parameters(self):
        with self.assertRaisesRegex(Exception, "POSITIONAL_OR_KEYWORD"):
            @dicefunction
            def keyword_only(value, *, bonus=1):
                return value + bonus

    def test_direct_python_call_rejects_unresolved_d_defaults(self):
        @dicefunction
        def add_default_bonus(value, bonus=D("default_bonus")):
            return value + bonus

        with self.assertRaisesRegex(Exception, "dice-session invocation"):
            add_default_bonus(4)

    def test_cache_enabled_function_reuses_pure_results(self):
        calls = []

        @dicefunction(cache=True)
        def add_bonus(value, bonus=2):
            calls.append((value, bonus))
            return value + bonus

        self.assertEqual(add_bonus(3), 5)
        self.assertEqual(add_bonus(3), 5)
        self.assertEqual(calls, [(3, 2)])

    def test_cache_enabled_sweep_function_is_rejected(self):
        with self.assertRaisesRegex(Exception, "cache=True"):
            @dicefunction(cache=True)
            def summed(value: Sweep[int]):
                return value

    def test_dsl_function_caches_pure_exact_results(self):
        session = dice_interpreter()
        session("double(value): value + value")
        self.assertEqual(only_distribution(session("double(3)"))[6], 1)
        self.assertEqual(len(session.interpreter._function_cache), 1)
        self.assertEqual(only_distribution(session("double(3)"))[6], 1)
        self.assertEqual(len(session.interpreter._function_cache), 1)

    def test_dsl_function_cache_is_invalidated_by_global_assignment(self):
        session = dice_interpreter()
        session("bonus = 1\nwith_bonus(value): value + bonus")
        self.assertEqual(only_distribution(session("with_bonus(3)"))[4], 1)
        self.assertEqual(len(session.interpreter._function_cache), 1)
        with self.assertRaisesRegex(Exception, "global reassignment"):
            session("bonus = 2")

    def test_dsl_function_rejects_sampling_in_body(self):
        session = dice_interpreter()
        session("sample_once(): !d6")
        with self.assertRaisesRegex(Exception, "must stay pure"):
            session("sample_once()")

    def test_dsl_function_rejects_impure_host_calls_in_body(self):
        session = dice_interpreter()
        session('mutate(): r_title("x")')
        with self.assertRaisesRegex(Exception, "must stay pure"):
            session("mutate()")


if __name__ == "__main__":
    unittest.main()
