from __future__ import annotations

import importlib.util
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISCUSSION_DIR = ROOT / "examples" / "01_dnd"
RENDER_CALL_RE = re.compile(r"render\s*\([^)]*\)")

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file


def _has_render_call(path: Path) -> bool:
    return "render(" in path.read_text(encoding="utf-8")


def dice_report_files() -> list[Path]:
    return sorted(path for path in DISCUSSION_DIR.glob("*.dice") if _has_render_call(path))


def python_report_files() -> list[Path]:
    return sorted(DISCUSSION_DIR.glob("*_report.py"))


def _replace_render_call(program_text: str, output_path: Path) -> str:
    matches = list(RENDER_CALL_RE.finditer(program_text))
    if len(matches) != 1:
        raise ValueError("expected exactly one render(...) call, found {}".format(len(matches)))
    replacement = 'render(path="{}")'.format(output_path.as_posix().replace('"', '\\"'))
    match = matches[0]
    return program_text[:match.start()] + replacement + program_text[match.end():]


def render_dice_report(sample_path: Path, output_path: Path) -> Path:
    program_text = sample_path.read_text(encoding="utf-8")
    instrumented_program = _replace_render_call(program_text, output_path)
    interpret_file(
        instrumented_program,
        current_dir=sample_path.parent,
        source_name=str(sample_path),
    )
    return output_path


def render_python_report(sample_path: Path, output_dir: Path) -> list[Path]:
    module_name = "_dice_discussion_report_" + "_".join(sample_path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(module_name, sample_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load {}".format(sample_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        build_report = getattr(module, "build_report", None)
        if not callable(build_report):
            raise RuntimeError("{} must define build_report(output_dir)".format(sample_path))
        result = build_report(output_dir)
    finally:
        sys.modules.pop(module_name, None)

    if result is None:
        return []
    if isinstance(result, (str, Path)):
        return [Path(result)]
    return [Path(path) for path in result]


def render_all_discussion_reports(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []
    for sample_path in dice_report_files():
        output_path = output_dir / "{}.png".format(sample_path.stem)
        rendered_paths.append(render_dice_report(sample_path, output_path))
    for sample_path in python_report_files():
        rendered_paths.extend(render_python_report(sample_path, output_dir))
    return rendered_paths
