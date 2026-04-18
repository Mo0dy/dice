import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("MPLBACKEND", "Agg")
mpl_config = Path(tempfile.gettempdir()) / "dice-mplconfig"
mpl_config.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CODE_BLOCK_PATTERN = re.compile(r"```([A-Za-z0-9_+-]+)\n(.*?)```", re.DOTALL)


def iter_markdown_code_blocks(path):
    text = Path(path).read_text(encoding="utf-8")
    for index, match in enumerate(CODE_BLOCK_PATTERN.finditer(text), start=1):
        language = match.group(1).strip().lower()
        source = match.group(2).strip()
        if not source:
            continue
        yield {
            "path": Path(path),
            "index": index,
            "language": language,
            "source": source,
        }
