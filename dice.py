#!/usr/bin/env python3
"""Interactive interpreter for the dice language"""

import argparse
import sys

try:
    import timeout_decorator
except ImportError:
    class _TimeoutFallback(object):
        @staticmethod
        def timeout(_seconds):
            def decorator(function):
                return function
            return decorator

    timeout_decorator = _TimeoutFallback()

from interpreter import Interpreter
from diceengine import ResultList, Distrib
from diceparser import DiceParser
from lexer import Lexer
import viewer


timeout_seconds = 5

def _round_result(result, roundlevel=0):
    if roundlevel and isinstance(result, (ResultList, Distrib)):
        for key, value in result.items():
            result[key] = round(value, roundlevel)
    return result

@timeout_decorator.timeout(timeout_seconds)
def interpret_statement(text, roundlevel=0):
    result = Interpreter(DiceParser(Lexer(text)).statement()).interpret()
    return _round_result(result, roundlevel)

@timeout_decorator.timeout(timeout_seconds)
def interpret_file(text, roundlevel=0):
    """Interpret a semicolon or newline separated program."""
    result = Interpreter(DiceParser(Lexer(text)).parse()).interpret()
    return _round_result(result, roundlevel)

def runinteractive(args):
    """Run a simple interactive shell."""
    while True:
        text = input("dice> ")
        if text == "exit":
            return 0
        if not text.strip():
            continue
        result = interpret_statement(text, args.roundlevel)
        if result is not None:
            print_result(result, args.grepable, args.verbose, text)
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
        return runinteractive(args)

    elif args.mode == 'execute':
        result = interpret_statement(args.command, args.roundlevel)
        if result is not None:
            print_result(result, args.grepable, args.verbose, args.command)
        if args.plot and result is not None:
            viewer.do(str(result))
            viewer.show()
        return 0
    elif args.mode == 'file':
        with open(args.file) as f:
            result = interpret_file(f.read(), args.roundlevel)
        if result is not None:
            print_result(result, args.grepable, args.verbose, args.file)
    return 0

if __name__ == "__main__":
    sys.exit(main())
