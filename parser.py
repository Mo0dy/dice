#!/usr/bin/env python3

import re
from syntaxtree import BinOp, TenOp, Val
from lexer import Token, Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, RES, PLUS, MINUS, MUL, DIV, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF

"""Generates Abstract Syntax Trees"""


class Parser(object):
    """Basic parser funcitonality"""
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = lexer.next_token()

    def exception(self, message=""):
        raise Exception("Parser exception: {}".format(message))

    def eat(self, type):
        """Checks for token type and advances token"""
        if type != self.current_token.type:
            self.exception("Tried to eat: {} but found {}".format(type, self.current_token.type))
        self.current_token = self.lexer.next_token()


class DiceParser(Parser):
    """Parser for the Dice language"""
    def factor(self):
        if self.current_token.type == LBRACK:
            self.eat(LBRACK)
            value1 = self.expr()
            token = self.current_token
            self.eat(COLON)
            value2 = self.expr()
            self.eat(RBRACK)
            return BinOp(value1, token, value2)
        else:
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

    def term(self):
        node = self.roll()
        while self.current_token.type in [MUL, DIV]:
            # MUL and DIV are both binary operators so they can be created by the same commands
            token = self.current_token
            self.eat(token.type)
            node = BinOp(node, token, self.roll())
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
            else:
                # no tenery operator just normal resolve
                node = BinOp(node, token, new_node1)
        return node

if __name__ == "__main__":
    lexer = Lexer("[1:5]")
    parser = DiceParser(lexer)
    ast = parser.expr()
    print(ast)
