import json
import os
import sys
import tempfile
import unittest
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
            raise AssertionError(f"could not load python sample {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            build_result = getattr(module, "build_result", None)
            if not callable(build_result):
                raise AssertionError(f"python sample {path} must define build_result()")
            return build_result()
        finally:
            sys.modules.pop(module_name, None)
    if case.mode == "file":
        return interpret_file(case.source, current_dir=case.current_dir, source_name=case.name)
    return interpret_statement(case.source, current_dir=case.current_dir, source_name=case.name)


class JsonRegressionTest(unittest.TestCase):
    def test_snapshots_match(self):
        cases = all_cases()
        self.assertTrue(cases, "expected at least one JSON regression case")

        for case in cases:
            with self.subTest(case=case.name):
                self.assertTrue(
                    case.snapshot_path.is_file(),
                    f"missing snapshot file {case.snapshot_path}",
                )
                result = evaluate_case(case)
                actual = _normalize_snapshot_payload(_serialize_result(result, probability_mode="raw"))
                expected = _normalize_snapshot_payload(json.loads(case.snapshot_path.read_text(encoding="utf-8")))
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
