#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file, interpret_statement, _serialize_result
from diceengine import SweepValues
from tests.json_regression_cases import all_cases


def _normalize_snapshot_payload(payload):
    if payload.get("type") == "string":
        value = payload.get("value")
        if isinstance(value, str) and value.startswith("/tmp/dice-render-") and value.endswith(".png"):
            normalized = dict(payload)
            normalized["value"] = "__RENDER_OUTPUT__"
            return normalized
    return payload


def evaluate_case(case):
    SweepValues.counter = 0
    if case.mode == "python":
        path = Path(case.source)
        module_name = "_dice_sample_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"could not load python sample {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            build_result = getattr(module, "build_result", None)
            if not callable(build_result):
                raise SystemExit(f"python sample {path} must define build_result()")
            return build_result()
        finally:
            sys.modules.pop(module_name, None)
    if case.mode == "file":
        return interpret_file(case.source, current_dir=case.current_dir, source_name=case.name)
    return interpret_statement(case.source, current_dir=case.current_dir, source_name=case.name)


def main():
    for case in all_cases():
        case.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        result = evaluate_case(case)
        serialized = _normalize_snapshot_payload(_serialize_result(result, probability_mode="raw"))
        case.snapshot_path.write_text(
            json.dumps(serialized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(case.snapshot_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
