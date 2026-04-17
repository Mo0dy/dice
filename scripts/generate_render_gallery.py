#!/usr/bin/env python3

"""Generate curated and sample renderer gallery images."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file
from tests.render_gallery_cases import CASE_NAMES, render_case


SAMPLE_FILES = (
    ROOT / "samples" / "dnd" / "ability_scores_4d6h3.dice",
    ROOT / "samples" / "dnd" / "agonizing_eldritch_blast_vs_ac.dice",
    ROOT / "samples" / "dnd" / "combat_profiles.dice",
    ROOT / "samples" / "dnd" / "eldritch_blast_debug.dice",
    ROOT / "samples" / "dnd" / "strategy_heatmap.dice",
)
RENDER_CALL_RE = re.compile(r"render\s*\([^)]*\)")


def _replace_render_call(program_text, output_path):
    matches = list(RENDER_CALL_RE.finditer(program_text))
    if len(matches) != 1:
        raise ValueError("Expected exactly one render(...) call, found {}".format(len(matches)))
    replacement = 'render(path="{}")'.format(output_path.as_posix().replace('"', '\\"'))
    match = matches[0]
    return program_text[:match.start()] + replacement + program_text[match.end():]


def _render_sample(sample_path, output_path):
    program_text = sample_path.read_text(encoding="utf-8")
    instrumented_program = _replace_render_call(program_text, output_path)
    interpret_file(
        instrumented_program,
        current_dir=str(sample_path.parent),
        source_name=str(sample_path),
    )
    return output_path


def _render_curated(output_dir):
    curated_dir = output_dir / "curated"
    curated_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []
    for case_name in CASE_NAMES:
        output_path = curated_dir / "{}.png".format(case_name)
        render_case(case_name, output_path)
        rendered_paths.append(output_path)
    return rendered_paths


def _render_samples(output_dir):
    sample_dir = output_dir / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []
    for sample_path in SAMPLE_FILES:
        output_path = sample_dir / "{}.png".format(sample_path.stem)
        _render_sample(sample_path, output_path)
        rendered_paths.append(output_path)
    return rendered_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=str(Path(tempfile.gettempdir()) / "dice-render-gallery"),
        help="Directory where gallery PNGs will be written.",
    )
    parser.add_argument(
        "--section",
        choices=("all", "curated", "samples"),
        default="all",
        help="Which gallery set to generate.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered_paths = []
    if args.section in {"all", "curated"}:
        rendered_paths.extend(_render_curated(output_dir))
    if args.section in {"all", "samples"}:
        rendered_paths.extend(_render_samples(output_dir))

    for rendered_path in rendered_paths:
        print(rendered_path)


if __name__ == "__main__":
    main()
