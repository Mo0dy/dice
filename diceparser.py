#!/usr/bin/env python3

import re
from syntaxtree import BinOp, TenOp, Val, UnOp, VarOp
from lexer import Token, Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, RES, PLUS, MINUS, MUL, DIV, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF, DIS, ADV, LPAREN, RPAREN, ELSEDIV, HIGH, LOW

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
    def brack(self):
        """NOT a seperate level just a helper method"""
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
        elif self.current_token.type == ADV:
            token = self.current_token
            self.eat(ADV)
            return UnOp(self.factor(), token)
        elif self.current_token.type == DIS:
            token = self.current_token
            self.eat(DIS)
            return UnOp(self.factor(), token)
        elif self.current_token.type == RES:
            token = self.current_token
            self.eat(RES)
            return UnOp(self.expr(), token)
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

if __name__ == "__main__":
    lexer = Lexer("d20[20]")
    parser = DiceParser(lexer)
    ast = parser.expr()
    print(ast)
