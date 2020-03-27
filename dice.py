#!/usr/bin/env python3

"""Interactive interpreter"""

import sys
import fileinput
import re

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from diceparser import DiceParser
from lexer import Lexer
from preprocessor import Preprocessor

def interpret(text, roundlevel=0):
    """Interprete command and return output"""
    try:
        result = Interpreter(DiceParser(Lexer(text)).expr()).interpret()
        # round and prettyfy
        if isinstance(result, ResultList) or isinstance(result, Distrib):
            if roundlevel:
                for k, v in result.items():
                    result[k] = round(v, roundlevel)
        return result
    except Exception as e:
        return str(e)

def runinteractive():
    """Get in put from console"""
    while True:
        roundlevel = 2
        text = input("dice> ")
        if text == "exit":
            return 0
        print(interpret(text, roundlevel))
    return 2


def main(args):
    # set if output should be grepable
    grepable = False
    roundlevel = 0
    # remove filename
    args = args[1:]
    while args:
        if args[0] in ["-i", "--interactive"]:
            return runinteractive()
            args = args[1:]
        elif args[0] in ["-e", "--execute"] and len(args) > 1:
            sys.stdout.write(str(interpret(args[1], roundlevel)) + "\n")
            return 0
        elif args[0] in ["-g", "--grepable"]:
            grepable = True
            args = args[1:]
        elif args[0] in ["-r", "--round"]:
            args = args[1:]
            if args and args[0].isdigit():
                roundlevel = int(args[0])
                args = args[1:]
        else:
            # no arg worked break loop
            break

    input_lines = fileinput.input(args)
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
        result = str(interpret(line, roundlevel))
        if result:
            if not grepable:
                sys.stdout.write("dice> " + line)
            sys.stdout.write(str(result) + "\n")
            if not grepable:
                sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
