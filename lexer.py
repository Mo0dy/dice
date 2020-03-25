#!/usr/bin/env python3

import re

# Tokens
INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, PLUS, MINUS, MUL, DIV, RES, ELSE, LBRACK, RBRACK, COMMA, COLON, EOF = "INTEGER", "ROLL", "GREATER_OR_EQUAL", "LESS_OR_EQUAL", "LESS", "GREATER", "EQUAL", "PLUS", "MINUS", "MUL", "DIV", "RES", "ELSE", "LBRACK", "RBRACK", "COMMA", "COLON", "EOF"

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
        """Finds next token"""

        # NOTE: more complex symbols need to be matched first if they contain less complex symbols
        # e.g. -> before -

        # the part of the text that has not yet been interpreted
        expression = self.text[self.index:]

        match = re.search(r"^\:", expression)
        if match:
            self.index += len(match[0])
            return Token(COLON, ":")

        match = re.search(r"^\,", expression)
        if match:
            self.index += len(match[0])
            return Token(COMMA, ",")

        match = re.search(r"^\[", expression)
        if match:
            self.index += len(match[0])
            return Token(LBRACK, "[")

        match = re.search(r"^\]", expression)
        if match:
            self.index += len(match[0])
            return Token(RBRACK, "]")

        match = re.search(r"^\-\>", expression)
        if match:
            self.index += len(match[0])
            return Token(RES, "->")

        match = re.search(r"^\|", expression)
        if match:
            self.index += len(match[0])
            return Token(ELSE, "|")

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
            return Token(GREATER_OR_EQUAL, ">=")

        match = re.search(r"^\<=", expression)
        if match:
            self.index += len(match[0])
            return Token(LESS_OR_EQUAL, "<=")

        match = re.search(r"^\<", expression)
        if match:
            self.index += len(match[0])
            return Token(LESS, "<")

        match = re.search(r"^\>", expression)
        if match:
            self.index += len(match[0])
            return Token(GREATER, ">")

        match = re.search(r"^==", expression)
        if match:
            self.index += len(match[0])
            return Token(EQUAL, "==")

        match = re.search(r"^\+", expression)
        if match:
            self.index += len(match[0])
            return Token(PLUS, "+")

        match = re.search(r"^\-", expression)
        if match:
            self.index += len(match[0])
            return Token(MINUS, "-")

        match = re.search(r"^\*", expression)
        if match:
            self.index += len(match[0])
            return Token(MUL, "*")

        match = re.search(r"^/", expression)
        if match:
            self.index += len(match[0])
            return Token(DIV, "/")


        # can't find anything anymore
        if len(self.text) != self.index:
            self.exception("Can not evaluate: '{}'".format(self.text[self.index:]))
        # end of token stream
        return Token(EOF, "EOF")
