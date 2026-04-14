import os
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dice
import viewer
from dice import interpret_file, interpret_statement
from diceengine import Distributions


class RenderStatementTest(unittest.TestCase):
    def test_render_single_expression_calls_render_result(self):
        mock_outcome = viewer.RenderOutcome(viewer.RenderSpec("bar", "Outcome", "Probability"), None)
        with mock.patch.object(viewer, "render_result", return_value=mock_outcome) as render_result:
            result = interpret_statement("render(d20)")
        self.assertIsNone(result)
        render_result.assert_called_once()
        rendered = render_result.call_args.args[0]
        self.assertIsInstance(rendered, Distributions)

    def test_render_comparison_calls_render_comparison(self):
        program = "a = d20\nb = d20 + 1\nrender(a, \"a\", b, \"b\")"
        mock_outcome = viewer.RenderOutcome(viewer.RenderSpec("compare_bar", "Outcome", "Probability", ("a", "b")), None)
        with mock.patch.object(viewer, "render_comparison", return_value=mock_outcome) as render_comparison:
            result = interpret_file(program)
        self.assertIsNone(result)
        render_comparison.assert_called_once()
        entries = render_comparison.call_args.args[0]
        self.assertEqual([label for label, _ in entries], ["a", "b"])

    def test_render_returns_output_path_in_headless_mode(self):
        result = interpret_statement("render(d20)")
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith(".png"))
        self.assertTrue(os.path.exists(result))

    def test_render_comparison_requires_labels(self):
        with self.assertRaisesRegex(Exception, "render comparison labels must be strings"):
            interpret_statement("render(d20, d20)")

    def test_render_comparison_requires_two_expressions(self):
        with self.assertRaisesRegex(Exception, "at least two expressions"):
            interpret_statement('render(d20, "only")')

    def test_render_comparison_requires_label_for_every_expression(self):
        with self.assertRaisesRegex(Exception, "require a label for every expression"):
            interpret_statement('render(d20, "a", d20)')


class ViewerSpecTest(unittest.TestCase):
    def test_unswept_distribution_uses_bar_spec(self):
        spec = viewer.build_render_spec(interpret_statement("d20"))
        self.assertEqual(spec.kind, "bar")

    def test_one_sweep_scalar_uses_line_spec(self):
        spec = viewer.build_render_spec(interpret_statement("~(d20 >= [AC:10:12] -> 5 | 0)"))
        self.assertEqual(spec.kind, "line")
        self.assertEqual(spec.x_label, "AC")

    def test_one_sweep_distribution_uses_heatmap_spec(self):
        spec = viewer.build_render_spec(interpret_statement("d20 >= [AC:10:12]"))
        self.assertEqual(spec.kind, "heatmap_distribution")
        self.assertEqual(spec.x_label, "AC")

    def test_two_sweep_scalar_uses_heatmap_spec(self):
        spec = viewer.build_render_spec(interpret_statement("~([AC:10:11] + [BONUS:1:2])"))
        self.assertEqual(spec.kind, "heatmap_scalar")
        self.assertEqual(spec.x_label, "BONUS")
        self.assertEqual(spec.y_label, "AC")

    def test_comparison_of_unswept_distributions_uses_overlay_spec(self):
        spec, _ = viewer.build_comparison_spec([
            ("a", interpret_statement("d20")),
            ("b", interpret_statement("d20 + 1")),
        ])
        self.assertEqual(spec.kind, "compare_bar")

    def test_comparison_of_scalar_sweeps_uses_line_overlay_spec(self):
        spec, _ = viewer.build_comparison_spec([
            ("a", interpret_statement("~(d20 >= [AC:10:12] -> 5 | 0)")),
            ("b", interpret_statement("~(d20 >= [AC:10:12] -> 7 | 0)")),
        ])
        self.assertEqual(spec.kind, "compare_line")
        self.assertEqual(spec.x_label, "AC")

    def test_comparison_rejects_incompatible_sweep_values(self):
        with self.assertRaisesRegex(Exception, "matching sweep axis values"):
            viewer.build_comparison_spec([
                ("a", interpret_statement("~(d20 >= [AC:10:12] -> 5 | 0)")),
                ("b", interpret_statement("~(d20 >= [AC:11:13] -> 7 | 0)")),
            ])

    def test_comparison_rejects_heatmap_shapes(self):
        with self.assertRaisesRegex(Exception, "only supports unswept distributions or one-sweep scalar results"):
            viewer.build_comparison_spec([
                ("a", interpret_statement("d20 >= [AC:10:12]")),
                ("b", interpret_statement("d20 >= [AC:10:12]")),
            ])

    def test_render_rejects_unsupported_shape(self):
        with self.assertRaisesRegex(Exception, "does not support this result shape yet"):
            viewer.build_render_spec(interpret_statement("~([AC:10:11] + [BONUS:1:2] + [LEVEL:1:2])"))


class ViewerBackendTest(unittest.TestCase):
    def test_qtagg_is_treated_as_interactive_backend(self):
        figure = viewer.plt.figure()
        try:
            with mock.patch.object(viewer.plt, "get_backend", return_value="QtAgg"):
                with mock.patch.object(viewer.plt, "show") as show:
                    output_path = viewer._show_figure(figure)
            self.assertIsNone(output_path)
            show.assert_called_once()
        finally:
            viewer.plt.close(figure)


class CliRenderTest(unittest.TestCase):
    def test_execute_plot_flag_uses_render_result(self):
        mock_outcome = viewer.RenderOutcome(viewer.RenderSpec("bar", "Outcome", "Probability"), "/tmp/example.png")
        with mock.patch.object(viewer, "render_result", return_value=mock_outcome) as render_result:
            with mock.patch.object(sys, "argv", ["dice.py", "-p", "execute", "d20"]):
                with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
                    exit_code = dice.main()
        self.assertEqual(exit_code, 0)
        render_result.assert_called_once()
        self.assertIn("/tmp/example.png", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
