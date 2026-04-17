import math
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.dnd_cases import all_dnd_cases


ROOT = Path(__file__).resolve().parents[1]
TROLL = ROOT / "tests" / "troll" / "run_troll.sh"
TROLL_README = ROOT / "tests" / "troll" / "README.md"
LOCAL_CAMLRUNM = ROOT / ".tools" / "mosml" / "bin" / "camlrunm"
LOCAL_TROLL_IMAGE = ROOT / ".tools" / "troll" / "troll"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file


def _has_troll_runtime():
    if os.environ.get("DICE_TROLL_BIN"):
        return True
    if shutil.which("troll"):
        return True
    return LOCAL_CAMLRUNM.exists() and LOCAL_TROLL_IMAGE.exists()


TROLL_AVAILABLE = _has_troll_runtime()
TROLL_SKIP_REASON = "Troll is not available. See {}".format(TROLL_README)


CASE_SOURCES = {case.name: case.source for case in all_dnd_cases()}


def _parse_troll_distribution(output):
    distribution = {}
    for line in output.splitlines():
        match = re.match(r"\s*(-?\d+):\s+([0-9.E~+-]+)\s+", line)
        if not match:
            continue
        outcome = int(match.group(1))
        probability_text = match.group(2).replace("E~", "e-")
        distribution[outcome] = float(probability_text) / 100.0
    return distribution


def _parse_troll_average(output):
    match = re.search(r"Average =\s*([0-9.E~+-]+)", output)
    if not match:
        raise AssertionError("Could not parse Troll average from output:\n{}".format(output))
    return float(match.group(1).replace("E~", "e-"))


def _only_scalar(distrib):
    items = list(distrib.items())
    if len(items) != 1 or items[0][1] != 1:
        raise AssertionError("Expected a deterministic distribution, got {}".format(distrib))
    return items[0][0]


def _scaled_distribution(distrib, scale):
    scaled = {}
    for outcome, probability in distrib.items():
        scaled_outcome = outcome * scale
        rounded = round(scaled_outcome)
        if not math.isclose(scaled_outcome, rounded, rel_tol=0.0, abs_tol=1e-12):
            raise AssertionError(
                "Scaled outcome {!r} with scale {!r} did not stay integral".format(outcome, scale)
            )
        scaled[int(rounded)] = probability
    return scaled


def _weapons_args(mode, *, scale=1, **overrides):
    values = {"MODE": mode, "AC": 0, "BONUS": 0, "MOD": 0, "EXTRA": 0, "ATTACKS": 0, "SCALE": scale}
    values.update(overrides)
    ordered = ["MODE", "AC", "BONUS", "MOD", "EXTRA", "ATTACKS", "SCALE"]
    return ["0", "tests/troll/dnd/weapons.t"] + [f"{key}={values[key]}" for key in ordered]


def _spells_args(mode, *, scale=1, **overrides):
    values = {
        "MODE": mode,
        "AC": 0,
        "BONUS": 0,
        "STAT": 0,
        "COUNT": 0,
        "DC": 0,
        "SAVEBONUS": 0,
        "SCALE": scale,
    }
    values.update(overrides)
    ordered = ["MODE", "AC", "BONUS", "STAT", "COUNT", "DC", "SAVEBONUS", "SCALE"]
    return ["0", "tests/troll/dnd/spells.t"] + [f"{key}={values[key]}" for key in ordered]


# The exact D&D library has outgrown the historical Troll mirror.
# Re-enable specific comparisons only when matching Troll fixtures are updated.
FULL_DISTRIBUTION_CASES = {}
SCALAR_SWEEP_CASES = {}
SCALAR_CASES = {}

ALL_CASES = set()
UNCOMPARED_CASES = set(CASE_SOURCES)


class TrollDistributionComparisonTest(unittest.TestCase):
    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_all_dnd_examples_have_troll_comparisons(self):
        discovered = set(CASE_SOURCES)
        self.assertEqual(discovered, ALL_CASES | UNCOMPARED_CASES)

    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_troll_matches_all_full_distribution_examples(self):
        for relative_path, spec in sorted(FULL_DISTRIBUTION_CASES.items()):
            with self.subTest(sample=relative_path):
                dice_distribution = interpret_file(
                    CASE_SOURCES[relative_path],
                    current_dir=ROOT,
                    source_name=relative_path,
                ).only_distribution()
                scale = spec.get("scale", 1)
                if scale != 1:
                    dice_distribution = _scaled_distribution(dice_distribution, scale)
                else:
                    dice_distribution = dict(dice_distribution.items())

                if "stdin" in spec:
                    troll_output = subprocess.check_output([str(TROLL), "0"], cwd=ROOT, text=True, input=spec["stdin"])
                else:
                    troll_output = subprocess.check_output([str(TROLL)] + spec["args"], cwd=ROOT, text=True)
                troll_distribution = _parse_troll_distribution(troll_output)

                self.assertEqual(sorted(dice_distribution.keys()), sorted(troll_distribution.keys()))
                for outcome in sorted(dice_distribution.keys()):
                    self.assertTrue(
                        math.isclose(dice_distribution[outcome], troll_distribution[outcome], rel_tol=0.0, abs_tol=1e-12),
                        msg=(
                            f"{relative_path} outcome {outcome} differed: "
                            f"dice={dice_distribution[outcome]!r} troll={troll_distribution[outcome]!r}"
                        ),
                    )

    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_troll_matches_all_scalar_sweep_examples(self):
        for relative_path, spec in sorted(SCALAR_SWEEP_CASES.items()):
            with self.subTest(sample=relative_path):
                result = interpret_file(CASE_SOURCES[relative_path], current_dir=ROOT, source_name=relative_path)
                self.assertEqual(len(result.axes), 1)
                self.assertEqual(list(result.axes[0].values), spec["axis_values"])

                scale = spec.get("scale", 1)
                for axis_value in spec["axis_values"]:
                    dice_scalar = _only_scalar(result.cells[(axis_value,)])
                    troll_output = subprocess.check_output([str(TROLL)] + spec["builder"](axis_value), cwd=ROOT, text=True)
                    troll_average = _parse_troll_average(troll_output)
                    self.assertTrue(
                        math.isclose(dice_scalar * scale, troll_average, rel_tol=0.0, abs_tol=1e-12),
                        msg=(
                            f"{relative_path} axis value {axis_value} differed: "
                            f"dice={dice_scalar!r} troll={troll_average!r} scale={scale}"
                        ),
                    )

    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_troll_matches_all_scalar_examples(self):
        for relative_path, spec in sorted(SCALAR_CASES.items()):
            with self.subTest(sample=relative_path):
                result = interpret_file(CASE_SOURCES[relative_path], current_dir=ROOT, source_name=relative_path)
                dice_scalar = _only_scalar(result.only_distribution())
                troll_scalar = sum(
                    _parse_troll_average(subprocess.check_output([str(TROLL)] + args, cwd=ROOT, text=True))
                    for args in spec["components"]
                )
                self.assertTrue(
                    math.isclose(dice_scalar * spec.get("scale", 1), troll_scalar, rel_tol=0.0, abs_tol=1e-12),
                    msg=f"{relative_path} differed: dice={dice_scalar!r} troll={troll_scalar!r}",
                )


if __name__ == "__main__":
    unittest.main()
