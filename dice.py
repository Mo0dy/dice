#!/usr/bin/env python3

"""Interactive interpreter"""

import sys

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from parser import DiceParser
from lexer import Lexer

def interpret(text):
    result = Interpreter(DiceParser(Lexer(text)).expr()).interpret()
    # round and prittyfy
    if isinstance(result, ResultList) or isinstance(result, Distrib):
        for k, v in result.items():
            result[k] = round(v, 2)
    return result

if __name__ == "__main__":
    while True:
        text = input("dice> ")
        if text == "exit":
            break
        try:
            result = interpret(text)
            print(result)
        except Exception as e:
            print(e)
