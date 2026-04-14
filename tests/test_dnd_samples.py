import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "dnd"

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file


def sample_files():
    roots = [SAMPLES / "at_table", SAMPLES / "analysis"]
    return sorted(path for root in roots for path in root.rglob("*.dice"))


class DndSampleLibraryTest(unittest.TestCase):
    def test_all_sample_files_execute(self):
        files = sample_files()
        self.assertTrue(files, "expected at least one D&D sample file")

        for path in files:
            with self.subTest(sample=str(path.relative_to(ROOT))):
                result = interpret_file(path.read_text(encoding="utf-8"), current_dir=path.parent)
                self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
