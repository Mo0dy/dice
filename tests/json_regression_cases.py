from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tests.dnd_cases import all_dnd_cases


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RESULTS = ROOT / "tests" / "expected_results"
SAMPLES = ROOT / "samples"
PYTHON_SAMPLES = ROOT / "samples" / "python_extensions"


@dataclass(frozen=True)
class JsonRegressionCase:
    name: str
    mode: str
    source: str
    current_dir: Path
    snapshot_path: Path


def sample_files() -> list[Path]:
    if not SAMPLES.exists():
        return []
    return sorted(SAMPLES.rglob("*.dice"))


def sample_cases() -> list[JsonRegressionCase]:
    cases = []
    for path in sample_files():
        relative = path.relative_to(ROOT)
        snapshot_path = EXPECTED_RESULTS / "samples" / relative.with_suffix(".json")
        cases.append(
            JsonRegressionCase(
                name=str(relative),
                mode="file",
                source=path.read_text(encoding="utf-8"),
                current_dir=path.parent,
                snapshot_path=snapshot_path,
            )
        )
    return cases


def dnd_cases() -> list[JsonRegressionCase]:
    return [
        JsonRegressionCase(
            name=case.name,
            mode="file",
            source=case.source,
            current_dir=ROOT,
            snapshot_path=case.snapshot_path,
        )
        for case in all_dnd_cases()
    ]


def python_sample_files() -> list[Path]:
    if not PYTHON_SAMPLES.exists():
        return []
    return sorted(PYTHON_SAMPLES.rglob("*.py"))


def python_cases() -> list[JsonRegressionCase]:
    cases = []
    for path in python_sample_files():
        relative = path.relative_to(ROOT)
        snapshot_path = EXPECTED_RESULTS / "samples" / relative.with_suffix(".json")
        cases.append(
            JsonRegressionCase(
                name=str(relative),
                mode="python",
                source=str(path),
                current_dir=path.parent,
                snapshot_path=snapshot_path,
            )
        )
    return cases


def example_cases() -> list[JsonRegressionCase]:
    examples = [
        ("scalar_addition", "1 + 1"),
        ("simple_die", "d20"),
        ("repeat_sum", "repeat_sum(3, d2)"),
        ("repeat_power", "d2 ^ 3"),
        ("branch_else_zero", "d20 >= 11 -> 5 | 0"),
        ("branch_half_damage", "d20 < 14 -> 2d10 |/"),
        ("branch_half_damage_floor", "d20 < 14 -> 2d10 |//"),
        ("advantage", "d+20"),
        ("keep_high", "3d20h1"),
        ("named_sweep", "d20 >= [AC:10:12]"),
        ("match_shared_roll", "split d20 | == 20 -> 10 | + 5 >= 15 -> 5 ||"),
        ("stdlib_import", 'import "std:dnd/weapons"; crit_longsword(16, 7, 4)'),
    ]
    cases = []
    for name, source in examples:
        cases.append(
            JsonRegressionCase(
                name=name,
                mode="statement",
                source=source,
                current_dir=ROOT,
                snapshot_path=EXPECTED_RESULTS / "examples" / f"{name}.json",
            )
        )
    return cases


def all_cases() -> list[JsonRegressionCase]:
    return dnd_cases() + sample_cases() + python_cases() + example_cases()
