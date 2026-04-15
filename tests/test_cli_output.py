import io
import json
import os
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
from dice import interpret_statement


class CliFormattingTest(unittest.TestCase):
    def test_unswept_distribution_uses_pretty_lines(self):
        rendered = dice._format_result_text(interpret_statement("d20 >= 11", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "false: 0.50\n true: 0.50")

    def test_unswept_distribution_aligns_numeric_labels(self):
        rendered = dice._format_result_text(interpret_statement("d20", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "  1: 0.05\n  2: 0.05\n  3: 0.05\n  4: 0.05\n  5: 0.05\n  6: 0.05\n  7: 0.05\n  8: 0.05\n  9: 0.05\n 10: 0.05\n 11: 0.05\n 12: 0.05\n 13: 0.05\n 14: 0.05\n 15: 0.05\n 16: 0.05\n 17: 0.05\n 18: 0.05\n 19: 0.05\n 20: 0.05\n(E): 10.50",
        )

    def test_scalar_distribution_collapses_to_number(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= 11 -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "2.50")

    def test_named_distribution_sweep_uses_table_header(self):
        rendered = dice._format_result_text(interpret_statement("d20 >= [AC:10:12]", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "  /AC    10    11    12\nfalse  0.45  0.50  0.55\n true  0.55  0.50  0.45",
        )

    def test_numeric_distribution_sweep_includes_mean_row(self):
        rendered = dice._format_result_text(interpret_statement("d20 + 6 >= [AC:10:12] -> 2d6 + 4", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "/AC    10    11    12\n  6  0.02  0.02  0.02\n  7  0.05  0.04  0.04\n  8  0.07  0.07  0.06\n  9  0.09  0.09  0.08\n 10  0.12  0.11  0.10\n 11  0.14  0.13  0.12\n 12  0.12  0.11  0.10\n 13  0.09  0.09  0.08\n 14  0.07  0.07  0.06\n 15  0.05  0.04  0.04\n 16  0.02  0.02  0.02\n(E)  9.24  8.69  7.92",
        )

    def test_named_scalar_sweep_uses_single_axis_header(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= [AC:10:12] -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "/AC\n10: 2.75\n11: 2.50\n12: 2.25")

    def test_named_scalar_sweep_aligns_labels(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= [AC:8:12] -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "/AC\n 8: 3.25\n 9: 3.00\n10: 2.75\n11: 2.50\n12: 2.25")

    def test_two_axis_scalar_result_uses_corner_label(self):
        rendered = dice._format_result_text(interpret_statement("~([AC:10:11] + [BONUS:1:2])", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "AC/BONUS      1      2\n      10  11.00  12.00\n      11  12.00  13.00",
        )

    def test_json_output_returns_structured_object(self):
        rendered = dice._format_result_json(interpret_statement("d20 >= 11", roundlevel=2), roundlevel=2)
        payload = json.loads(rendered)
        self.assertEqual(payload["type"], "distributions")
        self.assertEqual(payload["axes"], [])
        self.assertEqual(payload["cells"][0]["coordinates"], [])
        self.assertEqual(
            payload["cells"][0]["distribution"],
            [
                {"outcome": "false", "probability": 0.5},
                {"outcome": "true", "probability": 0.5},
            ],
        )


class CliInteractiveTest(unittest.TestCase):
    def test_set_round_command_updates_repl_rounding(self):
        args = SimpleNamespace(roundlevel=2, grepable=False, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["$ set_round 3", "~(d20 >= 11 -> 5 | 0)", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "round = 3\n2.500\n")

    def test_repl_history_uses_persistent_file(self):
        fake_readline = mock.Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": tmpdir}, clear=False):
                history_path = dice._setup_repl_history(fake_readline)
                dice._save_repl_history(history_path, fake_readline)
        self.assertEqual(history_path, os.path.join(tmpdir, "dice", "history"))
        fake_readline.read_history_file.assert_called_once_with(history_path)
        fake_readline.set_history_length.assert_called_once_with(dice.REPL_HISTORY_LENGTH)
        fake_readline.write_history_file.assert_called_once_with(history_path)


class CliMainIntegrationTest(unittest.TestCase):
    def test_main_prints_json_when_requested(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--json", "d20", ">=", "11"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["type"], "distributions")

    def test_main_uses_interactive_flag_for_repl(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--interactive"]):
            with mock.patch.object(dice, "runinteractive", return_value=0) as runinteractive:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        runinteractive.assert_called_once()

    def test_main_uses_file_flag_for_program_files(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".dice", delete=False) as handle:
            handle.write("1 + 1\n")
            path = handle.name
        try:
            with mock.patch.object(sys, "argv", ["dice.py", "--file", path]):
                with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                    exit_code = dice.main()
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "2.00\n")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
