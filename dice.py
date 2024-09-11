#!/usr/bin/env python3
"""Interactive interpreter for the dice language"""

import argparse
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

@timeout_decorator.timeout(timeout_seconds)
def interpret_statement(text, roundlevel=0, print_result=False, show_result=False):
    result = Interpreter(DiceParser(Lexer(text)).statement()).interpret()
    if print_result:
        print(result)
    if show_result:
        viewer.do(result)


@timeout_decorator.timeout(timeout_seconds)
def interpret_file(text, preprocessor, roundlevel=0):
    """Interprete command and return output"""
    # print statement
    if text.startswith('#'):
        # strip to not print new line
        return text.strip()

    # TODO: remove define
    preprocessed_text = preprocessor.preprocess(text)

    # nothing to interpret?
    if not preprocessed_text:
        return ""

    result = Interpreter(DiceParser(Lexer(preprocessed_text)).parse()).interpret()
    # round and prettyfy
    if isinstance(result, ResultList) or isinstance(result, Distrib):
        if roundlevel:
            for k, v in result.items():
                result[k] = round(v, roundlevel)
    return result

def runinteractive():
    """Get in put from console"""
    preprocessor = Preprocessor()
    while True:
        roundlevel = 2
        text = input("dice> ")
        if text == "exit":
            return 0
        interpret_file(text, preprocessor, roundlevel)
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


def main():
    parser = argparse.ArgumentParser(description="Process some inputs.")

    # Define subparsers for different modes (interactive, execute, default)
    subparsers = parser.add_subparsers(dest='mode', required=True, help="Modes of operation")

    # Subparser for interactive mode
    parser_interactive = subparsers.add_parser('interactive', help="Run in interactive mode")

    # Subparser for execute mode
    parser_execute = subparsers.add_parser('execute', help="Execute the following command")
    parser_execute.add_argument('command', type=str, help="Command to execute")

    parser_exec_file = subparsers.add_parser("file", help="Execute the file given.")
    parser_exec_file.add_argument('file', type=str, help="The file to execute.")

    parser.add_argument("-g", "--grepable", action="store_true", help="Enable grepable output")
    parser.add_argument("-r", "--roundlevel", type=int, default=0, help="Set rounding level")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-p", "--plot", action="store_true", help="Enable plotting")
    parser.add_argument('files', nargs='*', help="Files to process (or stdin if empty)")

    # Parse arguments
    args = parser.parse_args()

    # Handle modes
    if args.mode == 'interactive':
        return runinteractive()

    elif args.mode == 'execute':
        interpret_statement(args.command, args.roundlevel, args.verbose, args.plot)
        return 0
    elif args.mode == 'file':
        with open(args.file) as f:
            interpret_file(f.read(), Preprocessor(), args.roundlevel)
    return 0

if __name__ == "__main__":
    sys.exit(main())
