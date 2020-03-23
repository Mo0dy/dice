#!/usr/bin/env python3
import random
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

class Interpreter(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = lexer.next_token()
        print(self.current_token)

    def exception(self, message=""):
        raise Exception("Could not parse: {}".format(message))

    def eat(self, type):
        if type != self.current_token.type:
            self.exception("Tried to eat: {} but found {}".format(type, self.current_token.type))
        self.current_token = self.lexer.next_token()

    def factor(self):
        result = self.current_token.value
        self.eat(INTEGER)
        return result

    def term(self):
        result = self.factor()
        if self.current_token.type == ROLL:
            self.eat(ROLL)
            dicenum = self.factor()
            result = sum([random.randint(1, dicenum) for _ in range(result)])
            print("Rolled ", result, dicenum)
        return result

    def side(self):
        result = self.term()
        while self.current_token.type == PLUS:
            self.eat(PLUS)
            result += self.term()
        return result

    def throw(self):
        result = self.side()
        if self.current_token.type == GREATER_THEN:
            self.eat(GREATER_THEN)
            right_side = self.side()
            result = result >= right_side
        return result

    def expr(self):
        result = self.throw()
        if self.current_token.type == IF_THEN:
            self.eat(IF_THEN)
            if result:
                result = self.side()
            else:
                result = False
        return result


if __name__ == "__main__":
    lexer = Lexer("1d20 + 5 >= 15 -> 2d6 + 2")
    interpreter = Interpreter(lexer)
    print(interpreter.expr())
