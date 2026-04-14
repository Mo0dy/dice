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
AVG = "AVG"                              # "~"
PROP = "PROP"                            # "!"
ELSE = "ELSE"                            # "|"
LBRACK = "LBRACK"                        # "["
RBRACK = "RBRACK"                        # "]"
COMMA = "COMMA"                          # ","
COLON = "COLON"                          # ":"
DOT = "DOT"                              # ".
ADV = "ADV"                              # "d+"
DIS = "DIS"                              # "d-"
LPAREN = "LPAREN"                        # "("
RPAREN = "RPAREN"                        # ")"
ELSEDIV = "ELSEDIV"                      # "|/"
HIGH = "HIGH"                            # "h"
LOW = "LOW"                              # "l"
EOF = "EOF"                              # end of file
SEMI = "SEMI"                            # "SEMI"
ID = "ID"                                # any valid variable defenition
ASSIGN = "ASSIGN"                        # "="
PRINT = "PRINT"                          # "print"
STRING = "STRING"                        # anything inside ""

# Plotting intrinsics
PLOT = "PLOT"                            # "plot"
XLABEL = "XLABEL"                        # "xlabel"
YLABEL = "YLABEL"                        # "ylabel"
LABEL = "LABEL"                          # "label"
SHOW = "SHOW"                            # "show"
MATCH = "MATCH"                          # "match"
AS = "AS"                                # "as"
OTHERWISE = "OTHERWISE"                  # "otherwise"
IMPORT = "IMPORT"                        # "import"
SUM = "SUM"                              # "sum"



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
        self.string_input = self.normalize_input(string_input)
        # keep the original text in case needed
        self.original_text = string_input
        self.location = 0

    def exception(self, message=""):
        """Raises a lexer exception"""
        raise Exception("Lexer exception: {}".format(message))

    def normalize_input(self, expression):
        """Normalizes line endings while preserving ordinary spaces."""
        return expression.replace("\r\n", "\n").replace("\r", "\n")

    def next_token(self):
        """Returns next token in tokenstream"""
        while self.string_input and self.string_input[0] in [" ", "\t"]:
            self.string_input = self.string_input[1:]

        if self.string_input.startswith("//"):
            comment_end = 2
            while comment_end < len(self.string_input) and self.string_input[comment_end] != "\n":
                comment_end += 1
            self.string_input = self.string_input[comment_end:]
            return self.next_token()

        # Matches tokens with regex

        # all regular expressions for tokens and funcitons generating them from the matched string
        # NOTE: more complex symbols need to be matched first if they contain less complex symbols
        # e.g. -> before -
        # NOTE: no need to match beginning of string because re.match is used
        token_re_list = [
            [r'".*?"', lambda x: Token(STRING, x[1:-1])],
            [r"print\b", lambda x: Token(PRINT, x)],
            [r"xlabel\b", lambda x: Token(XLABEL, x)],
            [r"ylabel\b", lambda x: Token(YLABEL, x)],
            [r"label\b", lambda x: Token(LABEL, x)],
            [r"plot\b", lambda x: Token(PLOT, x)],
            [r"show\b", lambda x: Token(SHOW, x)],
            [r"match\b", lambda x: Token(MATCH, x)],
            [r"as\b", lambda x: Token(AS, x)],
            [r"otherwise\b", lambda x: Token(OTHERWISE, x)],
            [r"import\b", lambda x: Token(IMPORT, x)],
            [r"sum\b", lambda x: Token(SUM, x)],
            # d+ needed to not confuse indexing (d20.20)
            [r"\n",    lambda x: Token(SEMI, x)],
            [r"\;",    lambda x: Token(SEMI, x)],
            [r"h(?=\b|\s|\d|\(|\[|\"|\!|\~)", lambda x: Token(HIGH, x)],
            [r"l(?=\b|\s|\d|\(|\[|\"|\!|\~)", lambda x: Token(LOW, x)],
            [r"\|\/", lambda x: Token(ELSEDIV, x)],
            [r"\(",   lambda x: Token(LPAREN, x)],
            [r"\)",   lambda x: Token(RPAREN, x)],
            [r"d\-",  lambda x: Token(DIS, x)],
            [r"d\+",  lambda x: Token(ADV, x)],
            [r"\:",   lambda x: Token(COLON, x)],
            [r"\.",   lambda x: Token(DOT, x)],
            [r"\,",   lambda x: Token(COMMA, x)],
            [r"\[",   lambda x: Token(LBRACK, x)],
            [r"\]",   lambda x: Token(RBRACK, x)],
            [r"\-\>", lambda x: Token(RES, x)],
            [r"~",    lambda x: Token(AVG, x)],
            [r"\!",   lambda x: Token(PROP, x)],
            [r"\|",   lambda x: Token(ELSE, x)],
            [r"d(?=\b|\s|\d|\(|\[|\"|\!|\~)", lambda x: Token(ROLL, x)],
            [r"\>=",  lambda x: Token(GREATER_OR_EQUAL, x)],
            [r"\<=",  lambda x: Token(LESS_OR_EQUAL, x)],
            [r"\<",   lambda x: Token(LESS, x)],
            [r">",    lambda x: Token(GREATER, x)],
            [r"==",   lambda x: Token(EQUAL, x)],
            [r"\+",   lambda x: Token(PLUS, x)],
            [r"\-",   lambda x: Token(MINUS, x)],
            [r"\*",   lambda x: Token(MUL, x)],
            [r"/",    lambda x: Token(DIV, x)],
            [r"\=",   lambda x: Token(ASSIGN, x)],
            # try to match anything else to a variable or number
            [r"\d+",  lambda x: Token(INTEGER, int(x))],
            [r"\w+",  lambda x: Token(ID, x)],
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
            self.exception("Can not evaluate: '{}'".format(self.string_input))

        # end of token stream
        return Token(EOF, "EOF")
