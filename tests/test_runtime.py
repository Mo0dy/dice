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

from dice import interpret_file, interpret_statement


class RuntimeTest(unittest.TestCase):
    def test_multistatement_program_keeps_scope(self):
        result = interpret_file("attack = d20 >= 11\nattack -> 5")
        self.assertAlmostEqual(result[11], 2.5)

    def test_elsediv_matches_explicit_else_branch(self):
        shorthand = interpret_statement("d20 < 14 -> 2d10 |/")
        explicit = interpret_statement("d20 < 14 -> 2d10 | 2d10 / 2")
        self.assertEqual(str(shorthand), str(explicit))


if __name__ == "__main__":
    unittest.main()
