import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "manual"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dice import interpret_file
from tests.doc_examples import iter_markdown_code_blocks


def manual_examples():
    for path in sorted(MANUAL.rglob("*.md")):
        for block in iter_markdown_code_blocks(path):
            yield block


class ManualExamplesTest(unittest.TestCase):
    def test_manual_examples_execute(self):
        examples = list(manual_examples())
        self.assertTrue(examples, "manual/ should contain at least one executable example block")

        for block in examples:
            label = f'{block["path"].relative_to(ROOT)}#{block["index"]}:{block["language"]}'
            with self.subTest(example=label):
                if block["language"] == "dice":
                    result = interpret_file(
                        block["source"],
                        current_dir=block["path"].parent,
                        source_name=str(block["path"].relative_to(ROOT)),
                    )
                    self.assertIsNot(result, NotImplemented)
                    continue

                if block["language"] == "python":
                    namespace = {"__name__": "__manual_example__"}
                    exec(block["source"], namespace, namespace)
                    continue

                self.fail(f"Unsupported executable code block language in manual: {block['language']}")


if __name__ == "__main__":
    unittest.main()
