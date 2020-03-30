#!/usr/bin/env python3

"""Lexer for the "dice" language.

Is used to convert string input into a token stream"""


import re


# Tokens
INTEGER = "INTEGER"                      # any number
ROLL = "ROLL"                            # "d"
GREATER_OR_EQUAL = "GREATER_OR_EQUAL"    # ">="
LESS_OR_EQUAL = "LESS_OR_EQUAL"          # "<="
LESS = "LESS"                            # "<"
GREATER = "GREATER"                      # ">"
EQUAL = "EQUAL"                          # "=="
PLUS = "PLUS"                            # "+"
MINUS = "MINUS"                          # "-"
MUL = "MUL"                              # "*"
DIV = "DIV"                              # "/"
RES = "RES"                              # "->"
ELSE = "ELSE"                            # "|"
LBRACK = "LBRACK"                        # "["
RBRACK = "RBRACK"                        # "]"
COMMA = "COMMA"                          # ","
COLON = "COLON"                          # ":"
ADV = "ADV"                              # "d+"
DIS = "DIS"                              # "d-"
LPAREN = "LPAREN"                        # "("
RPAREN = "RPAREN"                        # ")"
ELSEDIV = "ELSEDIV"                      # "|/"
HIGH = "HIGH"                            # "h"
LOW = "LOW"                              # "l"
EOF = "EOF"                              # end of file


class Token(object):
    """Basic token for the interpreter. Holds type and value"""
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return "Token: {type}, {value}".format(type=self.type, value=self.value)


class Lexer(object):
    """Generate tokensteam from string input for dice language"""

    def __init__(self, string_input):
        """test = complete text to be interpreted"""
        # stores the string that has yet to interpreted
        self.string_input = self.cauterize_input(string_input)
        # keep the original text in case needed
        self.original_text = string_input

    def exception(self, message=""):
        """Raises a lexer exception"""
        raise Exception("Lexer exception: {}".format(message))

    def cauterize_input(self, expression):
        """Modifies input by removing uninteresting charcters (\n, " ")"""
        # TODO: this should done more universal
        return expression.replace(" ", "").replace("\n", "")

    def next_token(self):
        """Returns next token in tokenstream"""

        # Matches tokens with regex

        # all regular expressions for tokens and funcitons generating them from the matched string
        # NOTE: more complex symbols need to be matched first if they contain less complex symbols
        # e.g. -> before -
        # NOTE: no need to match beginning of string because re.match is used
        token_re_list = [
            [r"h", lambda x: Token(HIGH, x)],
            [r"l", lambda x: Token(LOW, x)],
            [r"\|\/", lambda x: Token(ELSEDIV, x)],
            [r"\(", lambda x: Token(LPAREN, x)],
            [r"\)", lambda x: Token(RPAREN, x)],
            [r"d\-", lambda x: Token(DIS, x)],
            [r"d\+", lambda x: Token(ADV, x)],
            [r"\:", lambda x: Token(COLON, x)],
            [r"\,", lambda x: Token(COMMA, x)],
            [r"\[", lambda x: Token(LBRACK, x)],
            [r"\]", lambda x: Token(RBRACK, x)],
            [r"\-\>", lambda x: Token(RES, x)],
            [r"\|", lambda x: Token(ELSE, x)],
            [r"d", lambda x: Token(ROLL, x)],
            [r"\>=", lambda x: Token(GREATER_OR_EQUAL, x)],
            [r"\<=", lambda x: Token(LESS_OR_EQUAL, x)],
            [r"\<", lambda x: Token(LESS, x)],
            [r">", lambda x: Token(GREATER, x)],
            [r"==", lambda x: Token(EQUAL, x)],
            [r"\+", lambda x: Token(PLUS, x)],
            [r"\-", lambda x: Token(MINUS, x)],
            [r"\*", lambda x: Token(MUL, x)],
            [r"/", lambda x: Token(DIV, x)],
            [r"[0-9]+", lambda x: Token(INTEGER, int(x))],
        ]

        # check tokens in order
        for regex, token_gen in token_re_list:
            # match only matches from the beginning of the string
            match = re.match(regex, self.string_input)
            if match:
                # advance string
                self.string_input = self.string_input[len(match[0]):]
                # generate token from generating function
                return token_gen(match.group(0))

        # can't find anything anymore but still input string
        if self.string_input:
            self.exception("Can not evaluate: '{}'".format(self.text[self.index:]))

        # end of token stream
        return Token(EOF, "EOF")
