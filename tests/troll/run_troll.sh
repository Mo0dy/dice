#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
README_PATH="$ROOT/tests/troll/README.md"

if [[ -n "${DICE_TROLL_BIN:-}" ]]; then
  exec "$DICE_TROLL_BIN" "$@"
fi

if command -v troll >/dev/null 2>&1; then
  exec "$(command -v troll)" "$@"
fi

LOCAL_CAMLRUNM="$ROOT/.tools/mosml/bin/camlrunm"
LOCAL_TROLL_IMAGE="$ROOT/.tools/troll/troll"

if [[ -x "$LOCAL_CAMLRUNM" && -f "$LOCAL_TROLL_IMAGE" ]]; then
  export LD_LIBRARY_PATH="$ROOT/.tools/mosml/lib/mosml${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  exec "$LOCAL_CAMLRUNM" "$LOCAL_TROLL_IMAGE" "$@"
fi

echo "Troll is not available. See $README_PATH" >&2
exit 127
