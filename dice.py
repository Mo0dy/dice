#!/usr/bin/env python3
"""Interactive interpreter for the dice language"""

import argparse
import os
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
from diceengine import Distributions
from diceparser import DiceParser, ParserError
from lexer import Lexer, LexerError
import viewer


timeout_seconds = 5

def _round_result(result, roundlevel=0):
    if roundlevel and isinstance(result, Distributions):
        result.round_probabilities(roundlevel)
    return result


def _interpret_ast(ast, roundlevel=0, engine=None, interpreter=None, current_dir=None):
    if interpreter is None:
        interpreter = Interpreter(ast, engine=engine, current_dir=current_dir)
    else:
        interpreter.ast = ast
        if current_dir is not None:
            interpreter.current_dir = os.path.abspath(current_dir)
    result = interpreter.interpret()
    return _round_result(result, roundlevel)

@timeout_decorator.timeout(timeout_seconds)
def interpret_statement(text, roundlevel=0, engine=None, interpreter=None, current_dir=None):
    parser = DiceParser(Lexer(text))
    ast = parser.parse() if (";" in text or "\n" in text) else parser.statement()
    return _interpret_ast(ast, roundlevel, engine=engine, interpreter=interpreter, current_dir=current_dir)

@timeout_decorator.timeout(timeout_seconds)
def interpret_file(text, roundlevel=0, engine=None, interpreter=None, current_dir=None):
    """Interpret a semicolon or newline separated program."""
    return _interpret_ast(
        DiceParser(Lexer(text)).parse(),
        roundlevel,
        engine=engine,
        interpreter=interpreter,
        current_dir=current_dir,
    )


class DiceSession(object):
    """Stateful Python-facing wrapper around the dice interpreter."""

    def __init__(self, roundlevel=0, engine=None, current_dir=None):
        self.roundlevel = roundlevel
        self.current_dir = os.path.abspath(current_dir if current_dir is not None else os.getcwd())
        self.interpreter = Interpreter(None, engine=engine, current_dir=self.current_dir)

    def __call__(self, text, current_dir=None):
        call_dir = self.current_dir if current_dir is None else os.path.abspath(current_dir)
        return interpret_statement(
            text,
            roundlevel=self.roundlevel,
            interpreter=self.interpreter,
            current_dir=call_dir,
        )

    def assign(self, name, value):
        if value is None:
            self.interpreter.exception("Unsupported host value type {}".format(type(value)))
        self.interpreter._validate_runtime_value(value)
        self.interpreter.global_scope[name] = value
        return value

    def register_function(self, function, name=None):
        return self.interpreter.register_function(function, name=name)


def dice_interpreter(roundlevel=0, current_dir=None, engine=None):
    return DiceSession(roundlevel=roundlevel, current_dir=current_dir, engine=engine)

def print_interactive_error(error):
    """Print a user-facing REPL error without a traceback."""
    prefix = "syntax error" if isinstance(error, (ParserError, LexerError)) else "error"
    sys.stderr.write("{}: {}\n".format(prefix, error))

def runinteractive(args):
    """Run a simple interactive shell."""
    interpreter = Interpreter(None, current_dir=os.getcwd())
    while True:
        try:
            text = input("dice> ")
        except EOFError:
            return 0
        except KeyboardInterrupt:
            sys.stderr.write("\n")
            continue
        if text == "exit":
            return 0
        if not text.strip():
            continue
        try:
            result = interpret_statement(text, args.roundlevel, interpreter=interpreter)
        except Exception as error:
            print_interactive_error(error)
            continue
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
            render_outcome = viewer.render_result(result)
            if render_outcome.output_path is not None:
                print_result(render_outcome.output_path, args.grepable, args.verbose, args.command)
        return 0
    elif args.mode == 'file':
        with open(args.file) as f:
            result = interpret_file(
                f.read(),
                args.roundlevel,
                current_dir=os.path.dirname(os.path.abspath(args.file)),
            )
        if result is not None:
            print_result(result, args.grepable, args.verbose, args.file)
    return 0

if __name__ == "__main__":
    sys.exit(main())
