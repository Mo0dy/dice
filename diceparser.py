#!/usr/bin/env python3


"""The Parser generates an Abstract Syntax Tree from a tokenstream"""


from syntaxtree import BinOp, TenOp, Val, UnOp, VarOp, Op, FunctionDef, Call, Match, MatchClause
from lexer import Token, Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, RES, PLUS, MINUS, MUL, DIV, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF, DIS, ADV, LPAREN, RPAREN, ELSEDIV, HIGH, LOW, AVG, PROP, ASSIGN, SEMI, ID, PRINT, STRING, LABEL, XLABEL, YLABEL, PLOT, SHOW, DOT, MATCH, AS, OTHERWISE


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

    def exception(self, message=""):
        """Raises a parser exception"""
        raise Exception("Parser exception: {}".format(message))

    def eat(self, type):
        """Checks for token type and advances token"""
        if type != self.current_token.type:
            self.exception("Tried to eat: {} but found {}".format(type, self.current_token.type))
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
        )

    def restore(self, state):
        self.current_token, self.peek_token, self.lexer.string_input = state

    def eat_match_separators(self):
        while self.current_token.type == SEMI and self.peek_token.type in [SEMI, ELSE]:
            self.eat(SEMI)


class DiceParser(Parser):
    """Parser for the Dice language

    Grammar:
        expr      :  comp (RES comp ((ELSE comp) | ELSEDIV)?)?
        comp      :  side ((GREATER_OR_EQUAL | LESS_OR_EQUAL | GREATER | LESS | EQUAL) side)?
        side      :  term ((ADD | SUB) term)*
        term      :  res ((MUL | DIV) res)*
        res       :  (PROP | ADV)? index
        index     :  roll (brack | dot)?
        roll      :  factor (ROLL factor ((HIGH | LOW) factor)?)?
        factor    :  INTEGER | STRING | ID | LPAREN exp RPAREN | brack | match | ROLL factor | DIS factor | ADV factor | AVG expr | PROP expr
        brack     :  LBRACK expr (COLON expr | (COMMA expr)*) RBRACK
        match     :  MATCH expr AS ID (SEMI)* match_clause ((SEMI)* match_clause)*
        match_clause : ELSE (OTHERWISE | expr) ASSIGN expr
        dot       :  DOT (INTEGER | ID)
    """

    # This just implements the grammar

    def brack(self):
        token = self.current_token
        self.eat(LBRACK)
        value1 = self.expr()
        if self.current_token.type == COLON:
            token = self.current_token
            self.eat(COLON)
            value2 = self.expr()
            self.eat(RBRACK)
            return BinOp(value1, token, value2)

        # Comma seperated values could also be implemented with a bounch of unary operators appending to a list
        # Somehow this (variadic operator) seems more straigtforward to me
        nodes = [value1]
        while self.current_token.type != RBRACK:
            self.eat(COMMA)
            nodes.append(self.expr())
        self.eat(RBRACK)
        return VarOp(token, nodes)

    def match_expr(self):
        token = self.current_token
        self.eat(MATCH)
        value = self.expr()
        self.eat(AS)
        if self.current_token.type != ID:
            self.exception("Expected identifier after as")
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
            self.exception("Expected at least one match clause")
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
            self.exception("Expected factor")

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
                self.exception("Expected INTEGER or ID")
        return node

    def res(self):
        token = None
        if self.current_token.type == PROP:
            token = self.current_token
            self.eat(PROP)
        elif self.current_token.type == AVG:
            token = self.current_token
            self.eat(AVG)
        return UnOp(self.index(), token) if token else self.index()

    def term(self):
        node = self.res()
        while self.current_token.type in [MUL, DIV]:
            # MUL and DIV are both binary operators so they can be created by the same commands
            token = self.current_token
            self.eat(token.type)
            node = BinOp(node, token, self.res())
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

    def expr(self):
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

    def statement(self):
        function_definition = self.try_function_definition()
        if function_definition:
            return function_definition
        if self.current_token.type == ID and self.peek_token.type == ASSIGN:
            token = self.current_token
            self.eat(ID)
            left = Val(token)
            token = self.current_token
            self.eat(ASSIGN)
            return BinOp(left, token, self.expr())
        elif self.current_token.type in [PRINT, LABEL, XLABEL, YLABEL, PLOT]:
            token = self.current_token
            self.eat(token.type)
            return UnOp(self.expr(), token)
        elif self.current_token.type == SHOW:
            token = self.current_token
            self.eat(SHOW)
            return Op(token)
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
            self.exception("Expected statement")
        if len(nodes) == 1:
            return nodes[0]
        return VarOp(Token(SEMI, ";"), nodes)

    def parse(self):
        node = self.program()
        if self.current_token.type != EOF:
            self.exception("Could not parse {}".format(self.current_token))
        return node

if __name__ == "__main__":
    lexer = Lexer('a = "test"; plot a; show')
    parser = DiceParser(lexer)
    ast = parser.parse()
    print(ast)
