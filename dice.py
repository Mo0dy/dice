#!/usr/bin/env python3
"""Interactive interpreter for the dice language"""

import argparse
import json
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

try:
    import readline
except ImportError:  # pragma: no cover - platform-specific
    readline = None

from interpreter import Interpreter
from diceengine import Distributions
from diceparser import DiceParser, ParserError
from lexer import Lexer, LexerError
import viewer


timeout_seconds = 5
DEFAULT_ROUNDLEVEL = 2
REPL_HISTORY_LENGTH = 1000


class InteractiveCommandError(Exception):
    """Raised for invalid REPL-only commands."""


def _is_numeric(value):
    return isinstance(value, (int, float))


def _is_deterministic_distribution(distrib):
    items = list(distrib.items())
    return len(items) == 1 and items[0][1] == 1


def _deterministic_outcome(distrib):
    return next(iter(distrib.keys()))


def _all_scalar(result):
    return all(_is_deterministic_distribution(distrib) for distrib in result.cells.values())


def _ordered_labels(values):
    def sort_key(value):
        if isinstance(value, (int, float)):
            return (0, value)
        return (1, str(value))

    return list(sorted(values, key=sort_key))


def _round_numeric(value, roundlevel):
    if roundlevel and isinstance(value, float):
        return round(value, roundlevel)
    return value


def _format_rounded_numeric(value, roundlevel=0):
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not roundlevel:
            return str(value)
        rounded = _round_numeric(value, roundlevel)
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.{roundlevel}f}"
    return str(value)


def _format_scalar(value, roundlevel=0):
    if _is_numeric(value):
        return _format_rounded_numeric(value, roundlevel)
    return str(value)


def _format_label(value, roundlevel=0):
    if _is_numeric(value):
        return _format_rounded_numeric(value, roundlevel)
    return str(value)


def _format_probability(value, roundlevel=0):
    return _format_rounded_numeric(value, roundlevel)


def _axis_header(name):
    return f"/{name}" if name else ""


def _corner_label(row_name, col_name):
    return "{}/{}".format(row_name or "", col_name or "")


def _string_table(rows):
    if not rows:
        return ""
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    return "\n".join(
        "  ".join(cell.rjust(widths[index]) for index, cell in enumerate(row))
        for row in rows
    )


def _format_key_value_lines(entries):
    if not entries:
        return ""
    label_width = max(len(label) for label, _ in entries)
    return "\n".join("{}: {}".format(label.rjust(label_width), value) for label, value in entries)


def _distribution_mean(distrib):
    if _is_deterministic_distribution(distrib):
        return None
    outcomes = list(distrib.keys())
    if not outcomes or not all(_is_numeric(outcome) for outcome in outcomes):
        return None
    return distrib.average()


def _format_unswept_distribution(distrib, roundlevel=0):
    if _is_deterministic_distribution(distrib):
        return _format_scalar(_deterministic_outcome(distrib), roundlevel)
    entries = [
        (_format_label(outcome, roundlevel), _format_probability(distrib[outcome], roundlevel))
        for outcome in _ordered_labels(distrib.keys())
    ]
    mean = _distribution_mean(distrib)
    if mean is not None:
        entries.append(("(E)", _format_scalar(mean, roundlevel)))
    return _format_key_value_lines(entries)


def _format_scalar_sweep(result, roundlevel=0):
    axis = result.axes[0]
    lines = []
    if axis.name:
        lines.append(_axis_header(axis.name))
    lines.append(
        _format_key_value_lines(
            [
                (
                    _format_label(value, roundlevel),
                    _format_scalar(_deterministic_outcome(result.cells[(value,)]), roundlevel),
                )
                for value in axis.values
            ]
        )
    )
    return "\n".join(lines)


def _format_distribution_sweep(result, roundlevel=0):
    axis = result.axes[0]
    outcomes = []
    seen = set()
    means = []
    for axis_value in axis.values:
        distrib = result.cells[(axis_value,)]
        means.append(_distribution_mean(distrib))
        for outcome in _ordered_labels(result.cells[(axis_value,)].keys()):
            if outcome not in seen:
                outcomes.append(outcome)
                seen.add(outcome)

    rows = [[_axis_header(axis.name)] + [_format_label(value, roundlevel) for value in axis.values]]
    for outcome in outcomes:
        rows.append(
            [_format_label(outcome, roundlevel)]
            + [_format_probability(result.cells[(value,)][outcome], roundlevel) for value in axis.values]
        )
    if all(mean is not None for mean in means):
        rows.append(["(E)"] + [_format_scalar(mean, roundlevel) for mean in means])
    return _string_table(rows)


def _format_scalar_heatmap(result, roundlevel=0):
    row_axis, col_axis = result.axes
    rows = [[_corner_label(row_axis.name, col_axis.name)] + [_format_label(value, roundlevel) for value in col_axis.values]]
    for row_value in row_axis.values:
        row = [_format_label(row_value, roundlevel)]
        for col_value in col_axis.values:
            scalar = _deterministic_outcome(result.cells[(row_value, col_value)])
            row.append(_format_scalar(scalar, roundlevel))
        rows.append(row)
    return _string_table(rows)


def _format_result_text(result, roundlevel=0):
    if isinstance(result, Distributions):
        if result.is_unswept():
            return _format_unswept_distribution(result.only_distribution(), roundlevel)
        if len(result.axes) == 1:
            if _all_scalar(result):
                return _format_scalar_sweep(result, roundlevel)
            return _format_distribution_sweep(result, roundlevel)
        if len(result.axes) == 2 and _all_scalar(result):
            return _format_scalar_heatmap(result, roundlevel)
    if isinstance(result, float) and roundlevel:
        return _format_scalar(result, roundlevel)
    return str(result)


def _serialize_distribution(distrib, roundlevel=0):
    entries = []
    for outcome in _ordered_labels(distrib.keys()):
        entries.append(
            {
                "outcome": _round_numeric(outcome, roundlevel) if _is_numeric(outcome) else outcome,
                "probability": _round_numeric(distrib[outcome], roundlevel),
            }
        )
    return entries


def _serialize_result(result, roundlevel=0):
    if isinstance(result, Distributions):
        axes = [
            {
                "key": axis.key,
                "name": axis.name if not axis.name.startswith("sweep_") else None,
                "values": [_round_numeric(value, roundlevel) if _is_numeric(value) else value for value in axis.values],
            }
            for axis in result.axes
        ]
        cells = []
        for coordinates, distrib in result.cells.items():
            coordinate_entries = []
            for axis, value in zip(result.axes, coordinates):
                coordinate_entries.append(
                    {
                        "axis_key": axis.key,
                        "axis_name": axis.name if not axis.name.startswith("sweep_") else None,
                        "value": _round_numeric(value, roundlevel) if _is_numeric(value) else value,
                    }
                )
            cells.append(
                {
                    "coordinates": coordinate_entries,
                    "distribution": _serialize_distribution(distrib, roundlevel),
                }
            )
        return {
            "type": "distributions",
            "axes": axes,
            "cells": cells,
        }
    if isinstance(result, str):
        return {"type": "string", "value": result}
    if _is_numeric(result):
        return {"type": "scalar", "value": _round_numeric(result, roundlevel)}
    return {"type": type(result).__name__, "value": str(result)}


def _format_result_json(result, roundlevel=0):
    return json.dumps(_serialize_result(result, roundlevel), indent=2)


def _history_file_path():
    state_home = os.environ.get("XDG_STATE_HOME")
    if not state_home:
        state_home = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(state_home, "dice", "history")


def _setup_repl_history(readline_module=None):
    readline_module = readline if readline_module is None else readline_module
    if readline_module is None:
        return None
    history_path = _history_file_path()
    try:
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
    except OSError:
        return None
    try:
        readline_module.read_history_file(history_path)
    except (FileNotFoundError, OSError):
        pass
    readline_module.set_history_length(REPL_HISTORY_LENGTH)
    return history_path


def _save_repl_history(history_path, readline_module=None):
    readline_module = readline if readline_module is None else readline_module
    if readline_module is None or history_path is None:
        return
    try:
        readline_module.write_history_file(history_path)
    except OSError:
        pass


def _handle_repl_command(text, state):
    stripped = text.strip()
    if not stripped.startswith("$"):
        return False
    parts = stripped[1:].split()
    if not parts:
        raise InteractiveCommandError("Missing interpreter command")
    if parts[0] == "set_round":
        if len(parts) != 2:
            raise InteractiveCommandError("set_round expects exactly one integer argument")
        try:
            roundlevel = int(parts[1])
        except ValueError as error:
            raise InteractiveCommandError("set_round expects an integer argument") from error
        if roundlevel < 0:
            raise InteractiveCommandError("set_round expects a non-negative integer")
        state["roundlevel"] = roundlevel
        return "round = {}".format(roundlevel)
    raise InteractiveCommandError("Unknown interpreter command {}".format(parts[0]))


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
    state = {"roundlevel": args.roundlevel}
    json_output = getattr(args, "json_output", False)
    history_path = _setup_repl_history()
    try:
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
                command_result = _handle_repl_command(text, state)
                if command_result is not False:
                    if command_result is not None:
                        sys.stdout.write(command_result + "\n")
                    continue
                result = interpret_statement(text, state["roundlevel"], interpreter=interpreter)
            except Exception as error:
                print_interactive_error(error)
                continue
            if result is not None:
                print_result(
                    result,
                    args.grepable,
                    args.verbose,
                    text,
                    json_output=json_output,
                    roundlevel=state["roundlevel"],
                )
    finally:
        _save_repl_history(history_path)
    return 2


def print_result(result, grepable=False, verbose=False, line="", json_output=False, roundlevel=0):
    """Print a result to stdout."""
    rendered = _format_result_json(result, roundlevel) if json_output else _format_result_text(result, roundlevel)
    if grepable:
        rendered = " ".join(rendered.splitlines())

    if verbose:
        if grepable:
            sys.stdout.write("dice> " + line.strip() + " :: " + rendered + "\n")
        else:
            sys.stdout.write("dice> " + line + "\n" + rendered + "\n")
        return
    sys.stdout.write(rendered + "\n")


def main():
    parser = argparse.ArgumentParser(description="Process some inputs.")
    parser.add_argument("-g", "--grepable", action="store_true", help="Enable grepable output")
    parser.add_argument("-R", "--round", "--roundlevel", dest="roundlevel", type=int, default=DEFAULT_ROUNDLEVEL, help="Set rounding level")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("-f", "--file", dest="file", help="Execute a dice source file")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Print structured JSON output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-p", "--plot", action="store_true", help="Enable plotting")
    parser.add_argument("command", nargs="*", help="Command to execute")

    # Parse arguments
    args = parser.parse_args()

    if args.interactive:
        if args.file or args.command:
            parser.error("--interactive cannot be combined with --file or a command")
        return runinteractive(args)

    if args.file:
        if args.command:
            parser.error("--file cannot be combined with a command")
        with open(args.file) as f:
            result = interpret_file(
                f.read(),
                args.roundlevel,
                current_dir=os.path.dirname(os.path.abspath(args.file)),
            )
        if result is not None:
            print_result(
                result,
                args.grepable,
                args.verbose,
                args.file,
                json_output=args.json_output,
                roundlevel=args.roundlevel,
            )
        if args.plot and result is not None:
            render_outcome = viewer.render_result(result)
            if render_outcome.output_path is not None:
                print_result(
                    render_outcome.output_path,
                    args.grepable,
                    args.verbose,
                    args.file,
                    json_output=args.json_output,
                    roundlevel=args.roundlevel,
                )
        return 0

    if not args.command:
        parser.error("expected a dice command, or use --interactive / --file")

    command = " ".join(args.command)
    result = interpret_statement(command, args.roundlevel)
    if result is not None:
        print_result(
            result,
            args.grepable,
            args.verbose,
            command,
            json_output=args.json_output,
            roundlevel=args.roundlevel,
        )
    if args.plot and result is not None:
        render_outcome = viewer.render_result(result)
        if render_outcome.output_path is not None:
            print_result(
                render_outcome.output_path,
                args.grepable,
                args.verbose,
                command,
                json_output=args.json_output,
                roundlevel=args.roundlevel,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
