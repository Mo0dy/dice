#!/usr/bin/env python3


"""The Parser generates an Abstract Syntax Tree from a tokenstream"""


import re
from syntaxtree import BinOp, TenOp, Val, UnOp, VarOp
from lexer import Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, RES, PLUS, MINUS, MUL, DIV, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF, DIS, ADV, LPAREN, RPAREN, ELSEDIV, HIGH, LOW, AVG, PROP, BEGIN, END, ASSIGN, SEMI, ID, PRINT


class Parser(object):
    """The baseclass for all parsers."""
    def __init__(self, lexer):
        """lexer = Reference to the lexer to generate tokenstream"""
        # TODO: implement lexer as generator to reduce dependencies
        self.lexer = lexer
        # Stores the token that is currently being operated on.
        # This variable can be advanced manully or by using self.eat
        self.current_token = lexer.next_token()

    def exception(self, message=""):
        """Raises a parser exception"""
        raise Exception("Parser exception: {}".format(message))

    def eat(self, type):
        """Checks for token type and advances token"""
        if type != self.current_token.type:
            self.exception("Tried to eat: {} but found {}".format(type, self.current_token.type))
        self.current_token = self.lexer.next_token()


class DiceParser(Parser):
    """Parser for the Dice language

    Grammar:
        expr      :  comp (RES comp ((ELSE comp) | ELSEDIV)?)?
        comp      :  side ((GREATER_OR_EQUAL | LESS_OR_EQUAL | GREATER | LESS | EQUAL) side)?
        side      :  term ((ADD | SUB) term)*
        term      :  res ((MUL | DIV) res)*
        res       :  (PROP | ADV)? index
        index     :  roll (brack)?
        roll      :  factor (ROLL factor ((HIGH | LOW) factor)?)?
        factor    :  INTEGER | LPAREN exp RPAREN | brack | ROLL factor | DIS factor | ADV factor
        brack     :  LBRACK expr (COLON expr | (COMMA expr)*) RBRACK
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

    def factor(self):
        if self.current_token.type == LBRACK:
            return self.brack()
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
            return Val(token)
        else:
            token = self.current_token
            self.eat(INTEGER)
            return Val(token)

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
            return BinOp(node, token, self.roll())
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
        if self.current_token.type == ID:
            token = self.current_token
            self.eat(ID)
            left = Val(token)
            token = self.current_token
            self.eat(ASSIGN)
            return BinOp(left, token, self.expr())
        elif self.current_token.type == PRINT:
            token = self.current_token
            self.eat(PRINT)
            return UnOp(self.expr(), token)
        else:
            return self.expr()

    def program(self):
        token = self.current_token
        self.eat(BEGIN)
        nodes = []
        # at least one statement
        while self.current_token.type != END:
            nodes.append(self.statement())
            self.eat(SEMI)
        self.eat(END)
        return VarOp(token, nodes)

    def parse(self):
        node = self.program()
        if self.current_token.type != EOF:
            self.exception("Could not parse {}".format(self.current_token))
        return node

if __name__ == "__main__":
    lexer = Lexer("BEGIN a = 1; END")
    parser = DiceParser(lexer)
    ast = parser.parse()
    print(ast)
