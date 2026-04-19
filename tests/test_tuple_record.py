import json
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

import dice
from dice import dice_interpreter, dicefunction, interpret_file, interpret_statement
from diceengine import Distribution, FiniteMeasure, RecordValue, Sweep, SweepValues, TupleValue


def only_distribution(result):
    if isinstance(result, Sweep):
        assert result.is_unswept()
        result = result.only_value()
    assert isinstance(result, (Distribution, FiniteMeasure))
    return result


class TupleRecordLiteralTest(unittest.TestCase):
    def test_empty_tuple_literal(self):
        result = interpret_statement("()")
        self.assertEqual(result, TupleValue(()))

    def test_parenthesized_scalar_is_grouping(self):
        result = interpret_statement("(1)")
        self.assertEqual(result, 1)

    def test_singleton_tuple_literal_requires_trailing_comma(self):
        result = interpret_statement("(1,)")
        self.assertEqual(result, TupleValue((1,)))

    def test_multi_tuple_literal(self):
        result = interpret_statement('(1, "two", 3)')
        self.assertEqual(result, TupleValue((1, "two", 3)))

    def test_identifier_key_record_literal(self):
        result = interpret_statement('(PLAN: "gwm", LEVEL: 11)')
        self.assertEqual(result, RecordValue((("PLAN", "gwm"), ("LEVEL", 11))))

    def test_integer_key_record_literal(self):
        result = interpret_statement("(0: 5, 1: 10)")
        self.assertEqual(result, RecordValue(((0, 5), (1, 10))))

    def test_mixed_tuple_and_record_entries_are_rejected(self):
        with self.assertRaisesRegex(Exception, "cannot mix tuple and record entries"):
            interpret_statement('(1, PLAN: "gwm")')

    def test_duplicate_record_keys_are_rejected(self):
        with self.assertRaisesRegex(Exception, "duplicate record key"):
            interpret_statement("(PLAN: 11, PLAN: 12)")

    def test_empty_record_syntax_is_rejected(self):
        with self.assertRaises(Exception):
            interpret_statement("(:)")


class TupleRecordRuntimeTest(unittest.TestCase):
    def test_tuple_can_flow_through_dsl_function(self):
        result = interpret_file("identity(x): x\nidentity((1, 2))")
        self.assertEqual(result, TupleValue((1, 2)))

    def test_record_can_flow_through_dsl_function(self):
        result = interpret_file("identity(x): x\nidentity((PLAN: 11))")
        self.assertEqual(result, RecordValue((("PLAN", 11),)))

    def test_tuple_is_valid_distribution_outcome(self):
        result = only_distribution(interpret_statement("d{(1,), (2,)}"))
        self.assertIn(TupleValue((1,)), result.keys())
        self.assertIn(TupleValue((2,)), result.keys())

    def test_record_is_valid_distribution_outcome(self):
        result = only_distribution(interpret_statement("d{(PLAN: 1), (PLAN: 2)}"))
        self.assertIn(RecordValue((("PLAN", 1),)), result.keys())
        self.assertIn(RecordValue((("PLAN", 2),)), result.keys())

    def test_type_reports_tuple(self):
        result = interpret_statement("type(())")
        self.assertEqual(result, "tuple")

    def test_type_reports_record(self):
        result = interpret_statement("type((PLAN: 11))")
        self.assertEqual(result, "record")

    def test_tuple_equality_is_rejected(self):
        with self.assertRaisesRegex(Exception, "comparisons do not support tuple or record values yet"):
            interpret_statement("(1,) == (1,)")

    def test_record_equality_is_rejected(self):
        with self.assertRaisesRegex(Exception, "comparisons do not support tuple or record values yet"):
            interpret_statement("(PLAN: 1) == (PLAN: 1)")

    def test_tuple_membership_is_rejected(self):
        with self.assertRaisesRegex(Exception, "in does not support tuple or record values yet"):
            interpret_statement("(1,) in {(1,), (2,)}")


class TupleRecordFormattingTest(unittest.TestCase):
    def test_text_output_renders_tuple(self):
        rendered = dice._format_result_text(interpret_statement('(1, "two")'))
        self.assertEqual(rendered, '(1, "two")')

    def test_text_output_renders_record(self):
        rendered = dice._format_result_text(interpret_statement('(PLAN: "gwm", LEVEL: 11)'))
        self.assertEqual(rendered, '(PLAN: "gwm", LEVEL: 11)')

    def test_json_output_serializes_top_level_tuple(self):
        payload = json.loads(dice._format_result_json(interpret_statement('(1, "two")')))
        self.assertEqual(
            payload,
            {"type": "tuple", "items": [1, "two"]},
        )

    def test_json_output_serializes_top_level_record(self):
        payload = json.loads(dice._format_result_json(interpret_statement('(PLAN: "gwm", LEVEL: 11)')))
        self.assertEqual(
            payload,
            {
                "type": "record",
                "entries": [
                    {"key_kind": "identifier", "key": "PLAN", "value": "gwm"},
                    {"key_kind": "identifier", "key": "LEVEL", "value": 11},
                ],
            },
        )

    def test_json_output_serializes_structured_distribution_outcomes(self):
        payload = json.loads(dice._format_result_json(interpret_statement("d{(1,), (2,)}")))
        self.assertEqual(
            payload["distribution"],
            [
                {"outcome": {"type": "tuple", "items": [1]}, "probability": 0.5},
                {"outcome": {"type": "tuple", "items": [2]}, "probability": 0.5},
            ],
        )

    def test_json_output_serializes_structured_axis_values_and_cell_scalars(self):
        result = Sweep.from_values(SweepValues((TupleValue((1,)), TupleValue((2,))), name="CASE"))
        payload = json.loads(dice._format_result_json(result))
        self.assertEqual(
            payload["axes"][0]["values"],
            [
                {"type": "tuple", "items": [1]},
                {"type": "tuple", "items": [2]},
            ],
        )
        self.assertEqual(
            payload["cells"][0]["value"],
            {"kind": "tuple", "value": {"type": "tuple", "items": [1]}},
        )

    def test_json_output_preserves_record_entry_order(self):
        result = Sweep.from_values(
            SweepValues(
                (
                    RecordValue((("PLAN", "gwm"), ("LEVEL", 11))),
                    RecordValue((("PLAN", "longbow"), ("LEVEL", 11))),
                ),
                name="CASE",
            )
        )
        payload = json.loads(dice._format_result_json(result))
        self.assertEqual(
            payload["axes"][0]["values"][0],
            {
                "type": "record",
                "entries": [
                    {"key_kind": "identifier", "key": "PLAN", "value": "gwm"},
                    {"key_kind": "identifier", "key": "LEVEL", "value": 11},
                ],
            },
        )


class TupleRecordPythonInteropTest(unittest.TestCase):
    def test_session_assign_accepts_record_value(self):
        session = dice_interpreter()
        session.assign("coord", RecordValue((("PLAN", "gwm"), ("LEVEL", 11))))
        result = session("coord")
        self.assertEqual(result, RecordValue((("PLAN", "gwm"), ("LEVEL", 11))))

    def test_decorated_function_can_return_record_value(self):
        session = dice_interpreter()

        @dicefunction
        def make_coord():
            return RecordValue((("PLAN", "gwm"), ("LEVEL", 11)))

        session.register_function(make_coord)
        result = session("make_coord()")
        self.assertEqual(result, RecordValue((("PLAN", "gwm"), ("LEVEL", 11))))

    def test_decorated_function_can_receive_tuple_value_from_dice(self):
        session = dice_interpreter()

        @dicefunction
        def passthrough(value):
            return value

        session.register_function(passthrough)
        result = session("passthrough((1, 2))")
        self.assertEqual(result, TupleValue((1, 2)))


if __name__ == "__main__":
    unittest.main()
