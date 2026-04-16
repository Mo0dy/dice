#!/usr/bin/env python3


"""The Interpreter for the dice language."""


from difflib import get_close_matches
import inspect
import os

from diagnostics import DiagnosticError, RuntimeError as DiceRuntimeError
from diceparser import DiceParser
from itertools import product

from lexer import Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, PLUS, MINUS, MUL, DIV, RES, ELSE, EOF, COLON, ADV, DIS, ELSEDIV, HIGH, LOW, LBRACK, AVG, PROP, ID, ASSIGN, SEMI, PRINT, STRING, DOT
from diceengine import (
    Sweep,
    Distrib,
    Distributions,
    RenderConfig,
    TRUE,
    FALSE,
    _accumulate_distribution_contributions,
    _coerce_to_distributions,
    _lookup_projected,
    _union_axes,
)
from executor import ExactExecutor


STDLIB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stdlib")


class CallableEntry(object):
    """User-defined callable exposed to dice source."""

    def __init__(self, name, kind, arity=None, variadic=False, function=None, node=None):
        self.name = name
        self.kind = kind
        self.arity = arity
        self.variadic = variadic
        self.function = function
        self.node = node


class Interpreter():
    """Excecutes the dice abstract syntax tree for the dice language"""

    # TODO: should I add typeguards here?
    # The runtime/executor layer still owns most semantic type validation.

    def __init__(
        self,
        ast,
        debug=False,
        executor=None,
        current_dir=None,
        imported_files=None,
        import_stack=None,
        render_config=None,
    ):
        """Works on a pre-generated abstract syntax tree"""
        self.ast = ast
        self.debug = debug
        self.global_scope = {}
        self.callable_scope = {}
        self.local_scopes = []
        self.call_stack = []
        self.render_config = render_config if render_config is not None else RenderConfig()
        self.executor = (
            executor
            if executor is not None
            else ExactExecutor(render_config=self.render_config)
        )
        self.current_dir = os.path.abspath(current_dir if current_dir is not None else os.getcwd())
        self.stdlib_root = os.path.abspath(STDLIB_ROOT)
        self.imported_files = imported_files if imported_files is not None else set()
        self.import_stack = import_stack if import_stack is not None else []
        self._sweep_cache = {}

    def visit(self, node):
        """Calls method with name visit_NodeName for every node visited.
        Does Depthfirst search."""
        method_name = 'visit_' + type(node).__name__
        if self.debug:
            print(f"EXEC: {type(node).__name__}, {node.token.type}")
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Gets calles if no proper visit methods exists"""
        raise DiceRuntimeError("internal error: no visit_{} method".format(type(node).__name__))

    def interpret(self):
        """Interprets AST (start by visiting ast node)"""
        return self.evaluate(self.ast)

    def evaluate(self, ast):
        self.collect_function_definitions(ast)
        return self.visit(ast)

    def collect_function_definitions(self, node):
        if node is None:
            return
        if type(node).__name__ == "FunctionDef":
            self.register_function_definition(node)
            return
        if type(node).__name__ == "VarOp" and node.op.type == SEMI:
            for child in node.nodes:
                if type(child).__name__ == "FunctionDef":
                    self.register_function_definition(child)

    def _register_callable(self, entry):
        if entry.name in self.callable_scope:
            self.exception(
                "Duplicate function definition for {}".format(entry.name),
                node=entry.node,
                hint="Rename one of the functions or remove the duplicate definition.",
            )
        if entry.name in self.executor.functions:
            self.exception(
                "Duplicate function definition for {}".format(entry.name),
                node=entry.node,
                hint="Builtins and user-defined functions share the same namespace.",
            )
        self.callable_scope[entry.name] = entry

    def register_function_definition(self, node):
        self._register_callable(
            CallableEntry(node.name.value, "dsl", arity=len(node.params), node=node)
        )

    def register_function(self, function, name=None):
        callable_name = name if name is not None else function.__name__
        if not callable_name:
            self.exception("python functions must have a name")
        if callable_name in self.callable_scope or callable_name in self.executor.functions:
            self.exception("Duplicate function definition for {}".format(callable_name))
        self.executor.register_function(function, name=callable_name)
        return function

    def _node_span(self, node):
        if node is None:
            return None
        token = getattr(node, "token", None)
        if token is None:
            token = getattr(node, "token1", None)
        if token is None:
            return None
        return getattr(token, "span", None)

    def _raise_or_enrich(self, error, node=None, hint=None):
        span = self._node_span(self._best_error_node(error, node))
        if isinstance(error, DiagnosticError):
            raise error.attach_span(span).attach_hint(hint)
        raise DiceRuntimeError(str(error), span=span, hint=hint)

    def _with_runtime_context(self, node, function):
        try:
            return function()
        except Exception as error:
            self._raise_or_enrich(error, node=node)

    def _suggest_name(self, name, candidates):
        matches = get_close_matches(name, sorted(candidates), n=1, cutoff=0.6)
        if matches:
            return matches[0]
        return None

    def _value_candidates(self):
        candidates = set(self.global_scope.keys())
        for scope in self.local_scopes:
            candidates.update(scope.keys())
        return candidates

    def _function_candidates(self):
        return set(self.callable_scope) | set(self.executor.functions)

    def _identifier_hint(self, name, *, prefer_call=False):
        function_candidates = self._function_candidates()
        value_candidates = self._value_candidates()

        if not prefer_call and name in function_candidates:
            return "{} is a function. Did you mean {}(...)?".format(name, name)
        if prefer_call and name in value_candidates:
            return "{} is a variable, not a function.".format(name)

        function_match = self._suggest_name(name, function_candidates)
        value_match = self._suggest_name(name, value_candidates)

        if prefer_call and function_match:
            return "Did you mean {}?".format(function_match)
        if not prefer_call and value_match:
            return "Did you mean {}?".format(value_match)
        if not prefer_call and function_match:
            return "Did you mean {}?".format(function_match)
        if prefer_call and value_match:
            return "Did you mean {}?".format(value_match)
        return None

    def _call_hint(self, entry):
        if entry.variadic:
            return None
        if getattr(entry, "kind", None) == "dsl":
            params = [param.value for param in entry.node.params]
        else:
            try:
                signature = inspect.signature(entry.function)
                params = [
                    parameter.name
                    for parameter in signature.parameters.values()
                    if parameter.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]
            except (TypeError, ValueError):
                params = []
            if not params:
                params = ["arg{}".format(index + 1) for index in range(entry.arity)]
        return "Call it like {}({}).".format(entry.name, ", ".join(params))

    def _literal_scalar_from_node(self, node):
        if type(node).__name__ == "Val" and node.token.type in [INTEGER, STRING]:
            return node.value
        return None

    def _best_roll_node(self, left_node, right_node):
        left_value = self._literal_scalar_from_node(left_node)
        right_value = self._literal_scalar_from_node(right_node)
        if right_value is not None and (not isinstance(right_value, int) or right_value <= 0):
            return right_node
        if left_value is not None and (not isinstance(left_value, int) or left_value < 0):
            return left_node
        return None

    def _best_keep_node(self, count_node, sides_node, keep_node):
        count_value = self._literal_scalar_from_node(count_node)
        sides_value = self._literal_scalar_from_node(sides_node)
        keep_value = self._literal_scalar_from_node(keep_node)
        if keep_value is not None and (
            not isinstance(keep_value, int)
            or keep_value < 0
            or (isinstance(count_value, int) and keep_value > count_value)
        ):
            return keep_node
        if sides_value is not None and (not isinstance(sides_value, int) or sides_value <= 0):
            return sides_node
        if count_value is not None and (not isinstance(count_value, int) or count_value < 0):
            return count_node
        return None

    def _best_error_node(self, error, node):
        if node is None:
            return None
        message = str(error).lower()
        node_type = type(node).__name__
        if node_type == "BinOp":
            if node.op.type == DIV and "divide by zero" in message:
                return node.right
            if node.op.type == ROLL and (
                "positive sides" in message
                or "integer outcomes" in message
            ):
                return self._best_roll_node(node.left, node.right) or node
        if node_type == "TenOp" and node.op1.type == ROLL and node.op2.type in [HIGH, LOW]:
            if "keep count" in message or "positive sides" in message or "integer outcomes" in message:
                return self._best_keep_node(node.left, node.middle, node.right) or node
        return node

    def _unknown_name_hint(self, name):
        return self._identifier_hint(name, prefer_call=False)

    def exception(self, message="", node=None, hint=None):
        """Raises an exception for the Interpreter"""
        raise DiceRuntimeError(message, span=self._node_span(node), hint=hint)

    def _resolve_import_path(self, import_path):
        if import_path.startswith("std:"):
            stdlib_path = import_path[len("std:"):].lstrip("/\\")
            if not stdlib_path:
                self.exception(
                    "Could not import {!r}".format(import_path),
                    hint='Use a stdlib path like "std:dnd/weapons.dice".',
                )
            resolved_path = os.path.abspath(os.path.join(self.stdlib_root, stdlib_path))
            if os.path.commonpath([self.stdlib_root, resolved_path]) != self.stdlib_root:
                self.exception(
                    "Could not import {!r}".format(import_path),
                    hint="Stdlib imports must stay inside the stdlib directory.",
                )
            return resolved_path

        if os.path.isabs(import_path):
            return os.path.abspath(import_path)

        return os.path.abspath(os.path.join(self.current_dir, import_path))

    def _validate_runtime_value(self, value):
        if value is None:
            return value
        if isinstance(value, (int, float, str, Sweep, Distrib, Distributions)):
            return value
        self.exception("Unsupported host value type {}".format(type(value)))

    def _bool_masses(self, condition, node=None):
        invalid = [outcome for outcome in condition.keys() if outcome not in (TRUE, FALSE)]
        if invalid:
            self.exception(
                "match guards must evaluate to booleans, got {}".format(invalid),
                node=node,
                hint="Use a comparison like 'roll >= 15' in each guard.",
            )
        return condition[TRUE], condition[FALSE]

    def _check_call_arity(self, entry, call_arity, node=None):
        if entry.variadic:
            return
        if call_arity != entry.arity:
            self.exception(
                "function {} expected {} arguments but got {}".format(
                    entry.name,
                    entry.arity,
                    call_arity,
                ),
                node=node,
                hint=self._call_hint(entry),
            )

    def _call_dsl_function(self, entry, values):
        function = entry.node
        if entry.name in self.call_stack:
            self.exception(
                "Recursion not supported for {}".format(entry.name),
                node=function,
                hint="Rewrite the function using a closed-form expression or a builtin helper.",
            )

        local_scope = {param.value: value for param, value in zip(function.params, values)}
        self.call_stack.append(entry.name)
        self.local_scopes.append(local_scope)
        try:
            return self.visit(function.body)
        finally:
            self.local_scopes.pop()
            self.call_stack.pop()

    def _call_host_function(self, entry, values):
        try:
            return self._validate_runtime_value(entry.function(*values))
        except Exception as error:
            self._raise_or_enrich(
                error,
                hint="The host function {} could not evaluate these arguments.".format(entry.name),
            )

    def _parse_imported_source(self, resolved_path):
        with open(resolved_path, encoding="utf-8") as handle:
            text = handle.read()
        return DiceParser(Lexer(text, source_name=resolved_path)).parse()

    def visit_VarOp(self, node):
        """Visits a Variary-Operation node"""
        if node.op.type == SEMI:
            last_result = None
            for n in node.nodes:
                if type(n).__name__ == "FunctionDef":
                    continue
                last_result = self.visit(n)
            return last_result

        elif node.op.type == LBRACK:
            values = []
            for child in node.nodes:
                new_val = self.visit(child)
                if type(new_val) not in [int, str]:
                    self.exception(
                        "sweep construction expects scalar values, got {}".format(type(new_val)),
                        node=child,
                        hint="Use plain integers or strings inside [...].",
                    )
                values.append(new_val)
            cache_key = tuple(values)
            if not hasattr(self, "_sweep_cache"):
                self._sweep_cache = {}
            if id(node) not in self._sweep_cache:
                self._sweep_cache[id(node)] = {}
            if cache_key not in self._sweep_cache[id(node)]:
                self._sweep_cache[id(node)][cache_key] = Sweep(values)
            return self._sweep_cache[id(node)][cache_key]

        self.exception("{} not implemented".format(node), node=node)

    def visit_FunctionDef(self, node):
        return

    def visit_Import(self, node):
        import_path = node.path.value
        resolved_path = self._resolve_import_path(import_path)

        if resolved_path in self.import_stack:
            cycle = " -> ".join(self.import_stack + [resolved_path])
            self.exception(
                "Import cycle detected: {}".format(cycle),
                node=node,
                hint="Remove one of the circular imports or move shared definitions into a third file.",
            )

        if resolved_path in self.imported_files:
            return

        if not os.path.isfile(resolved_path):
            self.exception(
                "Could not import {!r}".format(import_path),
                node=node.path,
                hint="Check that the file exists and that the path is relative to the importing file.",
            )

        ast = self._parse_imported_source(resolved_path)

        self.imported_files.add(resolved_path)
        self.import_stack.append(resolved_path)
        previous_dir = self.current_dir
        self.current_dir = os.path.dirname(resolved_path)
        try:
            return self.evaluate(ast)
        finally:
            self.current_dir = previous_dir
            self.import_stack.pop()

    def visit_Named(self, node):
        value = self.visit(node.value)
        if not isinstance(value, Sweep):
            self.exception(
                "named brackets require a sweep value",
                node=node,
                hint="Use a sweep expression like [AC:10:15] or [AC:10, 12, 14].",
            )

        cache_key = (id(node), value.values, node.name.value)
        if cache_key not in self._sweep_cache:
            self._sweep_cache[cache_key] = Sweep(value.values, name=node.name.value)
        return self._sweep_cache[cache_key]

    def visit_Call(self, node):
        function_name = node.name.value
        if function_name in self.callable_scope:
            entry = self.callable_scope[function_name]
            self._check_call_arity(entry, len(node.args), node=node)
            values = [self.visit(arg) for arg in node.args]
            return self._with_runtime_context(node, lambda: self._call_dsl_function(entry, values))
        if function_name not in self.executor.functions:
            self.exception(
                "Unknown function {}".format(function_name),
                node=node,
                hint=self._identifier_hint(function_name, prefer_call=True),
            )

        entry = self.executor.functions[function_name]
        self._check_call_arity(entry, len(node.args), node=node)
        values = [self.visit(arg) for arg in node.args]
        return self._with_runtime_context(node, lambda: self._call_host_function(entry, values))

    def visit_Match(self, node):
        matched_value = _coerce_to_distributions(self.visit(node.value))
        contributions = []

        for matched_coordinates, matched_distrib in matched_value.cells.items():
            for outcome, outcome_probability in matched_distrib.items():
                if outcome_probability == 0:
                    continue

                local_scope = {node.name.value: outcome}
                self.local_scopes.append(local_scope)
                try:
                    remaining_axes = matched_value.axes
                    remaining_cells = {matched_coordinates: 1}

                    for clause in node.clauses:
                        if clause.otherwise:
                            result_value = _coerce_to_distributions(self.visit(clause.result))
                            clause_axes = _union_axes([Distributions(remaining_axes, {coord: Distrib({mass: 1}) for coord, mass in remaining_cells.items()}), result_value])
                            coordinates_space = [()] if not clause_axes else product(*(axis.values for axis in clause_axes))
                            clause_cells = {}
                            for coordinates in coordinates_space:
                                remaining_mass = _lookup_projected(remaining_axes, remaining_cells, clause_axes, coordinates, 0)
                                if remaining_mass == 0:
                                    continue
                                result_distrib = result_value.lookup(clause_axes, coordinates)
                                weighted = Distrib()
                                for result_outcome, result_probability in result_distrib.items():
                                    weighted[result_outcome] = outcome_probability * remaining_mass * result_probability
                                clause_cells[coordinates] = weighted
                            contributions.append((clause_axes, clause_cells))
                            remaining_cells = {}
                            break

                        condition_value = _coerce_to_distributions(self.visit(clause.condition))
                        result_value = _coerce_to_distributions(self.visit(clause.result))
                        clause_axes = _union_axes([
                            Distributions(remaining_axes, {coord: Distrib({mass: 1}) for coord, mass in remaining_cells.items()}),
                            condition_value,
                            result_value,
                        ])
                        coordinates_space = [()] if not clause_axes else product(*(axis.values for axis in clause_axes))
                        clause_cells = {}
                        next_remaining = {}
                        for coordinates in coordinates_space:
                            remaining_mass = _lookup_projected(remaining_axes, remaining_cells, clause_axes, coordinates, 0)
                            if remaining_mass == 0:
                                continue
                            condition_distrib = condition_value.lookup(clause_axes, coordinates)
                            true_mass, false_mass = self._bool_masses(condition_distrib, node=clause.condition)
                            matched_mass = remaining_mass * true_mass
                            if matched_mass:
                                result_distrib = result_value.lookup(clause_axes, coordinates)
                                weighted = Distrib()
                                for result_outcome, result_probability in result_distrib.items():
                                    weighted[result_outcome] = outcome_probability * matched_mass * result_probability
                                clause_cells[coordinates] = weighted
                            next_mass = remaining_mass * false_mass
                            if next_mass:
                                next_remaining[coordinates] = next_mass
                        contributions.append((clause_axes, clause_cells))
                        remaining_axes = clause_axes
                        remaining_cells = next_remaining

                    if any(mass for mass in remaining_cells.values()):
                        self.exception(
                            "match expression left unmatched cases for {}".format(node.name.value),
                            node=node,
                            hint="Add an 'otherwise' clause to cover the remaining cases.",
                        )
                finally:
                    self.local_scopes.pop()

        return _accumulate_distribution_contributions(contributions)

    def visit_TenOp(self, node):
        """Visit a Tenary-Operator node"""
        if node.op1.type == RES and node.op2.type == ELSE:
            return self._with_runtime_context(
                node,
                lambda: self.executor.reselse(self.visit(node.left), self.visit(node.middle), self.visit(node.right)),
            )
        elif node.op1.type == ROLL and node.op2.type == HIGH:
            return self._with_runtime_context(
                node,
                lambda: self.executor.rollhigh(self.visit(node.left), self.visit(node.middle), self.visit(node.right)),
            )
        elif node.op1.type == ROLL and node.op2.type == LOW:
            return self._with_runtime_context(
                node,
                lambda: self.executor.rolllow(self.visit(node.left), self.visit(node.middle), self.visit(node.right)),
            )
        self.exception("{} not implemented".format(node), node=node)

    def visit_BinOp(self, node):
        """Visit a Binary-Operator node"""

        if node.op.type == PLUS:
            return self._with_runtime_context(node, lambda: self.executor.add(self.visit(node.left), self.visit(node.right)))
        if node.op.type == MINUS:
            return self._with_runtime_context(node, lambda: self.executor.sub(self.visit(node.left), self.visit(node.right)))
        if node.op.type == MUL:
            return self._with_runtime_context(node, lambda: self.executor.mul(self.visit(node.left), self.visit(node.right)))
        if node.op.type == DIV:
            return self._with_runtime_context(node, lambda: self.executor.div(self.visit(node.left), self.visit(node.right)))
        if node.op.type == ROLL:
            return self._with_runtime_context(node, lambda: self.executor.roll(self.visit(node.left), self.visit(node.right)))
        if node.op.type == GREATER_OR_EQUAL:
            return self._with_runtime_context(node, lambda: self.executor.greaterorequal(self.visit(node.left), self.visit(node.right)))
        if node.op.type == LESS_OR_EQUAL:
            return self._with_runtime_context(node, lambda: self.executor.lessorequal(self.visit(node.left), self.visit(node.right)))
        if node.op.type == GREATER:
            return self._with_runtime_context(node, lambda: self.executor.greater(self.visit(node.left), self.visit(node.right)))
        if node.op.type == LESS:
            return self._with_runtime_context(node, lambda: self.executor.less(self.visit(node.left), self.visit(node.right)))
        if node.op.type == EQUAL:
            return self._with_runtime_context(node, lambda: self.executor.equal(self.visit(node.left), self.visit(node.right)))
        if node.op.type == RES:
            return self._with_runtime_context(node, lambda: self.executor.res(self.visit(node.left), self.visit(node.right)))
        if node.op.type == ELSEDIV:
            return self._with_runtime_context(node, lambda: self.executor.reselsediv(self.visit(node.left), self.visit(node.right)))
        if node.op.type == COLON:
            # generate a sweep ranging value1 to value2 of integers
            val1 = self.visit(node.left)
            if type(val1) != int:
                self.exception(
                    "expected an integer range start, got {}".format(type(val1)),
                    node=node.left,
                    hint="Range sweeps look like [1:6] or [AC:10:15].",
                )
            val2 = self.visit(node.right)
            if type(val2) != int:
                self.exception(
                    "expected an integer range end, got {}".format(type(val2)),
                    node=node.right,
                    hint="Range sweeps look like [1:6] or [AC:10:15].",
                )
            cache_key = (val1, val2)
            if not hasattr(self, "_sweep_cache"):
                self._sweep_cache = {}
            if id(node) not in self._sweep_cache:
                self._sweep_cache[id(node)] = {}
            if cache_key not in self._sweep_cache[id(node)]:
                self._sweep_cache[id(node)][cache_key] = Sweep(range(val1, val2 + 1))
            return self._sweep_cache[id(node)][cache_key]
        if node.op.type == LBRACK:
            return self._with_runtime_context(node, lambda: self.executor.choose(self.visit(node.left), self.visit(node.right)))
        if node.op.type == DOT:
            return self._with_runtime_context(node, lambda: self.executor.choose_single(self.visit(node.left), self.visit(node.right)))
        if node.op.type == ASSIGN:
            self.global_scope[node.left.value] = self.visit(node.right)
            return

        self.exception("{} not implemented".format(node), node=node)

    def visit_UnOp(self, node):
        """Visits a Unary-Operator node"""
        if node.op.type == ROLL:
            return self._with_runtime_context(node, lambda: self.executor.rollsingle(self.visit(node.value)))
        elif node.op.type == ADV:
            return self._with_runtime_context(node, lambda: self.executor.rolladvantage(self.visit(node.value)))
        elif node.op.type == DIS:
            return self._with_runtime_context(node, lambda: self.executor.rolldisadvantage(self.visit(node.value)))
        elif node.op.type == RES:
            return self._with_runtime_context(node, lambda: self.executor.mean(self.visit(node.value)))
        elif node.op.type == AVG:
            return self._with_runtime_context(node, lambda: self.executor.mean(self.visit(node.value)))
        elif node.op.type == PROP:
            return self._with_runtime_context(node, lambda: self.executor.sample(self.visit(node.value)))
        elif node.op.type == PRINT:
            print(self.visit(node.value))
            return
        self.exception("{} not implemented".format(node), node=node)

    def visit_Val(self, node):
        """Visits a Value node"""
        if node.token.type in [INTEGER, STRING]:
            return node.value

        for scope in reversed(self.local_scopes):
            if node.value in scope:
                return scope[node.value]

        if not node.value in self.global_scope:
            self.exception(
                "unknown name {}".format(node.value),
                node=node,
                hint=self._unknown_name_hint(node.value),
            )
        return self.global_scope[node.value]

if __name__ == "__main__":
    input_text = 'a = d20; print a; render(a)'
    ast = DiceParser(Lexer(input_text)).parse()
    print(ast)
    interpreter = Interpreter(ast)
    result = interpreter.interpret()
