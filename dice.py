#!/usr/bin/env python3


"""Interactive interpreter for the dice language"""

import sys
import fileinput
import re
import time

import timeout_decorator

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from diceparser import DiceParser
from lexer import Lexer
from preprocessor import Preprocessor
import viewer


timeout_seconds = 5


# Maximum runtime 5 seconds
@timeout_decorator.timeout(timeout_seconds)
def interpret_dice(text):
    return Interpreter(DiceParser(Lexer(text)).parse()).interpret()

def interpret(text, preprocessor, roundlevel=0):
    """Interprete command and return output"""
    # print statement
    if text.startswith('#'):
        # strip to not print new line
        return text.strip()

    preprocessed_text = preprocessor.preprocess(text)

    # nothing to interpret?
    if not preprocessed_text:
        return ""

    try:
        result = interpret_dice(preprocessed_text)
        # round and prettyfy
        if isinstance(result, ResultList) or isinstance(result, Distrib):
            if roundlevel:
                for k, v in result.items():
                    result[k] = round(v, roundlevel)
        return result
    except Exception as e:
        # print exception if one happens
        return str(e)

def runinteractive():
    """Get in put from console"""
    preprocessor = Preprocessor()
    while True:
        roundlevel = 2
        text = input("dice> ")
        if text == "exit":
            return 0
        interpret(text, preprocessor, roundlevel)
    return 2

def print_result(result, grepable=False, verbose=False, line=""):
    """Prints result to std out

    grepable = only one line
    verbose = also print command
    line = needed to print command"""

    # send result to stdout
    if grepable:
        if verbose:
            sys.stdout.write("dice> " + line.strip() + " :: " + str(result) + "\n")
        else:
            sys.stdout.write(str(result) + "\n")
    else:
        if verbose:
            sys.stdout.write("dice> " + line + str(result) + "\n")
        else:
            sys.stdout.write(str(result) + "\n")


def main(args):
    # set if output should be grepable
    grepable = False
    verbose = False
    plot = False
    roundlevel = 0
    # remove filename
    args = args[1:]

    # interpret args
    while args:
        if args[0] in ["-i", "--interactive"]:
            return runinteractive()
            args = args[1:]
        elif args[0] in ["-e", "--execute"] and len(args) > 1:
            # HACK: interpret the rest of the args
            # they have to be surrounded by quotation marks
            sys.stdout.write(str(interpret(" ".join(args[1:]), Preprocessor(), roundlevel)) + "\n")
            return 0
        elif args[0] in ["-g", "--grepable"]:
            grepable = True
            args = args[1:]
        elif args[0] in ["-r", "--round"]:
            args = args[1:]
            if args and args[0].isdigit():
                roundlevel = int(args[0])
                args = args[1:]
        elif args[0] in ["-v", "--verbose"]:
            verbose = True
            args = args[1:]
        elif args[0] in ["-p", "--plot"]:
            plot = True
            args = args[1:]
        else:
            # no arg worked break loop
            break

    # no more arguments use fileinput to either interpret the pipe or open a file
    # (if args still has values e.g. a file path)
    input_lines = fileinput.input(args)

    # The preprocessor for all following lines
    # Using this means definitions are shared!
    preprocessor = Preprocessor()

    interpret(''.join(input_lines), preprocessor, roundlevel)

    # for line in input_lines:
    #     # apply definitions:
    #     result = str(interpret(line, preprocessor, roundlevel))

    #     if not result:
    #         continue

    #     if plot:
    #         # plot
    #         viewer.do(result)
    #         if verbose:
    #             # don't print commands just results if verbose and plot
    #             print_result(result, grepable, False)

    #     print_result(result, grepable, verbose, line)
    # exit success
    if plot:
        viewer.show()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
