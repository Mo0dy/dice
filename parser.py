#!/usr/bin/env python3

import re
from syntaxtree import BinOp, Val
from lexer import Token, Lexer, INTEGER, ROLL, GREATER_THEN, IF_THEN, PLUS, EOF

"""Generates Abstract Syntax Trees"""


class Parser(object):
    """Basic parser funcitonality"""
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = lexer.next_token()

    def exception(self, message=""):
        raise Exception("Could not parse: {}".format(message))

    def eat(self, type):
        """Checks for token type and advances token"""
        if type != self.current_token.type:
            self.exception("Tried to eat: {} but found {}".format(type, self.current_token.type))
        self.current_token = self.lexer.next_token()


class DiceParser(Parser):
    """Parser for the Dice language"""
    def factor(self):
        token = self.current_token
        self.eat(INTEGER)
        return Val(token)

    def roll(self):
        node = self.factor()
        if self.current_token.type == ROLL:
            token = self.current_token
            self.eat(ROLL)
            node = BinOp(node, token, self.factor())
        return node

    def side(self):
        node = self.roll()
        while self.current_token.type == PLUS:
            token = self.current_token
            self.eat(PLUS)
            node = BinOp(node, token, self.roll())
        return node

    def expr(self):
        node = self.side()
        if self.current_token.type == GREATER_THEN:
            # store token for AST
            token = self.current_token
            self.eat(GREATER_THEN)
            node = BinOp(node, token, self.side())
        return node

if __name__ == "__main__":
    lexer = Lexer("1d20 + 2 >= 20")
    parser = DiceParser(lexer)
    ast = parser.expr()
    print(ast)
