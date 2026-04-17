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

from matplotlib.testing.compare import compare_images

from tests.render_gallery_cases import CASE_NAMES, expected_case_path, render_case


class RenderGoldenImageTest(unittest.TestCase):
    def test_curated_render_gallery_matches_png_baselines(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = Path(tempdir)
            for case_name in CASE_NAMES:
                with self.subTest(case=case_name):
                    expected_path = expected_case_path(case_name)
                    self.assertTrue(expected_path.exists(), "Missing baseline {}".format(expected_path))
                    actual_path = tempdir_path / "{}.png".format(case_name)
                    render_case(case_name, actual_path)
                    comparison = compare_images(str(expected_path), str(actual_path), tol=2.0)
                    self.assertIsNone(comparison, comparison)


if __name__ == "__main__":
    unittest.main()
