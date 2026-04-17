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
from diceengine import RecordValue, Sweep


def only_value(result):
    assert isinstance(result, Sweep)
    assert result.is_unswept()
    return result.only_value()


def only_distribution(result):
    value = only_value(result)
    return value


def deterministic_outcome(cell):
    items = list(cell.items())
    assert len(items) == 1
    outcome, probability = items[0]
    assert probability == 1.0
    return outcome


class SweepIndexingTest(unittest.TestCase):
    def test_coordinate_index_fixes_named_axis(self):
        result = interpret_statement("([PLAN:1, 2] + [AC:10, 11])[PLAN: 1]")
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(10,)]), 11)
        self.assertEqual(deterministic_outcome(result.cells[(11,)]), 12)

    def test_axis_spec_reorders_remaining_axes(self):
        result = interpret_statement('([PLAN:1, 2] + [AC:10, 11])["AC", "PLAN"]')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC", "PLAN"))
        self.assertEqual(deterministic_outcome(result.cells[(10, 1)]), 11)
        self.assertEqual(deterministic_outcome(result.cells[(11, 2)]), 13)

    def test_filter_clause_shrinks_axis_domain(self):
        result = interpret_statement("([PLAN:1, 2] + [AC:10, 11, 12])[AC in {10, 12}]")
        self.assertEqual(tuple(axis.name for axis in result.axes), ("PLAN", "AC"))
        self.assertEqual(result.axes[1].values, (10, 12))

    def test_axis_spec_variable_can_drive_indexing(self):
        result = interpret_file('axes = ("AC", "PLAN")\n([PLAN:1, 2] + [AC:10, 11])[axes]')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC", "PLAN"))

    def test_positional_axis_spec_uses_current_axis_order(self):
        result = interpret_statement('([PLAN:1, 2] + [AC:10, 11])[1, 0]')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC", "PLAN"))
        self.assertEqual(deterministic_outcome(result.cells[(10, 1)]), 11)

    def test_positional_coordinate_uses_current_axis_order(self):
        result = interpret_statement('([PLAN:1, 2] + [AC:10, 11])[0: 2]')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(10,)]), 12)

    def test_positional_refs_observe_reordered_current_axis_order(self):
        result = interpret_statement('(([PLAN:1, 2] + [AC:10, 11])["AC", "PLAN"])[0: 10]')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("PLAN",))
        self.assertEqual(deterministic_outcome(result.cells[(1,)]), 11)

    def test_coordinate_record_variable_can_drive_indexing(self):
        result = interpret_file("focus = (PLAN: 2)\n([PLAN:1, 2] + [AC:10, 11])[focus]")
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(10,)]), 12)

    def test_mixed_coordinate_and_axis_spec_values_can_drive_indexing(self):
        result = interpret_file(
            'focus = (PLAN: 2)\naxes = ("AC",)\n([PLAN:1, 2] + [AC:10, 11])[focus, axes]'
        )
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(11,)]), 13)

    def test_sumover_new_value_first_signature_reduces_named_axis(self):
        result = interpret_statement('sumover([PLAN:1, 2] + [AC:10, 11], "PLAN")')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(10,)]), 23)
        self.assertEqual(deterministic_outcome(result.cells[(11,)]), 25)

    def test_meanover_numeric_scalars_returns_numeric_average(self):
        result = only_value(interpret_statement('meanover([X:1, 2, 3], "X")'))
        self.assertEqual(result, 2.0)

    def test_sumover_multi_axis_reduces_cartesian_product(self):
        result = interpret_statement('sumover([PLAN:1, 2] + [LEVEL:10, 20] + [AC:100, 200], ("PLAN", "LEVEL"))')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(100,)]), 466)
        self.assertEqual(deterministic_outcome(result.cells[(200,)]), 866)

    def test_sumover_all_axes_reduces_to_unswept_value(self):
        result = only_distribution(interpret_statement("sumover([X:1, 2, 3])"))
        self.assertEqual(next(iter(result.keys())), 6)

    def test_meanover_distributions_returns_distribution_mixture(self):
        distribution = only_distribution(interpret_statement('meanover(d2 + [bonus:0, 1], "bonus")'))
        self.assertAlmostEqual(distribution[1], 0.25)
        self.assertAlmostEqual(distribution[2], 0.5)
        self.assertAlmostEqual(distribution[3], 0.25)

    def test_meanover_multi_axis_reduces_multiple_axes(self):
        result = only_distribution(interpret_statement('meanover([PLAN:1, 2] + [LEVEL:10, 20], ("PLAN", "LEVEL"))'))
        self.assertAlmostEqual(result[11], 0.25)
        self.assertAlmostEqual(result[12], 0.25)
        self.assertAlmostEqual(result[21], 0.25)
        self.assertAlmostEqual(result[22], 0.25)

    def test_maxover_returns_winning_cell_value(self):
        result = interpret_statement('maxover([PLAN:1, 2] + [AC:10, 11], "PLAN")')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(10,)]), 12)
        self.assertEqual(deterministic_outcome(result.cells[(11,)]), 13)

    def test_maxover_all_axes_reduces_to_unswept_value(self):
        result = only_value(interpret_statement("maxover([X:1, 2, 3])"))
        self.assertEqual(result, 3)

    def test_argmaxover_single_axis_returns_coordinate_record(self):
        result = interpret_statement('argmaxover([PLAN:1, 2] + [AC:10, 11], "PLAN")')
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(result.cells[(10,)], RecordValue((("PLAN", 2),)))

    def test_argmaxover_all_axes_returns_unswept_coordinate_record(self):
        result = only_value(interpret_statement('argmaxover([PLAN:1, 2] + [LEVEL:10, 20])'))
        self.assertEqual(result, RecordValue((("PLAN", 2), ("LEVEL", 20))))

    def test_argmaxover_multi_axis_can_be_used_for_gather(self):
        result = interpret_file(
            'study = [PLAN:1, 2] + [LEVEL:10, 20] + [AC:100, 200]\n'
            'best = argmaxover(study, ("PLAN", "LEVEL"))\n'
            "study[best]"
        )
        self.assertEqual(tuple(axis.name for axis in result.axes), ("AC",))
        self.assertEqual(deterministic_outcome(result.cells[(100,)]), 122)
        self.assertEqual(deterministic_outcome(result.cells[(200,)]), 222)

    def test_indexing_cannot_drop_unfixed_axes_yet(self):
        with self.assertRaisesRegex(Exception, "cannot drop unfixed axes yet"):
            interpret_statement('([PLAN:1, 2] + [LEVEL:10, 20] + [AC:100, 200])[LEVEL: 10, "AC"]')

    def test_indexing_rejects_duplicate_axis_mentions(self):
        with self.assertRaisesRegex(Exception, "cannot mention the same axis twice"):
            interpret_statement('([PLAN:1, 2] + [AC:10, 11])["AC", "AC"]')

    def test_reducer_rejects_duplicate_axis_mentions(self):
        with self.assertRaisesRegex(Exception, "cannot mention the same axis twice"):
            interpret_statement('sumover([PLAN:1, 2] + [AC:10, 11], ("AC", "AC"))')

    def test_indexing_rejects_missing_axis_value(self):
        with self.assertRaisesRegex(Exception, "outside axis"):
            interpret_statement("([PLAN:1, 2] + [AC:10, 11])[PLAN: 3]")


if __name__ == "__main__":
    unittest.main()
