import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_statement


def readme_examples():
    text = README.read_text(encoding="utf-8")
    blocks = re.findall(r"```dice\n(.*?)```", text, re.DOTALL)
    examples = []
    for block in blocks:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if line:
                examples.append(line)
    return examples

class ReadmeExamplesTest(unittest.TestCase):
    def test_readme_examples_execute(self):
        examples = readme_examples()
        self.assertTrue(examples, "README.md should contain at least one ```dice``` example block")

        for example in examples:
            with self.subTest(example=example):
                result = interpret_statement(example)
                self.assertIsNot(result, NotImplemented)


if __name__ == "__main__":
    unittest.main()
