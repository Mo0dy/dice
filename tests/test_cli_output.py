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
from interpreter import Interpreter


class CliFormattingTest(unittest.TestCase):
    def test_roundlevel_only_affects_rendering_not_runtime_distribution(self):
        result = interpret_statement("d3", roundlevel=2)
        distrib = result.only_distribution()
        self.assertAlmostEqual(distrib[1], 1 / 3)
        self.assertAlmostEqual(distrib[2], 1 / 3)
        self.assertAlmostEqual(distrib[3], 1 / 3)

    def test_rounded_rendering_handles_wide_distribution_without_runtime_error(self):
        rendered = dice._format_result_text(interpret_statement("2d6 + 2d6", roundlevel=2), roundlevel=2)
        self.assertIn(" 14: 11.27%", rendered)
        self.assertIn("(E): 14", rendered)

    def test_unswept_distribution_uses_pretty_lines(self):
        rendered = dice._format_result_text(interpret_statement("d20 >= 11", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "  0: 50%\n  1: 50%\n(E): 0.50")

    def test_unswept_distribution_aligns_numeric_labels(self):
        rendered = dice._format_result_text(interpret_statement("d20", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "  1: 5%\n  2: 5%\n  3: 5%\n  4: 5%\n  5: 5%\n  6: 5%\n  7: 5%\n  8: 5%\n  9: 5%\n 10: 5%\n 11: 5%\n 12: 5%\n 13: 5%\n 14: 5%\n 15: 5%\n 16: 5%\n 17: 5%\n 18: 5%\n 19: 5%\n 20: 5%\n(E): 10.50",
        )

    def test_scalar_distribution_collapses_to_number(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= 11 -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "2.50")

    def test_string_result_renders_directly(self):
        rendered = dice._format_result_text(interpret_statement("type(d20)"), roundlevel=2)
        self.assertEqual(rendered, "Sweep[Distribution]")

    def test_shape_result_renders_directly(self):
        rendered = dice._format_result_text(interpret_statement("shape(d20 >= [AC:10..12])"), roundlevel=2)
        self.assertEqual(rendered, "[AC: (10, 11, 12)]")

    def test_named_distribution_sweep_uses_table_header(self):
        rendered = dice._format_result_text(interpret_statement("d20 >= [AC:10..12]", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "/AC    10    11    12\n  0   45%   50%   55%\n  1   55%   50%   45%\n(E)  0.55  0.50  0.45",
        )

    def test_distribution_sweep_shows_integral_probabilities_without_decimal_padding(self):
        rendered = dice._format_result_text(interpret_statement("d2 >= [AC:1..3]", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "/AC     1     2     3\n  1  100%   50%    0%\n  0    0%   50%  100%\n(E)     1  0.50     0",
        )

    def test_numeric_distribution_sweep_includes_mean_row(self):
        rendered = dice._format_result_text(interpret_statement("d20 + 6 >= [AC:10..12] -> 2d6 + 4", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "/AC      10      11      12\n  0     15%     20%     25%\n  6   2.36%   2.22%   2.08%\n  7   4.72%   4.44%   4.17%\n  8   7.08%   6.67%   6.25%\n  9   9.44%   8.89%   8.33%\n 10  11.81%  11.11%  10.42%\n 11  14.17%  13.33%  12.50%\n 12  11.81%  11.11%  10.42%\n 13   9.44%   8.89%   8.33%\n 14   7.08%   6.67%   6.25%\n 15   4.72%   4.44%   4.17%\n 16   2.36%   2.22%   2.08%\n(E)    9.35    8.80    8.25",
        )

    def test_named_scalar_sweep_uses_single_axis_header(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= [AC:10..12] -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "/AC\n10: 2.75\n11: 2.50\n12: 2.25")

    def test_named_scalar_sweep_aligns_labels(self):
        rendered = dice._format_result_text(interpret_statement("~(d20 >= [AC:8..12] -> 5 | 0)", roundlevel=2), roundlevel=2)
        self.assertEqual(rendered, "/AC\n 8: 3.25\n 9: 3\n10: 2.75\n11: 2.50\n12: 2.25")

    def test_two_axis_scalar_result_uses_corner_label(self):
        rendered = dice._format_result_text(interpret_statement("~([AC:10..11] + [BONUS:1..2])", roundlevel=2), roundlevel=2)
        self.assertEqual(
            rendered,
            "AC/BONUS   1   2\n      10  11  12\n      11  12  13",
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
                {"outcome": 0, "probability": 0.5},
                {"outcome": 1, "probability": 0.5},
            ],
        )

    def test_json_output_serializes_string_result(self):
        rendered = dice._format_result_json(interpret_statement("type(d20)"), roundlevel=2)
        payload = json.loads(rendered)
        self.assertEqual(payload, {"type": "string", "value": "Sweep[Distribution]"})

    def test_json_output_serializes_shape_string_result(self):
        rendered = dice._format_result_json(interpret_statement("shape(d20 >= [AC:10..12])"), roundlevel=2)
        payload = json.loads(rendered)
        self.assertEqual(payload, {"type": "string", "value": "[AC: (10, 11, 12)]"})

    def test_raw_probability_mode_uses_raw_text_probabilities(self):
        rendered = dice._format_result_text(
            interpret_statement("d20 >= 11", roundlevel=2),
            roundlevel=2,
            probability_mode="raw",
        )
        self.assertEqual(rendered, "  0: 0.50\n  1: 0.50\n(E): 0.50")

    def test_json_can_explicitly_use_percent_probabilities(self):
        rendered = dice._format_result_json(
            interpret_statement("d20 >= 11", roundlevel=2),
            roundlevel=2,
            probability_mode="percent",
        )
        payload = json.loads(rendered)
        self.assertEqual(
            payload["cells"][0]["distribution"],
            [
                {"outcome": 0, "probability": 50.0},
                {"outcome": 1, "probability": 50.0},
            ],
        )


class CliInteractiveTest(unittest.TestCase):
    def test_set_round_command_updates_repl_rounding(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["$ set_round 3", "~(d20 >= 11 -> 5 | 0)", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "round = 3\n2.500\n")

    def test_set_render_mode_command_updates_repl_render_mode(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["$ set_render_mode blocking", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "render_mode = blocking\n")

    def test_set_probability_mode_command_updates_repl_probability_mode(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["$ set_probability_mode raw", "d20 >= 11", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(stdout.getvalue(), "probability_mode = raw\n  0: 0.50\n  1: 0.50\n(E): 0.50\n")

    def test_repl_prints_split_implicit_zero_warning(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["split d20 | == 20 -> 10", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertIn("warning: split omitted a final branch and will default remaining cases to 0", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "  0: 95%\n 10: 5%\n(E): 0.50\n")

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

    def test_repl_completion_uses_interpreter_candidates(self):
        fake_readline = mock.Mock()
        interpreter = Interpreter(None)
        interpreter.global_scope["bonus"] = 2
        interpreter.register_function(lambda ac: ac, name="hit")
        fake_readline.get_line_buffer.return_value = "bo"
        fake_readline.get_begidx.return_value = 0
        fake_readline.get_endidx.return_value = 2

        dice._setup_repl_completion(interpreter, fake_readline)

        completer = fake_readline.set_completer.call_args.args[0]
        self.assertEqual(completer("bo", 0), "bonus")
        self.assertIsNone(completer("bo", 1))
        fake_readline.parse_and_bind.assert_called_once_with("tab: complete")
        fake_readline.set_completer_delims.assert_called_once_with(dice.REPL_COMPLETER_DELIMS)

    def test_repl_errors_show_location_and_hint(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=["1 +", "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("syntax error: expected an expression", stderr.getvalue())
        self.assertIn("<repl>:1:4", stderr.getvalue())
        self.assertIn("hint:", stderr.getvalue())

    def test_repl_reports_unterminated_string_cleanly(self):
        args = SimpleNamespace(roundlevel=2, verbose=False, json_output=False)
        with mock.patch("builtins.input", side_effect=['"abc', "exit"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.runinteractive(args)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("syntax error: unterminated string literal", stderr.getvalue())
        self.assertIn("<repl>:1:1", stderr.getvalue())
        self.assertIn("matching double quote", stderr.getvalue())


class InterpreterCompletionTest(unittest.TestCase):
    def test_identifier_completion_includes_builtins_and_user_symbols(self):
        interpreter = Interpreter(None)
        interpreter.global_scope["bonus"] = 2
        interpret_statement("hit(ac): d20 >= ac", interpreter=interpreter)

        self.assertEqual(interpreter.complete("bo", line_buffer="bo", begidx=0, endidx=2), ["bonus"])
        self.assertEqual(interpreter.complete("hi", line_buffer="hi", begidx=0, endidx=2), ["hit"])
        self.assertEqual(interpreter.complete("gre", line_buffer="gre", begidx=0, endidx=3), ["greater", "greaterorequal"])

    def test_import_completion_omits_dice_extension(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "combat.dice").write_text("hit(ac): d20 >= ac\n", encoding="utf-8")
            (root / "lib").mkdir()
            (root / "lib" / "damage.dice").write_text("damage(ac): ac\n", encoding="utf-8")
            interpreter = Interpreter(None, current_dir=root)

            self.assertEqual(interpreter.complete("co", line_buffer='import "co', begidx=8, endidx=10), ["combat"])

            lib_completions = interpreter.complete("l", line_buffer='import "l', begidx=8, endidx=9)
            self.assertIn("lib/", lib_completions)
            self.assertIn("lib/damage", lib_completions)

            self.assertEqual(interpreter.complete("lib/da", line_buffer='import "lib/da', begidx=8, endidx=14), ["lib/damage"])

    def test_import_completion_supports_stdlib_prefix(self):
        interpreter = Interpreter(None)
        completions = interpreter.complete(
            "std:dnd/wea",
            line_buffer='import "std:dnd/wea',
            begidx=8,
            endidx=19,
        )
        self.assertEqual(completions, ["std:dnd/weapons"])

    def test_import_completion_expands_single_stdlib_directory(self):
        interpreter = Interpreter(None)
        completions = interpreter.complete(
            "std:",
            line_buffer='import "std:',
            begidx=8,
            endidx=12,
        )
        self.assertIn("std:dnd/", completions)
        self.assertIn("std:dnd/spells", completions)


class CliMainIntegrationTest(unittest.TestCase):
    def test_main_prints_json_when_requested(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--json", "d20", ">=", "11"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["type"], "distributions")

    def test_main_waits_for_rendered_figures_after_file_execution(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "plot.dice"
            path.write_text('render(d20, "Roll", "Title")\n', encoding="utf-8")
            with mock.patch.object(sys, "argv", ["dice.py", "--file", str(path)]):
                with mock.patch("dice.wait_for_rendered_figures") as wait_for_rendered_figures:
                    with mock.patch("sys.stdout", new=io.StringIO()):
                        exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        wait_for_rendered_figures.assert_called_once_with(
            dice.RenderConfig.from_mode("deferred")
        )

    def test_main_honors_script_render_mode_toggle(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "plot.dice"
            path.write_text('set_render_mode("blocking")\nrender(d20, "Roll", "Title")\n', encoding="utf-8")
            with mock.patch.object(sys, "argv", ["dice.py", "--file", str(path)]):
                with mock.patch("dice.wait_for_rendered_figures") as wait_for_rendered_figures:
                    with mock.patch("sys.stdout", new=io.StringIO()):
                        exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        wait_for_rendered_figures.assert_called_once_with(
            dice.RenderConfig.from_mode("blocking")
        )

    def test_main_json_defaults_to_raw_probabilities_even_with_percent_text_default(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--json", "d20", ">=", "11"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual([entry["outcome"] for entry in payload["cells"][0]["distribution"]], [0, 1])
        self.assertAlmostEqual(payload["cells"][0]["distribution"][0]["probability"], 0.5)
        self.assertAlmostEqual(payload["cells"][0]["distribution"][1]["probability"], 0.5)

    def test_main_json_honors_script_probability_mode_toggle(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "probabilities.dice"
            path.write_text('set_probability_mode("percent")\nd20 >= 11\n', encoding="utf-8")
            with mock.patch.object(sys, "argv", ["dice.py", "--json", "--file", str(path)]):
                with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                    exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual([entry["outcome"] for entry in payload["cells"][0]["distribution"]], [0, 1])
        self.assertAlmostEqual(payload["cells"][0]["distribution"][0]["probability"], 50.0)
        self.assertAlmostEqual(payload["cells"][0]["distribution"][1]["probability"], 50.0)

    def test_main_json_defaults_to_unrounded_output(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--json", "d3"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload["cells"][0]["distribution"],
            [
                {"outcome": 1, "probability": 1 / 3},
                {"outcome": 2, "probability": 1 / 3},
                {"outcome": 3, "probability": 1 / 3},
            ],
        )

    def test_main_json_honors_explicit_roundlevel(self):
        with mock.patch.object(sys, "argv", ["dice.py", "--json", "-R", "2", "d3"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload["cells"][0]["distribution"],
            [
                {"outcome": 1, "probability": 0.33},
                {"outcome": 2, "probability": 0.33},
                {"outcome": 3, "probability": 0.33},
            ],
        )

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
            self.assertEqual(stdout.getvalue(), "2\n")
        finally:
            os.unlink(path)

    def test_main_file_print_statement_uses_cli_formatting(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".dice", delete=False) as handle:
            handle.write("print d20 >= 11\n")
            path = handle.name
        try:
            with mock.patch.object(sys, "argv", ["dice.py", "--file", path]):
                with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                    exit_code = dice.main()
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "  0: 50%\n  1: 50%\n(E): 0.50\n")
        finally:
            os.unlink(path)

    def test_main_prints_formatted_errors_for_bad_commands(self):
        with mock.patch.object(sys, "argv", ["dice.py", "1", "+"]):
            with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
                    exit_code = dice.main()
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("syntax error: expected an expression", stderr.getvalue())
        self.assertIn("<command>:1:4", stderr.getvalue())
        self.assertIn("hint:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
