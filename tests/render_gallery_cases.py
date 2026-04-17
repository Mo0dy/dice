import os
import sys
import tempfile
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
from diceengine import RenderConfig, ReportSpec, report_add_note, report_append_chart, report_set_title
from executor import ExactExecutor


CASE_NAMES = (
    "auto_d20",
    "compare_scalar",
    "best_strategy",
    "simple_report",
)
EXPECTED_DIR = ROOT / "tests" / "expected_results" / "render_gallery"


def _compare_chart():
    executor = ExactExecutor()
    return executor.r_compare(
        interpret_statement('("Plain", ~(d20 >= [AC:10..18] -> 5 | 0))'),
        interpret_statement('("Boosted", ~(d20 >= [AC:10..18] -> 7 | 0))'),
        x="Armor class",
        title="Expected damage by armor class",
    )


def _best_chart():
    result = interpret_file(
        'score(plan, ac): split plan as name | name == "plain" -> ac | name == "boosted" -> ac + 2 | otherwise -> ac + 1\n'
        'score([PLAN:"plain", "boosted", "steady"], [AC:10..18])'
    )
    return ExactExecutor().r_best(result, title="Best strategy by AC")


def _simple_report():
    report = ReportSpec()
    report = report_set_title(report, "Renderer report")
    report = report_append_chart(report, ExactExecutor().r_auto(interpret_statement("d20"), x="Outcome", title="d20 PMF"))
    report = report_append_chart(report, _compare_chart())
    report = report_add_note(report, "Curated render baseline for manual review.")
    return report


def render_case(name, output_path):
    config = RenderConfig(probability_mode="percent")
    if name == "auto_d20":
        return viewer.render_chart(
            ExactExecutor().r_auto(interpret_statement("d20"), x="Outcome", title="d20 PMF"),
            render_config=config,
            path=str(output_path),
            dpi=160,
        ).output_path
    if name == "compare_scalar":
        return viewer.render_chart(
            _compare_chart(),
            render_config=config,
            path=str(output_path),
            dpi=160,
        ).output_path
    if name == "best_strategy":
        return viewer.render_chart(
            _best_chart(),
            render_config=config,
            path=str(output_path),
            dpi=160,
        ).output_path
    if name == "simple_report":
        return viewer.render_report(
            _simple_report(),
            render_config=config,
            path=str(output_path),
            dpi=160,
        ).output_path
    raise ValueError(name)


def expected_case_path(name):
    return EXPECTED_DIR / "{}.png".format(name)
