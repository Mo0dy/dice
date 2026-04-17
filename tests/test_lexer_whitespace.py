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

from lexer import AS, CARET, DEDENT, EOF, HIGH, ID, IMPORT, INDENT, INTEGER, LOW, MATCH, OTHERWISE, PIPE, RES, ROLL, SEMI, SPLIT, SPLITZERO, STRING, AT, Lexer


def tokens(text):
    lexer = Lexer(text)
    result = []
    while True:
        token = lexer.next_token()
        if token.type == EOF:
            break
        result.append((token.type, token.value))
    return result


class LexerWhitespaceTest(unittest.TestCase):
    def test_identifier_stays_identifier_without_spaces(self):
        self.assertEqual(tokens("adb"), [(ID, "adb")])

    def test_spaced_binary_roll_uses_roll_operator(self):
        self.assertEqual(tokens("a d b"), [(ID, "a"), (ROLL, "d"), (ID, "b")])

    def test_compact_identifier_with_digits_stays_identifier(self):
        self.assertEqual(tokens("ad20"), [(ID, "ad20")])

    def test_spaced_identifier_then_literal_roll_tokenizes(self):
        self.assertEqual(tokens("a d20"), [(ID, "a"), (ROLL, "d"), (INTEGER, 20)])

    def test_integer_then_spaced_identifier_roll_tokenizes(self):
        self.assertEqual(tokens("2 d b"), [(INTEGER, 2), (ROLL, "d"), (ID, "b")])

    def test_spaced_unary_roll_tokenizes(self):
        self.assertEqual(tokens("d sides"), [(ROLL, "d"), (ID, "sides")])

    def test_spaced_keep_high_tokenizes(self):
        self.assertEqual(tokens("a d b h c"), [(ID, "a"), (ROLL, "d"), (ID, "b"), (HIGH, "h"), (ID, "c")])

    def test_spaced_keep_low_tokenizes(self):
        self.assertEqual(tokens("a d b l c"), [(ID, "a"), (ROLL, "d"), (ID, "b"), (LOW, "l"), (ID, "c")])

    def test_strings_preserve_internal_spaces(self):
        self.assertEqual(tokens('"fire bolt"'), [(STRING, "fire bolt")])

    def test_comments_are_skipped_and_newlines_still_split_statements(self):
        self.assertEqual(tokens('x = 1 # keep this\n y = 2'), [(ID, "x"), ("ASSIGN", "="), (INTEGER, 1), (SEMI, "\n"), (ID, "y"), ("ASSIGN", "="), (INTEGER, 2)])

    def test_split_keywords_tokenize(self):
        self.assertEqual(
            tokens("split d20 as roll | otherwise -> 0 ||"),
            [(SPLIT, "split"), (ROLL, "d"), (INTEGER, 20), (AS, "as"), (ID, "roll"), ("ELSE", "|"), (OTHERWISE, "otherwise"), (RES, "->"), (INTEGER, 0), (SPLITZERO, "||")],
        )

    def test_match_keyword_stays_reserved_for_migration_hint(self):
        self.assertEqual(tokens("match"), [(MATCH, "match")])

    def test_at_tokenizes_for_anonymous_split_binding(self):
        self.assertEqual(tokens("@"), [(AT, "@")])

    def test_import_keyword_tokenizes(self):
        self.assertEqual(tokens('import "spells/base.dice"'), [(IMPORT, "import"), (STRING, "spells/base.dice")])

    def test_sum_name_tokenizes_as_identifier(self):
        self.assertEqual(tokens("sum(3, d6)"), [(ID, "sum"), ("LPAREN", "("), (INTEGER, 3), ("COMMA", ","), (ROLL, "d"), (INTEGER, 6), ("RPAREN", ")")])

    def test_render_name_tokenizes_as_identifier(self):
        self.assertEqual(tokens('render(d20, "hit")'), [(ID, "render"), ("LPAREN", "("), (ROLL, "d"), (INTEGER, 20), ("COMMA", ","), (STRING, "hit"), ("RPAREN", ")")])

    def test_pipeline_tokenizes(self):
        self.assertEqual(tokens("d20 $ mean"), [(ROLL, "d"), (INTEGER, 20), (PIPE, "$"), (ID, "mean")])

    def test_repeat_sum_operator_tokenizes_without_spaces(self):
        self.assertEqual(tokens("d6^3"), [(ROLL, "d"), (INTEGER, 6), (CARET, "^"), (INTEGER, 3)])

    def test_repeat_sum_operator_tokenizes_with_spaces(self):
        self.assertEqual(tokens("d6 ^ 3"), [(ROLL, "d"), (INTEGER, 6), (CARET, "^"), (INTEGER, 3)])

    def test_indented_function_body_emits_indent_and_dedent_tokens(self):
        self.assertEqual(
            tokens("f(x):\n    y = x + 1\n    y"),
            [
                (ID, "f"),
                ("LPAREN", "("),
                (ID, "x"),
                ("RPAREN", ")"),
                ("COLON", ":"),
                (SEMI, "\n"),
                (INDENT, None),
                (ID, "y"),
                ("ASSIGN", "="),
                (ID, "x"),
                ("PLUS", "+"),
                (INTEGER, 1),
                (SEMI, "\n"),
                (ID, "y"),
                (DEDENT, None),
            ],
        )

    def test_keyword_argument_tokenizes_as_identifier_assign_expression(self):
        self.assertEqual(
            tokens("spell(slot_level=3)"),
            [(ID, "spell"), ("LPAREN", "("), (ID, "slot_level"), ("ASSIGN", "="), (INTEGER, 3), ("RPAREN", ")")],
        )


if __name__ == "__main__":
    unittest.main()
