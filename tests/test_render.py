import os
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
import diceengine
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

    def test_render_single_expression_accepts_axis_label_and_title(self):
        mock_outcome = viewer.RenderOutcome(viewer.RenderSpec("bar", "Outcome", "Probability"), None)
        with mock.patch.object(viewer, "render_result", return_value=mock_outcome) as render_result:
            result = interpret_statement('render(d20, "Roll", "Hit chances")')
        self.assertIsNone(result)
        render_result.assert_called_once()
        self.assertEqual(render_result.call_args.kwargs["x_label"], "Roll")
        self.assertEqual(render_result.call_args.kwargs["title"], "Hit chances")

    def test_render_comparison_accepts_axis_label_and_trailing_title(self):
        program = 'a = d20\nb = d20 + 1\nrender(a, "a", b, "b", "Roll", "Comparison")'
        mock_outcome = viewer.RenderOutcome(viewer.RenderSpec("compare_bar", "Outcome", "Probability", ("a", "b")), None)
        with mock.patch.object(viewer, "render_comparison", return_value=mock_outcome) as render_comparison:
            result = interpret_file(program)
        self.assertIsNone(result)
        render_comparison.assert_called_once()
        self.assertEqual(render_comparison.call_args.kwargs["x_label"], "Roll")
        self.assertEqual(render_comparison.call_args.kwargs["title"], "Comparison")

    def test_render_returns_output_path_in_headless_mode(self):
        result = interpret_statement("render(d20)")
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith(".png"))
        self.assertTrue(os.path.exists(result))

    def test_render_comparison_requires_labels(self):
        with self.assertRaisesRegex(Exception, "require an axis label before the title"):
            interpret_statement("render(d20, d20)")

    def test_render_comparison_requires_label_for_every_expression(self):
        with self.assertRaisesRegex(Exception, "require a label for every expression"):
            interpret_statement('render(d20, "a", d20)')

    def test_render_lazily_loads_viewer_once(self):
        diceengine._viewer_module = None
        mock_viewer = mock.Mock()
        mock_viewer.render_result.side_effect = [
            viewer.RenderOutcome(viewer.RenderSpec("bar", "Outcome", "Probability"), "first"),
            viewer.RenderOutcome(viewer.RenderSpec("bar", "Outcome", "Probability"), "second"),
        ]
        try:
            with mock.patch("diceengine.importlib.import_module", return_value=mock_viewer) as import_module:
                self.assertEqual(diceengine.render("one"), "first")
                self.assertEqual(diceengine.render("two"), "second")
            import_module.assert_called_once_with("viewer")
            self.assertEqual(mock_viewer.render_result.call_count, 2)
        finally:
            diceengine._viewer_module = None

    def test_dice_session_uses_non_blocking_render_config(self):
        diceengine._viewer_module = None
        mock_viewer = mock.Mock()
        mock_viewer.render_result.return_value = viewer.RenderOutcome(
            viewer.RenderSpec("bar", "Outcome", "Probability"),
            None,
        )
        session = dice.dice_interpreter()
        try:
            with mock.patch("diceengine.importlib.import_module", return_value=mock_viewer):
                session.interpreter.executor.render("one")
            mock_viewer.render_result.assert_called_once_with(
                "one",
                render_config=diceengine.RenderConfig(interactive_blocking=False),
            )
        finally:
            diceengine._viewer_module = None


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

    def test_comparison_of_bernoulli_sweeps_uses_probability_overlay_spec(self):
        spec, _ = viewer.build_comparison_spec([
            ("a", interpret_statement("d20 >= [AC:10:12]")),
            ("b", interpret_statement("d20 >= [AC:10:12]")),
        ])
        self.assertEqual(spec.kind, "compare_probability_line")
        self.assertEqual(spec.x_label, "AC")

    def test_comparison_of_distribution_sweeps_allows_unnamed_axes(self):
        spec, _ = viewer.build_comparison_spec([
            ("a", interpret_statement("d2 + [10:12]")),
            ("b", interpret_statement("d2 + [10:12]")),
        ])
        self.assertEqual(spec.kind, "compare_distribution_line")
        self.assertEqual(spec.x_label, "Sweep 1")

    def test_comparison_rejects_incompatible_sweep_values(self):
        with self.assertRaisesRegex(Exception, "matching sweep axis values"):
            viewer.build_comparison_spec([
                ("a", interpret_statement("~(d20 >= [AC:10:12] -> 5 | 0)")),
                ("b", interpret_statement("~(d20 >= [AC:11:13] -> 7 | 0)")),
            ])

    def test_comparison_rejects_two_sweep_distribution_shapes(self):
        with self.assertRaisesRegex(Exception, "one-sweep distribution results"):
            viewer.build_comparison_spec([
                ("a", interpret_statement("d20 + [AC:10:11] + [BONUS:1:2]")),
                ("b", interpret_statement("d20 + [AC:10:11] + [BONUS:1:2]")),
            ])

    def test_render_rejects_unsupported_shape(self):
        with self.assertRaisesRegex(Exception, "does not support this result shape yet"):
            viewer.build_render_spec(interpret_statement("~([AC:10:11] + [BONUS:1:2] + [LEVEL:1:2])"))


class ViewerBackendTest(unittest.TestCase):
    def test_probability_bar_scales_to_percent_by_default(self):
        result = interpret_statement("d2")
        figure, ax = viewer.plt.subplots()
        try:
            viewer._plot_unswept_bar(ax, result)
            heights = [patch.get_height() for patch in ax.patches]
            self.assertEqual(heights, [50.0, 50.0])
        finally:
            viewer.plt.close(figure)

    def test_probability_bar_can_use_raw_probabilities(self):
        result = interpret_statement("d2")
        figure, ax = viewer.plt.subplots()
        try:
            viewer._plot_unswept_bar(
                ax,
                result,
                render_config=diceengine.RenderConfig(probability_mode="raw"),
            )
            heights = [patch.get_height() for patch in ax.patches]
            self.assertEqual(heights, [0.5, 0.5])
        finally:
            viewer.plt.close(figure)

    def test_titled_figure_sets_window_title(self):
        figure = viewer.plt.figure()
        original_manager = getattr(figure.canvas, "manager", None)
        mock_manager = mock.Mock()
        figure.canvas.manager = mock_manager
        try:
            viewer._set_window_title(figure, "Hit chances")
            mock_manager.set_window_title.assert_called_once_with("Hit chances")
        finally:
            figure.canvas.manager = original_manager
            viewer.plt.close(figure)

    def test_multiple_figures_still_set_window_title(self):
        figure = viewer.plt.figure()
        original_manager = getattr(figure.canvas, "manager", None)
        mock_manager = mock.Mock()
        figure.canvas.manager = mock_manager
        try:
            with mock.patch.object(viewer.plt, "get_fignums", return_value=[1, 2]):
                viewer._set_window_title(figure, "Hit chances")
            mock_manager.set_window_title.assert_called_once_with("Hit chances")
        finally:
            figure.canvas.manager = original_manager
            viewer.plt.close(figure)

    def test_qtagg_is_treated_as_interactive_backend(self):
        figure = viewer.plt.figure()
        try:
            with mock.patch.object(viewer.plt, "get_backend", return_value="QtAgg"):
                with mock.patch.object(viewer.plt, "show") as show:
                    with mock.patch.object(viewer.plt, "close") as close:
                        output_path = viewer._show_figure(figure)
            self.assertIsNone(output_path)
            show.assert_called_once()
            close.assert_called_once_with(figure)
        finally:
            viewer.plt.close(figure)

    def test_qtagg_can_render_non_blocking(self):
        figure = viewer.plt.figure()
        try:
            with mock.patch.object(viewer.plt, "get_backend", return_value="QtAgg"):
                with mock.patch.object(viewer.plt, "show") as show:
                    with mock.patch.object(viewer.plt, "pause") as pause:
                        with mock.patch.object(viewer.plt, "close") as close:
                            output_path = viewer._show_figure(
                                figure,
                                render_config=diceengine.RenderConfig(
                                    interactive_blocking=False
                                ),
                            )
            self.assertIsNone(output_path)
            show.assert_called_once_with(block=False)
            pause.assert_called_once_with(0.001)
            close.assert_not_called()
        finally:
            viewer.plt.close(figure)

    def test_wait_for_rendered_figures_blocks_until_close_in_deferred_mode(self):
        figure = viewer.plt.figure()
        try:
            with mock.patch.object(viewer.plt, "get_backend", return_value="QtAgg"):
                with mock.patch.object(viewer.plt, "get_fignums", return_value=[figure.number]):
                    with mock.patch.object(viewer.plt, "show") as show:
                        viewer.wait_for_rendered_figures(
                            render_config=diceengine.RenderConfig.from_mode("deferred")
                        )
            show.assert_called_once_with()
        finally:
            viewer.plt.close(figure)

    def test_render_bar_uses_percent_probability_axis_label_by_default(self):
        result = interpret_statement("d2")
        figure, ax = viewer.plt.subplots()
        try:
            with mock.patch.object(viewer.plt, "subplots", return_value=(figure, ax)):
                with mock.patch.object(viewer, "_show_figure", return_value=None):
                    viewer.render_result(result)
            self.assertEqual(ax.get_ylabel(), "Probability (%)")
        finally:
            viewer.plt.close(figure)

    def test_render_bar_can_use_raw_probability_axis_label(self):
        result = interpret_statement("d2")
        figure, ax = viewer.plt.subplots()
        try:
            with mock.patch.object(viewer.plt, "subplots", return_value=(figure, ax)):
                with mock.patch.object(viewer, "_show_figure", return_value=None):
                    viewer.render_result(
                        result,
                        render_config=diceengine.RenderConfig(probability_mode="raw"),
                    )
            self.assertEqual(ax.get_ylabel(), "Probability")
        finally:
            viewer.plt.close(figure)


if __name__ == "__main__":
    unittest.main()
