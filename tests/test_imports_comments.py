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
from diceengine import Distributions, TRUE, FALSE


def only_distribution(result):
    assert isinstance(result, Distributions)
    assert result.is_unswept()
    return result.only_distribution()


class ImportAndCommentTest(unittest.TestCase):
    def test_line_comment_can_stand_alone(self):
        result = only_distribution(interpret_file("// note\n1 + 1"))
        self.assertEqual(result[2], 1)

    def test_trailing_comment_does_not_affect_statement(self):
        result = only_distribution(interpret_file("x = 2 // set x\nx + 1"))
        self.assertEqual(result[3], 1)

    def test_import_loads_relative_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "combat.dice").write_text("hit(ac) = d20 >= ac\n", encoding="utf-8")
            result = interpret_file(
                'import "combat.dice"\nhit(11)',
                current_dir=root,
            )
            distribution = only_distribution(result)
            self.assertAlmostEqual(distribution[TRUE], 0.5)
            self.assertAlmostEqual(distribution[FALSE], 0.5)

    def test_import_loads_absolute_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            helper = root / "combat.dice"
            helper.write_text("hit(ac) = d20 >= ac\n", encoding="utf-8")
            result = interpret_file(
                f'import "{helper}"\nhit(11)',
                current_dir=root / "somewhere" / "else",
            )
            distribution = only_distribution(result)
            self.assertAlmostEqual(distribution[TRUE], 0.5)
            self.assertAlmostEqual(distribution[FALSE], 0.5)

    def test_nested_import_resolves_from_importing_file_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "lib").mkdir()
            (root / "lib" / "damage.dice").write_text("damage(ac) = hit(ac) -> 5 | 0\n", encoding="utf-8")
            (root / "combat.dice").write_text('import "lib/damage.dice"\nhit(ac) = d20 >= ac\n', encoding="utf-8")
            result = interpret_file(
                'import "combat.dice"\ndamage(11)',
                current_dir=root,
            )
            distribution = only_distribution(result)
            self.assertAlmostEqual(distribution[5], 0.5)
            self.assertAlmostEqual(distribution[0], 0.5)

    def test_import_is_only_processed_once(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "helpers.dice").write_text("bonus = 2\nadd_bonus(x) = x + bonus\n", encoding="utf-8")
            result = interpret_file(
                'import "helpers.dice"\nimport "helpers.dice"\nadd_bonus(3)',
                current_dir=root,
            )
            distribution = only_distribution(result)
            self.assertEqual(distribution[5], 1)

    def test_import_cycle_raises(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "a.dice").write_text('import "b.dice"\n', encoding="utf-8")
            (root / "b.dice").write_text('import "a.dice"\n', encoding="utf-8")
            with self.assertRaisesRegex(Exception, "Import cycle detected"):
                interpret_file('import "a.dice"\n1', current_dir=root)

    def test_imported_files_can_contain_comments(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "shared.dice").write_text("// helper file\nx = 2\n", encoding="utf-8")
            result = only_distribution(
                interpret_file('import "shared.dice"\nx + 1', current_dir=root)
            )
            self.assertEqual(result[3], 1)

    def test_import_loads_stdlib_file(self):
        helper_result = interpret_file(
            'import "std:dnd/weapons.dice"\ncrit_longsword(16, 7, 4)',
            current_dir=Path(tempfile.gettempdir()),
        )
        inline_result = interpret_statement(
            "match d20 as roll | roll == 20 = 2 d 8 + 4 | roll + 7 >= 16 = 1 d 8 + 4 | otherwise = 0"
        )
        self.assertEqual(str(helper_result), str(inline_result))

    def test_missing_import_raises(self):
        with self.assertRaisesRegex(Exception, "Could not import"):
            interpret_statement('import "missing.dice"')

    def test_missing_stdlib_import_raises(self):
        with self.assertRaisesRegex(Exception, "Could not import"):
            interpret_statement('import "std:dnd/missing.dice"')


if __name__ == "__main__":
    unittest.main()
