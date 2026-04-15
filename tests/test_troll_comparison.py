import os
import math
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "dnd"
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


def _sample_files():
    roots = [SAMPLES / "at_table", SAMPLES / "analysis"]
    return sorted(path for root in roots for path in root.rglob("*.dice"))


def _relative_sample(path):
    return str(path.relative_to(ROOT))


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


def _weapons_args(mode, **overrides):
    values = {"MODE": mode, "AC": 0, "BONUS": 0, "MOD": 0, "EXTRA": 0, "ATTACKS": 0}
    values.update(overrides)
    ordered = ["MODE", "AC", "BONUS", "MOD", "EXTRA", "ATTACKS"]
    return ["0", "tests/troll/dnd/weapons.t"] + [f"{key}={values[key]}" for key in ordered]


def _spells_args(mode, **overrides):
    values = {"MODE": mode, "AC": 0, "BONUS": 0, "STAT": 0, "COUNT": 0, "DC": 0, "SAVEBONUS": 0}
    values.update(overrides)
    ordered = ["MODE", "AC", "BONUS", "STAT", "COUNT", "DC", "SAVEBONUS"]
    return ["0", "tests/troll/dnd/spells.t"] + [f"{key}={values[key]}" for key in ordered]


FULL_DISTRIBUTION_CASES = {
    "samples/dnd/at_table/bless_longsword_attack.dice": {"args": _weapons_args(5, AC=16, BONUS=7, MOD=4)},
    "samples/dnd/at_table/crit_longsword_attack.dice": {"args": _weapons_args(6, AC=16, BONUS=7, MOD=4)},
    "samples/dnd/at_table/eldritch_blast.dice": {"args": _spells_args(1, AC=15, BONUS=7, STAT=4)},
    "samples/dnd/at_table/eldritch_blast_three_beams.dice": {"args": _spells_args(2, AC=15, BONUS=7, STAT=4, COUNT=3)},
    "samples/dnd/at_table/fighter_extra_attack.dice": {"args": _weapons_args(9, AC=16, BONUS=7, MOD=4, ATTACKS=2)},
    "samples/dnd/at_table/fireball_save.dice": {"args": _spells_args(5, DC=15, SAVEBONUS=2)},
    "samples/dnd/at_table/great_weapon_master_attack.dice": {"args": _weapons_args(2, AC=17, BONUS=8, MOD=4)},
    "samples/dnd/at_table/guiding_bolt.dice": {"args": _spells_args(3, AC=15, BONUS=7)},
    "samples/dnd/at_table/inflict_wounds.dice": {"args": _spells_args(4, AC=15, BONUS=7)},
    "samples/dnd/at_table/longsword_attack.dice": {"args": _weapons_args(1, AC=16, BONUS=7, MOD=4)},
    "samples/dnd/at_table/magic_missile.dice": {"args": _spells_args(7, COUNT=3)},
    "samples/dnd/at_table/paladin_smite_attack.dice": {"args": _weapons_args(8, AC=17, BONUS=8, MOD=4, EXTRA=3)},
    "samples/dnd/at_table/rogue_sneak_attack.dice": {"args": _weapons_args(4, AC=16, BONUS=7, MOD=4, EXTRA=3)},
    "samples/dnd/at_table/sacred_flame.dice": {"args": _spells_args(6, DC=15, SAVEBONUS=2)},
    "samples/dnd/analysis/stat_roll_4d6h3.dice": {"stdin": "sum largest 3 4d6\n"},
}


SCALAR_SWEEP_CASES = {
    "samples/dnd/analysis/bless_longsword_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(5, AC=value, BONUS=7, MOD=4),
    },
    "samples/dnd/analysis/crit_longsword_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(6, AC=value, BONUS=7, MOD=4),
    },
    "samples/dnd/analysis/eldritch_blast_three_beams_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _spells_args(2, AC=value, BONUS=7, STAT=4, COUNT=3),
    },
    "samples/dnd/analysis/eldritch_blast_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _spells_args(1, AC=value, BONUS=7, STAT=4),
    },
    "samples/dnd/analysis/fighter_longsword_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(1, AC=value, BONUS=7, MOD=4),
    },
    "samples/dnd/analysis/fighter_two_attacks_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(9, AC=value, BONUS=7, MOD=4, ATTACKS=2),
    },
    "samples/dnd/analysis/fireball_vs_save_bonus.dice": {
        "axis_values": list(range(0, 10)),
        "vary_key": "SAVEBONUS",
        "builder": lambda value: _spells_args(5, DC=15, SAVEBONUS=value),
    },
    "samples/dnd/analysis/guiding_bolt_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _spells_args(3, AC=value, BONUS=7),
    },
    "samples/dnd/analysis/gwm_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(2, AC=value, BONUS=8, MOD=4),
    },
    "samples/dnd/analysis/inflict_wounds_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _spells_args(4, AC=value, BONUS=7),
    },
    "samples/dnd/analysis/magic_missile_vs_darts.dice": {
        "axis_values": list(range(1, 7)),
        "vary_key": "COUNT",
        "builder": lambda value: _spells_args(7, COUNT=value),
    },
    "samples/dnd/analysis/paladin_smite_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(8, AC=value, BONUS=8, MOD=4, EXTRA=3),
    },
    "samples/dnd/analysis/reckless_gwm_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(3, AC=value, BONUS=8, MOD=4),
    },
    "samples/dnd/analysis/sacred_flame_vs_save_bonus.dice": {
        "axis_values": list(range(0, 10)),
        "vary_key": "SAVEBONUS",
        "builder": lambda value: _spells_args(6, DC=15, SAVEBONUS=value),
    },
    "samples/dnd/analysis/sharpshooter_vs_ac.dice": {
        "axis_values": list(range(10, 23)),
        "vary_key": "AC",
        "builder": lambda value: _weapons_args(7, AC=value, BONUS=8, MOD=4),
    },
}


SCALAR_CASES = {
    "samples/dnd/analysis/fireball_party_total.dice": {
        "components": [
            _spells_args(5, DC=15, SAVEBONUS=0),
            _spells_args(5, DC=15, SAVEBONUS=2),
            _spells_args(5, DC=15, SAVEBONUS=5),
            _spells_args(5, DC=15, SAVEBONUS=7),
        ]
    }
}


ALL_CASES = set(FULL_DISTRIBUTION_CASES) | set(SCALAR_SWEEP_CASES) | set(SCALAR_CASES)


class TrollDistributionComparisonTest(unittest.TestCase):
    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_all_dnd_examples_have_troll_comparisons(self):
        discovered = {_relative_sample(path) for path in _sample_files()}
        self.assertEqual(discovered, ALL_CASES)

    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_troll_matches_all_full_distribution_examples(self):
        for relative_path, spec in sorted(FULL_DISTRIBUTION_CASES.items()):
            with self.subTest(sample=relative_path):
                sample_path = ROOT / relative_path
                dice_distribution = interpret_file(sample_path.read_text(encoding="utf-8"), current_dir=sample_path.parent).only_distribution().distrib
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
                sample_path = ROOT / relative_path
                result = interpret_file(sample_path.read_text(encoding="utf-8"), current_dir=sample_path.parent)
                self.assertEqual(len(result.axes), 1)
                self.assertEqual(list(result.axes[0].values), spec["axis_values"])

                for axis_value in spec["axis_values"]:
                    dice_scalar = _only_scalar(result.cells[(axis_value,)])
                    troll_output = subprocess.check_output([str(TROLL)] + spec["builder"](axis_value), cwd=ROOT, text=True)
                    troll_average = _parse_troll_average(troll_output)
                    self.assertTrue(
                        math.isclose(dice_scalar, troll_average, rel_tol=0.0, abs_tol=1e-12),
                        msg=(
                            f"{relative_path} axis value {axis_value} differed: "
                            f"dice={dice_scalar!r} troll={troll_average!r}"
                        ),
                    )

    @unittest.skipUnless(TROLL_AVAILABLE, TROLL_SKIP_REASON)
    def test_troll_matches_all_scalar_examples(self):
        for relative_path, spec in sorted(SCALAR_CASES.items()):
            with self.subTest(sample=relative_path):
                sample_path = ROOT / relative_path
                result = interpret_file(sample_path.read_text(encoding="utf-8"), current_dir=sample_path.parent)
                dice_scalar = _only_scalar(result.only_distribution())
                troll_scalar = sum(
                    _parse_troll_average(subprocess.check_output([str(TROLL)] + args, cwd=ROOT, text=True))
                    for args in spec["components"]
                )
                self.assertTrue(
                    math.isclose(dice_scalar, troll_scalar, rel_tol=0.0, abs_tol=1e-12),
                    msg=f"{relative_path} differed: dice={dice_scalar!r} troll={troll_scalar!r}",
                )


if __name__ == "__main__":
    unittest.main()
