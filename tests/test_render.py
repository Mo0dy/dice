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

import viewer
from dice import interpret_file, interpret_statement
from diceengine import ChartSpec, PanelWidthClass, RenderConfig, ReportSpec
from executor import ExactExecutor


class RenderRuntimeTest(unittest.TestCase):
    def test_top_level_chart_auto_appends_and_render_flushes(self):
        result = interpret_statement("r_auto(d20); render()")
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith(".png"))
        self.assertTrue(os.path.exists(result))

    def test_render_accepts_export_kwargs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "chart.png"
            result = interpret_statement(f'r_auto(d20); render(path="{output}", format="png", dpi=120)')
            self.assertEqual(result, str(output))
            self.assertTrue(output.exists())

    def test_render_requires_pending_items(self):
        with self.assertRaisesRegex(Exception, "requires at least one pending report item"):
            interpret_statement("render()")

    def test_duplicate_title_is_rejected(self):
        with self.assertRaisesRegex(Exception, "duplicate r_title"):
            interpret_statement('r_title("A"); r_title("B")')

    def test_duplicate_hero_is_rejected(self):
        with self.assertRaisesRegex(Exception, "duplicate r_hero"):
            interpret_statement('r_hero(r_auto(d20)); r_hero(r_auto(d6))')

    def test_render_resets_state_between_outputs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            first = Path(tempdir) / "first.png"
            second = Path(tempdir) / "second.png"
            program = (
                f'r_auto(d20); render(path="{first}")\n'
                f'r_auto(d6); render(path="{second}")\n'
            )
            result = interpret_file(program)
            self.assertEqual(result, str(second))
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_chart_assignment_does_not_auto_append_until_referenced(self):
        with self.assertRaisesRegex(Exception, "requires at least one pending report item"):
            interpret_statement("chart = r_auto(d20); render()")
        result = interpret_statement("chart = r_auto(d20); chart; render()")
        self.assertTrue(result.endswith(".png"))


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.executor = ExactExecutor()

    def test_r_auto_unswept_distribution_is_narrow(self):
        chart = ChartSpec("auto", interpret_statement("d20"))
        plan = viewer.build_chart_plan(chart)
        self.assertEqual(plan.kind, "unswept_distribution")
        self.assertEqual(plan.width_class, PanelWidthClass.NARROW)

    def test_r_auto_two_axis_scalar_prefers_wide_heatmap(self):
        chart = ChartSpec("auto", interpret_statement("~([AC:10..11] + [BONUS:1..2])"))
        plan = viewer.build_chart_plan(chart)
        self.assertEqual(plan.kind, "scalar_heatmap")
        self.assertEqual(plan.width_class, PanelWidthClass.WIDE)

    def test_r_compare_scalar_sweeps_builds_compare_scalar_plan(self):
        chart = self.executor.r_compare(
            interpret_statement('("A", ~(d20 >= [AC:10..12] -> 5 | 0))'),
            interpret_statement('("B", ~(d20 >= [AC:10..12] -> 7 | 0))'),
            x="AC",
        )
        self.assertIsInstance(chart, ChartSpec)
        plan = viewer.build_chart_plan(chart)
        self.assertEqual(plan.kind, "compare_scalar")

    def test_r_diff_builds_diff_plan(self):
        chart = self.executor.r_diff(
            interpret_statement('("A", ~(d20 >= [AC:10..12] -> 5 | 0))'),
            interpret_statement('("B", ~(d20 >= [AC:10..12] -> 7 | 0))'),
            x="AC",
        )
        plan = viewer.build_chart_plan(chart)
        self.assertEqual(plan.kind, "diff")
        self.assertEqual(plan.width_class, PanelWidthClass.WIDE)

    def test_r_best_builds_strategy_plan(self):
        chart = ChartSpec(
            "best",
            interpret_file(
                'score(plan, ac): split plan as name | name == "plain" -> ac | otherwise -> ac + 1\n'
                'score([PLAN:"plain", "hex"], [AC:10..12])'
            ),
        )
        plan = viewer.build_chart_plan(chart)
        self.assertEqual(plan.kind, "best_strategy")
        self.assertEqual(plan.width_class, PanelWidthClass.WIDE)

    def test_report_plan_packs_narrow_panels_two_up_and_wide_panels_full_row(self):
        pending = ReportSpec()
        from diceengine import report_append_chart

        pending = report_append_chart(pending, self.executor.r_auto(interpret_statement("d20")))
        pending = report_append_chart(pending, self.executor.r_auto(interpret_statement("d6")))
        pending = report_append_chart(
            pending,
            self.executor.r_wide(self.executor.r_auto(interpret_statement("~([AC:10..11] + [BONUS:1..2])"))),
        )
        plan = viewer.build_report_plan(pending)
        self.assertEqual(len(plan.rows), 2)
        self.assertEqual(len(plan.rows[0]), 2)
        self.assertEqual(plan.rows[1][0].width_class, PanelWidthClass.WIDE)


class FigureStructureTest(unittest.TestCase):
    def test_compare_scalar_uses_direct_labels_without_legend_for_small_series_count(self):
        plan = viewer.build_chart_plan(
            ExactExecutor().r_compare(
                interpret_statement('("A", ~(d20 >= [AC:10..12] -> 5 | 0))'),
                interpret_statement('("B", ~(d20 >= [AC:10..12] -> 7 | 0))'),
                x="AC",
            )
        )
        figure, ax = viewer.plt.subplots()
        try:
            viewer.render_chart_on_axes(figure, ax, plan, RenderConfig())
            self.assertIsNone(ax.get_legend())
            self.assertGreaterEqual(len(ax.texts), 2)
        finally:
            viewer.plt.close(figure)

    def test_distribution_sweep_adds_colorbar(self):
        plan = viewer.build_chart_plan(ChartSpec("auto", interpret_statement("d20 >= [AC:10..12]")))
        figure, ax = viewer.plt.subplots()
        try:
            viewer.render_chart_on_axes(figure, ax, plan, RenderConfig())
            self.assertEqual(len(figure.axes), 2)
        finally:
            viewer.plt.close(figure)

    def test_render_report_outputs_png(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "report.png"
            program = (
                'r_title("Report")\n'
                'r_compare(("A", ~(d20 >= [AC:10..12] -> 5 | 0)), ("B", ~(d20 >= [AC:10..12] -> 7 | 0)), x="AC")\n'
                f'render(path="{output}")\n'
            )
            result = interpret_file(program)
            self.assertEqual(result, str(output))
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
