#!/usr/bin/env python3
import random
import re
from diceengine import Diceprop


# class RollInterpreter(Interpreter):
#     """An interpreter for dice rolling"""
#     def factor(self):
#         result = self.current_token.value
#         self.eat(INTEGER)
#         return result

#     def term(self):
#         result = self.factor()
#         if self.current_token.type == ROLL:
#             self.eat(ROLL)
#             dicenum = self.factor()
#             result = sum([random.randint(1, dicenum) for _ in range(result)])
#         return result

#     def side(self):
#         result = self.term()
#         while self.current_token.type == PLUS:
#             self.eat(PLUS)
#             result += self.term()
#         return result

#     def throw(self):
#         result = self.side()
#         if self.current_token.type == GREATER_THEN:
#             self.eat(GREATER_THEN)
#             right_side = self.side()
#             result = result >= right_side
#         return result

#     def expr(self):
#         result = self.throw()
#         if self.current_token.type == IF_THEN:
#             self.eat(IF_THEN)
#             if result:
#                 result = self.side()
#             else:
#                 result = False
#         return result


class PropInterpreter(Interpreter):
    def factor(self):
        result = self.current_token.value
        self.eat(INTEGER)
        return result

    def roll(self):
        result = self.factor()
        if self.current_token.type == ROLL:
            self.eat(ROLL)
            dicesides = self.factor()
            result = Diceprop(result, dicesides)
        return result

    def side(self):
        result = self.roll()
        while self.current_token.type == PLUS:
            self.eat(PLUS)
            right_side = self.roll()
            result = Diceprop.add(result, right_side)
        return result

    def expr(self):
        result = self.side()
        if self.current_token.type == GREATER_THEN:
            self.eat(GREATER_THEN)
            right_side = self.side()
            result = Diceprop.greaterorequal(result, right_side)
        return result



if __name__ == "__main__":
    lexer = Lexer("1d20 >= 20")
    interpreter = PropInterpreter(lexer)
    print(interpreter.expr())
