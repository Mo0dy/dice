#!/usr/bin/env python3


"""The Interpreter for the dice language."""


import inspect
import os

from diceparser import DiceParser
from itertools import product

from lexer import Lexer, INTEGER, ROLL, GREATER_OR_EQUAL, LESS_OR_EQUAL, LESS, GREATER, EQUAL, PLUS, MINUS, MUL, DIV, RES, ELSE, EOF, COLON, ADV, DIS, ELSEDIV, HIGH, LOW, LBRACK, AVG, PROP, ID, ASSIGN, SEMI, PRINT, STRING, DOT
from diceengine import Diceengine, Sweep, Distrib, Distributions, TRUE, FALSE, _coerce_to_distributions, _union_axes
from standard_library import register_standard_library


class CallableEntry(object):
    """Registered callable exposed to dice source."""

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
    # At the moment the Diceengine does it's own typeguards so maybe thats ok
    # It feels like that should be a language Feature also but idk
    # Interpreter.py and Diceengine.py have a lot of dependencies anyways

    def __init__(self, ast, debug=False, engine=None, current_dir=None, imported_files=None, import_stack=None):
        """Works on a pre-generated abstract syntax tree"""
        self.ast = ast
        self.debug = debug
        self.global_scope = {}
        self.callable_scope = {}
        self.local_scopes = []
        self.call_stack = []
        self.engine = engine if engine is not None else Diceengine
        self.current_dir = os.path.abspath(current_dir if current_dir is not None else os.getcwd())
        self.imported_files = imported_files if imported_files is not None else set()
        self.import_stack = import_stack if import_stack is not None else []
        self._sweep_cache = {}
        self._register_builtin_functions()

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
        raise Exception('No visit_{} method'.format(type(node).__name__))

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
            self.exception("Duplicate function definition for {}".format(entry.name))
        self.callable_scope[entry.name] = entry

    def _register_builtin_functions(self):
        register_standard_library(self, CallableEntry)

    def register_function_definition(self, node):
        self._register_callable(
            CallableEntry(node.name.value, "dsl", arity=len(node.params), node=node)
        )

    def _callable_arity(self, function):
        signature = inspect.signature(function)
        arity = 0
        for parameter in signature.parameters.values():
            if parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                self.exception("Python functions only support fixed positional arguments")
            if parameter.default is not inspect._empty:
                self.exception("Python functions only support fixed positional arguments")
            arity += 1
        return arity

    def register_function(self, function, name=None):
        callable_name = name if name is not None else function.__name__
        if not callable_name:
            self.exception("Python functions must have a name")
        arity = self._callable_arity(function)
        self._register_callable(CallableEntry(callable_name, "host", arity=arity, function=function))
        return function

    def exception(self, message=""):
        """Raises an exception for the Interpreter"""
        raise Exception("Interpreter exception: {}".format(message))

    def _validate_runtime_value(self, value):
        if value is None:
            return value
        if isinstance(value, (int, float, str, Sweep, Distrib, Distributions)):
            return value
        self.exception("Unsupported host value type {}".format(type(value)))

    def _lookup_projected(self, axes, cells, combined_axes, coordinates, default):
        if not axes:
            return cells.get((), default)
        index_by_key = {axis.key: idx for idx, axis in enumerate(combined_axes)}
        local_coordinates = tuple(coordinates[index_by_key[axis.key]] for axis in axes)
        return cells.get(local_coordinates, default)

    def _fixed_axis_distribution(self, axes, coordinates):
        return Distributions(axes, {coordinates: Distrib({0: 1})})

    def _accumulate_distribution_contributions(self, contributions):
        combined_axes = _union_axes([Distributions(axes, cells) for axes, cells in contributions]) if contributions else ()
        coordinates_space = [()] if not combined_axes else product(*(axis.values for axis in combined_axes))
        cells = {}
        for coordinates in coordinates_space:
            distrib = Distrib()
            for axes, contribution_cells in contributions:
                projected = self._lookup_projected(axes, contribution_cells, combined_axes, coordinates, None)
                if not projected:
                    continue
                for outcome, probability in projected.items():
                    distrib[outcome] = distrib[outcome] + probability
            cells[coordinates] = distrib
        return Distributions(combined_axes, cells if cells else {(): Distrib()})

    def _bool_masses(self, condition):
        invalid = [outcome for outcome in condition.keys() if outcome not in (TRUE, FALSE)]
        if invalid:
            self.exception("Match guards expect boolean outcomes, got {}".format(invalid))
        return condition[TRUE], condition[FALSE]

    def _check_call_arity(self, entry, call_arity):
        if entry.variadic:
            return
        if call_arity != entry.arity:
            self.exception(
                "Function {} expected {} arguments but got {}".format(
                    entry.name,
                    entry.arity,
                    call_arity,
                )
            )

    def _call_dsl_function(self, entry, values):
        function = entry.node
        if entry.name in self.call_stack:
            self.exception("Recursion not supported for {}".format(entry.name))

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
            if str(error).startswith("Interpreter exception:"):
                raise
            self.exception("Function {} failed: {}".format(entry.name, error))

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
                    self.exception("Constructing sweep expected scalar got: {}".format(type(new_val)))
                values.append(new_val)
            cache_key = tuple(values)
            if not hasattr(self, "_sweep_cache"):
                self._sweep_cache = {}
            if id(node) not in self._sweep_cache:
                self._sweep_cache[id(node)] = {}
            if cache_key not in self._sweep_cache[id(node)]:
                self._sweep_cache[id(node)][cache_key] = Sweep(values)
            return self._sweep_cache[id(node)][cache_key]

        self.exception("{} not implemented".format(node))

    def visit_FunctionDef(self, node):
        return

    def visit_Import(self, node):
        import_path = node.path.value
        resolved_path = os.path.abspath(os.path.join(self.current_dir, import_path))

        if resolved_path in self.import_stack:
            cycle = " -> ".join(self.import_stack + [resolved_path])
            self.exception("Import cycle detected: {}".format(cycle))

        if resolved_path in self.imported_files:
            return

        if not os.path.isfile(resolved_path):
            self.exception("Could not import {}".format(import_path))

        with open(resolved_path, encoding="utf-8") as handle:
            ast = DiceParser(Lexer(handle.read())).parse()

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
            self.exception("Named brackets require a sweep value")

        cache_key = (id(node), value.values, node.name.value)
        if cache_key not in self._sweep_cache:
            self._sweep_cache[cache_key] = Sweep(value.values, name=node.name.value)
        return self._sweep_cache[cache_key]

    def visit_Call(self, node):
        function_name = node.name.value
        if function_name not in self.callable_scope:
            self.exception("Unknown function {}".format(function_name))

        entry = self.callable_scope[function_name]
        self._check_call_arity(entry, len(node.args))
        values = [self.visit(arg) for arg in node.args]
        if entry.kind == "dsl":
            return self._call_dsl_function(entry, values)
        return self._call_host_function(entry, values)

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
                                remaining_mass = self._lookup_projected(remaining_axes, remaining_cells, clause_axes, coordinates, 0)
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
                            remaining_mass = self._lookup_projected(remaining_axes, remaining_cells, clause_axes, coordinates, 0)
                            if remaining_mass == 0:
                                continue
                            condition_distrib = condition_value.lookup(clause_axes, coordinates)
                            true_mass, false_mass = self._bool_masses(condition_distrib)
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
                        self.exception("Match expression left unmatched cases for {}".format(node.name.value))
                finally:
                    self.local_scopes.pop()

        return self._accumulate_distribution_contributions(contributions)

    def visit_TenOp(self, node):
        """Visit a Tenary-Operator node"""
        if node.op1.type == RES and node.op2.type == ELSE:
            return self.engine.reselse(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
        elif node.op1.type == ROLL and node.op2.type == HIGH:
            return self.engine.rollhigh(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
        elif node.op1.type == ROLL and node.op2.type == LOW:
            return self.engine.rolllow(self.visit(node.left), self.visit(node.middle), self.visit(node.right))
        self.exception("{} not implemented".format(node))

    def visit_BinOp(self, node):
        """Visit a Binary-Operator node"""

        if node.op.type == PLUS:
            return self.engine.add(self.visit(node.left), self.visit(node.right))
        if node.op.type == MINUS:
            return self.engine.sub(self.visit(node.left), self.visit(node.right))
        if node.op.type == MUL:
            return self.engine.mul(self.visit(node.left), self.visit(node.right))
        if node.op.type == DIV:
            return self.engine.div(self.visit(node.left), self.visit(node.right))
        if node.op.type == ROLL:
            return self.engine.roll(self.visit(node.left), self.visit(node.right))
        if node.op.type == GREATER_OR_EQUAL:
            return self.engine.greaterorequal(self.visit(node.left), self.visit(node.right))
        if node.op.type == LESS_OR_EQUAL:
            return self.engine.lessorequal(self.visit(node.left), self.visit(node.right))
        if node.op.type == GREATER:
            return self.engine.greater(self.visit(node.left), self.visit(node.right))
        if node.op.type == LESS:
            return self.engine.less(self.visit(node.left), self.visit(node.right))
        if node.op.type == EQUAL:
            return self.engine.equal(self.visit(node.left), self.visit(node.right))
        if node.op.type == RES:
            return self.engine.res(self.visit(node.left), self.visit(node.right))
        if node.op.type == ELSEDIV:
            return self.engine.reselsediv(self.visit(node.left), self.visit(node.right))
        if node.op.type == COLON:
            # generate a sweep ranging value1 to value2 of integers
            val1 = self.visit(node.left)
            if type(val1) != int:
                self.exception("Expected int got {}".format(type(val1)))
            val2 = self.visit(node.right)
            if type(val2) != int:
                self.exception("Expected int got {}".format(type(val2)))
            cache_key = (val1, val2)
            if not hasattr(self, "_sweep_cache"):
                self._sweep_cache = {}
            if id(node) not in self._sweep_cache:
                self._sweep_cache[id(node)] = {}
            if cache_key not in self._sweep_cache[id(node)]:
                self._sweep_cache[id(node)][cache_key] = Sweep(range(val1, val2 + 1))
            return self._sweep_cache[id(node)][cache_key]
        if node.op.type == LBRACK:
            return self.engine.choose(self.visit(node.left), self.visit(node.right))
        if node.op.type == DOT:
            return self.engine.choose_single(self.visit(node.left), self.visit(node.right))
        if node.op.type == ASSIGN:
            self.global_scope[node.left.value] = self.visit(node.right)
            return

        self.exception("{} not implemented".format(node))

    def visit_UnOp(self, node):
        """Visits a Unary-Operator node"""
        if node.op.type == ROLL:
            return self.engine.rollsingle(self.visit(node.value))
        elif node.op.type == ADV:
            return self.engine.rolladvantage(self.visit(node.value))
        elif node.op.type == DIS:
            return self.engine.rolldisadvantage(self.visit(node.value))
        elif node.op.type == RES:
            return self.engine.resunary(self.visit(node.value))
        elif node.op.type == AVG:
            return self.engine.resunary(self.visit(node.value))
        elif node.op.type == PROP:
            return self.engine.prop(self.visit(node.value))
        elif node.op.type == PRINT:
            print(self.visit(node.value))
            return
        self.exception("{} not implemented".format(node))

    def visit_Val(self, node):
        """Visits a Value node"""
        if node.token.type in [INTEGER, STRING]:
            return node.value

        for scope in reversed(self.local_scopes):
            if node.value in scope:
                return scope[node.value]

        if not node.value in self.global_scope:
            self.exception("Could not dereference {}".format(node))
        return self.global_scope[node.value]

if __name__ == "__main__":
    input_text = 'a = d20; print a; render(a)'
    ast = DiceParser(Lexer(input_text)).parse()
    print(ast)
    interpreter = Interpreter(ast)
    result = interpreter.interpret()
