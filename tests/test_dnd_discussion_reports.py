import tempfile
import unittest
from pathlib import Path

from tests.dnd_discussion_reports import (
    dice_report_files,
    python_report_files,
    render_all_discussion_reports,
)


class DndDiscussionReportTest(unittest.TestCase):
    def test_all_discussion_reports_render(self):
        expected_count = len(dice_report_files()) + len(python_report_files())
        self.assertGreater(expected_count, 0, "expected at least one discussion report sample")

        output_dir = Path(tempfile.mkdtemp(prefix="dice-discussion-reports-"))
        rendered_paths = render_all_discussion_reports(output_dir)

        self.assertEqual(len(rendered_paths), expected_count)
        for path in rendered_paths:
            with self.subTest(report=str(path)):
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
