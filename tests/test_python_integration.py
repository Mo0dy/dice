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

from dice import dice_interpreter
from diceengine import Distribution, Distributions, TRUE, FALSE
from executor import ExactExecutor


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


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

    def test_registers_raw_python_function(self):
        session = dice_interpreter()

        def add_bonus(value):
            return value + 2

        session.register_function(add_bonus)
        self.assertEqual(session("add_bonus(3)"), 5)

    def test_registers_lifted_python_function(self):
        session = dice_interpreter()

        def increment(value: Distribution) -> Distribution:
            return Distribution((outcome + 1, probability) for outcome, probability in value.items())

        session.register_function(increment)
        result = session("increment([1..2])")
        self.assertEqual(result.axes[0].values, (1, 2))
        self.assertEqual(result.cells[(1,)][2], 1)
        self.assertEqual(result.cells[(2,)][3], 1)

    def test_duplicate_registered_name_raises(self):
        session = dice_interpreter()
        session.register_function(lambda value: value, name="alias")
        with self.assertRaisesRegex(Exception, "Duplicate function definition"):
            session.register_function(lambda value: value, name="alias")

    def test_assign_rejects_unsupported_python_values(self):
        session = dice_interpreter()
        with self.assertRaisesRegex(Exception, "Unsupported host value type"):
            session.assign("bad", object())

    def test_registered_function_rejects_unsupported_return_type(self):
        session = dice_interpreter()

        def bad():
            return object()

        session.register_function(bad)
        with self.assertRaisesRegex(Exception, "Unsupported host value type"):
            session("bad()")


if __name__ == "__main__":
    unittest.main()
