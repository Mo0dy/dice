#!/usr/bin/env python3

"""Interactive interpreter"""

import sys
import fileinput
import re

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from parser import DiceParser
from lexer import Lexer
from preprocessor import Preprocessor

def interpret(text):
    """Interprete command and return output"""
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
    """Get in put from console"""
    while True:
        text = input("dice> ")
        if text == "exit":
            return 0
        print(interpret(text))
    return 2


def main(args):
    if len(args) > 1:
        if args[1] in ["-i", "--interactive"]:
            return runinteractive()
        elif args[1] in ["-e", "--execute"] and len(args) > 1:
            sys.stdout.write(interpret(args[2]))
            return 0

    input_lines = fileinput.input()
    preprocessor = Preprocessor()
    for line in input_lines:
        # comments
        if line.startswith("//") or line.startswith("\n"):
            continue
        # print statement
        if line[0] == '#':
            sys.stdout.write(line)
            continue
        # apply definitions:
        line = preprocessor.preprocess(line)
        # create new definitions
        if line.startswith("!define"):
            preprocessor.define(line[len("!define"):].strip())
            continue
        result = str(interpret(line))
        if result:
            sys.stdout.write("dice> " + line)
            sys.stdout.write(str(result) + "\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
