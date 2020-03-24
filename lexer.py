#!/usr/bin/env python3

import re

# Tokens
INTEGER, ROLL, GREATER_THEN, IF_THEN, PLUS, EOF = "INTEGER", "ROLL", "GREATER_THEN", "IF_THEN", "PLUS", "EOF"


class Token(object):
    """Basic token for the interpreter. Holds type and value"""
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return "Token: {type}, {value}".format(type=self.type, value=self.value)

    def __str__(self):
        return self.__repr__()


class Lexer(object):
    """Generate tokensteam from string input"""

    def __init__(self, text):
        self.text = self.cauterize_input(text)
        self.index = 0

    def exception(self, message=""):
        raise Exception("Lexer exception: {}".format(message))

    def cauterize_input(self, expression):
        return expression.replace(" ", "")

    def next_token(self):
        # the part of the text that has not yet been interpreted
        expression = self.text[self.index:]

        # find INTEGER token
        match = re.search(r"^[0-9]+", expression)
        if match:
            self.index += len(match[0])
            return Token(INTEGER, int(match[0]))

        # check for ROLL token
        match = re.search(r"^d", expression)
        if match:
            self.index += len(match[0])
            return Token(ROLL, 'd')

        # check for GREATER_THEN token
        match = re.search(r"^\>=", expression)
        if match:
            self.index += len(match[0])
            return Token(GREATER_THEN, ">=")

        match = re.search(r"^\+", expression)
        if match:
            self.index += len(match[0])
            return Token(PLUS, "+")

        match = re.search(r"^\-\>", expression)
        if match:
            self.index += len(match[0])
            return Token(IF_THEN, "->")

        # can't find anything anymore
        if len(self.text) != self.index:
            self.exception("Can not evaluate: '{}'".format(self.text[self.index:]))
        # end of token stream
        return Token(EOF, "EOF")
