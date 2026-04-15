# Troll Test Setup

The Troll files in this directory are only used by the internal comparison tests in [tests/test_troll_comparison.py](/home/felix/_Documents/Projects/dice/tests/test_troll_comparison.py:1).

## How To Make The Tests Work

Use one of these options:

1. Install Troll so the `troll` binary is available on `PATH`.
2. Set `DICE_TROLL_BIN=/absolute/path/to/troll` before running the tests.
3. Create a local workspace-only setup under `.tools/`:
   - place Moscow ML at `.tools/mosml/`
   - place the Troll bytecode image at `.tools/troll/troll`
   - the helper script [run_troll.sh](/home/felix/_Documents/Projects/dice/tests/troll/run_troll.sh:1) will then run Troll through `.tools/mosml/bin/camlrunm`

Example:

```bash
python3 -m unittest tests.test_troll_comparison -v
```

If Troll is unavailable, the comparison test will skip and point back to this file.
