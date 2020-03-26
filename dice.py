#!/usr/bin/env python3

"""Interactive interpreter"""

import sys
import fileinput

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from parser import DiceParser
from lexer import Lexer

def interpret(text):
    try:
        result = Interpreter(DiceParser(Lexer(text)).expr()).interpret()
        # round and prettyfy
        if isinstance(result, ResultList) or isinstance(result, Distrib):
            for k, v in result.items():
                result[k] = round(v, 2)
        return result
    except Exception as e:
        return str(e)

def runinteractive():
    while True:
        text = input("dice> ")
        if text == "exit":
            return 0
        print(interpret(text))
    return 2

def main(args):
    if len(args) > 1 and args[1] in ["-i", "--interactive"]:
        return runinteractive()

    input_lines = fileinput.input()
    for line in input_lines:
        print("dice> ", line)
        print(interpret(line))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
