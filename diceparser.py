#!/usr/bin/env python3


"""The Parser generates an Abstract Syntax Tree from a tokenstream"""


from diagnostics import ParserError
from syntaxtree import BinOp, TenOp, Val, UnOp, VarOp, Op, FunctionDef, Call, Match, MatchClause, Import, Named
from lexer import Token, Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, RES, PIPE, PLUS, MINUS, MUL, DIV, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF, DIS, ADV, LPAREN, RPAREN, ELSEDIV, HIGH, LOW, AVG, PROP, ASSIGN, SEMI, ID, PRINT, STRING, DOT, MATCH, AS, OTHERWISE, IMPORT

TOKEN_LABELS = {
    INTEGER: "integer",
    ROLL: "'d'",
    GREATER_OR_EQUAL: "'>='",
    LESS_OR_EQUAL: "'<='",
    LESS: "'<'",
    GREATER: "'>'",
    EQUAL: "'=='",
    RES: "'->'",
    PIPE: "'$'",
    PLUS: "'+'",
    MINUS: "'-'",
    MUL: "'*'",
    DIV: "'/'",
    ELSE: "'|'",
    ELSEDIV: "'|/'",
    LBRACK: "'['",
    RBRACK: "']'",
    COMMA: "','",
    COLON: "':'",
    LPAREN: "'('",
    RPAREN: "')'",
    HIGH: "'h'",
    LOW: "'l'",
    AVG: "'~'",
    PROP: "'!'",
    ASSIGN: "'='",
    SEMI: "statement separator",
    ID: "identifier",
    PRINT: "'print'",
    STRING: "string",
    DOT: "'.'",
    MATCH: "'match'",
    AS: "'as'",
    OTHERWISE: "'otherwise'",
    IMPORT: "'import'",
    EOF: "end of input",
}


class Parser(object):
    """The baseclass for all parsers."""
    def __init__(self, lexer):
        """lexer = Reference to the lexer to generate tokenstream"""
        # TODO: implement lexer as generator to reduce dependencies
        self.lexer = lexer
        # Keep one token of lookahead so assignments can be distinguished from
        # identifier expressions when parsing statements.
        self.current_token = lexer.next_token()
        self.peek_token = lexer.next_token()

    def exception(self, message="", token=None, hint=None):
        """Raises a parser exception"""
        token = self.current_token if token is None else token
        span = token.span if token is not None else None
        raise ParserError(message, span=span, hint=hint)

    def expected_token_hint(self, expected_type, actual_token):
        if actual_token.type == EOF and expected_type == RPAREN:
            return "You may be missing a closing ')'."
        if actual_token.type == EOF and expected_type == RBRACK:
            return "You may be missing a closing ']'."
        return None

    def token_label(self, token):
        if token.type == ID and token.value is not None:
            return "identifier {!r}".format(token.value)
        if token.type == INTEGER and token.value is not None:
            return "integer {!r}".format(token.value)
        if token.type == STRING and token.value is not None:
            return "string {!r}".format(token.value)
        return TOKEN_LABELS.get(token.type, token.type)

    def eat(self, type):
        """Checks for token type and advances token"""
        if type != self.current_token.type:
            self.exception(
                "expected {} but found {}".format(
                    TOKEN_LABELS.get(type, type),
                    self.token_label(self.current_token),
                ),
                token=self.current_token,
                hint=self.expected_token_hint(type, self.current_token),
            )
        self.current_token = self.peek_token
        self.peek_token = self.lexer.next_token()

    def eat_one_or_more(self, type):
        self.eat(type)
        while self.current_token.type == type:
            self.eat(type)

    def eat_zero_or_more(self, type):
        while self.current_token.type == type:
            self.eat(type)

    def snapshot(self):
        return (
            self.current_token,
            self.peek_token,
            self.lexer.string_input,
            self.lexer.location,
            self.lexer.line,
            self.lexer.column,
        )

    def restore(self, state):
        (
            self.current_token,
            self.peek_token,
            self.lexer.string_input,
            self.lexer.location,
            self.lexer.line,
            self.lexer.column,
        ) = state

    def eat_match_separators(self):
        while self.current_token.type == SEMI and self.peek_token.type in [SEMI, ELSE]:
            self.eat(SEMI)


class DiceParser(Parser):
    """Parser for the Dice language

    Grammar:
        expr      :  resolve (PIPE pipeline_target)*
        resolve   :  comp (RES comp ((ELSE comp) | ELSEDIV)?)?
        comp      :  side ((GREATER_OR_EQUAL | LESS_OR_EQUAL | GREATER | LESS | EQUAL) side)?
        side      :  term ((PLUS | MINUS) term)*
        term      :  index ((MUL | DIV) index)*
        index     :  roll (brack | dot)?
        roll      :  factor (ROLL factor ((HIGH | LOW) factor)?)?
        factor    :  INTEGER | STRING | ID | LPAREN expr RPAREN | brack | match | ROLL factor | DIS factor | ADV factor | AVG expr | PROP expr
        brack     :  LBRACK expr (COLON expr | (COMMA expr)*) RBRACK
        match     :  MATCH expr AS ID (SEMI)* match_clause ((SEMI)* match_clause)*
        match_clause : ELSE (OTHERWISE | expr) ASSIGN expr
        dot       :  DOT (INTEGER | ID)
        pipeline_target : ID | ID LPAREN expr (COMMA expr)* RPAREN
    """

    # This just implements the grammar

    def brack(self):
        token = self.current_token
        self.eat(LBRACK)
        sweep_name = None
        if self.current_token.type == ID and self.peek_token.type == COLON:
            sweep_name = Val(self.current_token)
            self.eat(ID)
            self.eat(COLON)
        value1 = self.expr()
        if self.current_token.type == COLON:
            token = self.current_token
            self.eat(COLON)
            value2 = self.expr()
            self.eat(RBRACK)
            node = BinOp(value1, token, value2)
            return Named(sweep_name, node) if sweep_name else node

        # Comma seperated values could also be implemented with a bounch of unary operators appending to a list
        # Somehow this (variadic operator) seems more straigtforward to me
        nodes = [value1]
        while self.current_token.type != RBRACK:
            self.eat(COMMA)
            nodes.append(self.expr())
        self.eat(RBRACK)
        node = VarOp(token, nodes)
        return Named(sweep_name, node) if sweep_name else node

    def match_expr(self):
        token = self.current_token
        self.eat(MATCH)
        value = self.expr()
        self.eat(AS)
        if self.current_token.type != ID:
            self.exception(
                "expected an identifier after 'as'",
                token=self.current_token,
                hint="Write a binding name like: match d20 as roll | roll == 20 = 10",
            )
        name = Val(self.current_token)
        self.eat(ID)
        self.eat_match_separators()
        clauses = []
        while self.current_token.type == ELSE:
            self.eat(ELSE)
            if self.current_token.type == OTHERWISE:
                self.eat(OTHERWISE)
                condition = None
                otherwise = True
            else:
                condition = self.expr()
                otherwise = False
            self.eat(ASSIGN)
            clauses.append(MatchClause(condition, self.expr(), otherwise=otherwise))
            self.eat_match_separators()
        if not clauses:
            self.exception(
                "expected at least one match clause",
                token=self.current_token,
                hint="Add a clause like '| otherwise = ...' or '| condition = ...'.",
            )
        return Match(value, name, clauses, token)

    def factor(self):
        if self.current_token.type == LBRACK:
            return self.brack()
        elif self.current_token.type == MATCH:
            return self.match_expr()
        elif self.current_token.type == LPAREN:
            self.eat(LPAREN)
            node = self.expr()
            self.eat(RPAREN)
            return node
        elif self.current_token.type == ROLL:
            token = self.current_token
            self.eat(ROLL)
            return UnOp(self.factor(), token)
        elif self.current_token.type == DIS:
            token = self.current_token
            self.eat(DIS)
            return UnOp(self.factor(), token)
        elif self.current_token.type == ADV:
            token = self.current_token
            self.eat(ADV)
            return UnOp(self.factor(), token)
        elif self.current_token.type == AVG:
            token = self.current_token
            self.eat(AVG)
            return UnOp(self.expr(), token)
        elif self.current_token.type == PROP:
            token = self.current_token
            self.eat(PROP)
            return UnOp(self.expr(), token)
        elif self.current_token.type == ID:
            token = self.current_token
            self.eat(ID)
            if self.current_token.type == LPAREN:
                return self.call(Val(token))
            return Val(token)
        elif self.current_token.type == STRING:
            token = self.current_token
            self.eat(STRING)
            return Val(token)
        elif self.current_token.type == INTEGER:
            token = self.current_token
            self.eat(INTEGER)
            return Val(token)
        else:
            self.exception(
                "expected an expression",
                token=self.current_token,
                hint="Try a number, identifier, function call, parenthesized expression, or dice expression.",
            )

    def call(self, name):
        self.eat(LPAREN)
        args = []
        if self.current_token.type != RPAREN:
            args.append(self.expr())
            while self.current_token.type == COMMA:
                self.eat(COMMA)
                args.append(self.expr())
        self.eat(RPAREN)
        return Call(name, args)

    def try_function_definition(self):
        if self.current_token.type != ID or self.peek_token.type != LPAREN:
            return None

        state = self.snapshot()
        try:
            name_token = self.current_token
            self.eat(ID)
            self.eat(LPAREN)
            params = []
            if self.current_token.type != RPAREN:
                if self.current_token.type != ID:
                    self.restore(state)
                    return None
                params.append(Val(self.current_token))
                self.eat(ID)
                while self.current_token.type == COMMA:
                    self.eat(COMMA)
                    if self.current_token.type != ID:
                        self.restore(state)
                        return None
                    params.append(Val(self.current_token))
                    self.eat(ID)
            self.eat(RPAREN)
            if self.current_token.type != ASSIGN:
                self.restore(state)
                return None
            self.eat(ASSIGN)
            return FunctionDef(Val(name_token), params, self.expr())
        except Exception:
            self.restore(state)
            raise

    def roll(self):
        node = self.factor()
        if self.current_token.type == ROLL:
            token = self.current_token
            self.eat(ROLL)
            node2 = self.factor()
            if self.current_token.type in [HIGH, LOW]:
                token2 = self.current_token
                self.eat(token2.type)
                return TenOp(node, token, node2, token2, self.factor())
            node = BinOp(node, token, node2)
        return node

    def index(self):
        node = self.roll()
        if self.current_token.type == LBRACK:
            token = self.current_token
            # NOTE: I changed this line to use self.factor() instead of self.roll() should be correct I guess
            return BinOp(node, token, self.factor())
        if self.current_token.type == DOT:
            token = self.current_token
            self.eat(DOT)
            if self.current_token.type == INTEGER or self.current_token.type == ID:
                return BinOp(node, token, self.factor())
            else:
                self.exception(
                    "expected an integer or identifier after '.'",
                    token=self.current_token,
                    hint="Use a literal index like '.1' or a variable name like '.target'.",
                )
        return node

    def term(self):
        node = self.index()
        while self.current_token.type in [MUL, DIV]:
            # MUL and DIV are both binary operators so they can be created by the same commands
            token = self.current_token
            self.eat(token.type)
            node = BinOp(node, token, self.index())
        return node

    def side(self):
        node = self.term()
        while self.current_token.type in [PLUS, MINUS]:
            # MINUS and PLUS are both binary operators so they can be created by the same commands
            token = self.current_token
            self.eat(token.type)
            node = BinOp(node, token, self.term())
        return node

    def comp(self):
        node = self.side()
        if self.current_token.type in [GREATER_OR_EQUAL, LESS_OR_EQUAL, GREATER, LESS, EQUAL]:
            # store token for AST
            token = self.current_token
            self.eat(token.type)
            node = BinOp(node, token, self.side())
        return node

    def resolve(self):
        node = self.comp()
        if self.current_token.type == RES:
            # store token for AST
            token = self.current_token
            self.eat(RES)
            # cache node if tenary operator gets called
            new_node1 = self.comp()
            if self.current_token.type == ELSE:
                token2 = self.current_token
                self.eat(ELSE)
                node = TenOp(node, token, new_node1, token2, self.comp())
            elif self.current_token.type == ELSEDIV:
                token2 = self.current_token
                self.eat(ELSEDIV)
                node = BinOp(node, token2, new_node1)
            else:
                # no tenery operator just normal resolve
                node = BinOp(node, token, new_node1)
        return node

    def pipeline_target(self, value):
        if self.current_token.type != ID:
            self.exception(
                "expected a function name after '$'",
                token=self.current_token,
                hint="Write a pipeline target like '$ mean' or '$ add(2)'.",
            )

        name = Val(self.current_token)
        self.eat(ID)
        args = [value]
        if self.current_token.type == LPAREN:
            self.eat(LPAREN)
            if self.current_token.type != RPAREN:
                args.append(self.expr())
                while self.current_token.type == COMMA:
                    self.eat(COMMA)
                    args.append(self.expr())
            self.eat(RPAREN)
        return Call(name, args)

    def expr(self):
        node = self.resolve()
        while self.current_token.type == PIPE:
            self.eat(PIPE)
            node = self.pipeline_target(node)
        return node

    def statement(self):
        function_definition = self.try_function_definition()
        if function_definition:
            return function_definition
        if self.current_token.type == IMPORT:
            token = self.current_token
            self.eat(IMPORT)
            if self.current_token.type != STRING:
                self.exception(
                    "expected a string path after 'import'",
                    token=self.current_token,
                    hint='Use a quoted path like import "helpers.dice".',
                )
            path = Val(self.current_token)
            self.eat(STRING)
            return Import(path, token)
        if self.current_token.type == ID and self.peek_token.type == ASSIGN:
            token = self.current_token
            self.eat(ID)
            left = Val(token)
            token = self.current_token
            self.eat(ASSIGN)
            return BinOp(left, token, self.expr())
        if self.current_token.type == PRINT:
            token = self.current_token
            self.eat(token.type)
            return UnOp(self.expr(), token)
        else:
            return self.expr()

    def program(self):
        nodes = []
        self.eat_zero_or_more(SEMI)
        while self.current_token.type != EOF:
            nodes.append(self.statement())
            if self.current_token.type == EOF:
                break
            self.eat_one_or_more(SEMI)
            self.eat_zero_or_more(SEMI)
        if not nodes:
            self.exception(
                "expected a statement",
                token=self.current_token,
                hint="Programs can contain assignments, imports, function definitions, or expressions.",
            )
        if len(nodes) == 1:
            return nodes[0]
        return VarOp(Token(SEMI, ";"), nodes)

    def parse(self):
        node = self.program()
        if self.current_token.type != EOF:
            self.exception(
                "unexpected trailing input starting at {}".format(self.token_label(self.current_token)),
                token=self.current_token,
            )
        return node

if __name__ == "__main__":
    lexer = Lexer('a = "test"; render(a)')
    parser = DiceParser(lexer)
    ast = parser.parse()
    print(ast)
