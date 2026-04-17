#!/usr/bin/env python3

"""Interpreter-facing execution backends for dice semantics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect
from typing import Any, get_origin, get_type_hints

import diceengine
from diceparser import DiceParser
from lexer import Lexer, ASSIGN, SEMI, PRINT


MISSING = object()


@dataclass(frozen=True)
class DiceDefault:
    source: str
    ast: object


def D(source):
    if not isinstance(source, str) or not source.strip():
        raise Exception("D(...) expects a non-empty dice expression string")
    ast = DiceParser(Lexer(source)).parse()
    if type(ast).__name__ in {"FunctionDef", "Import"}:
        raise Exception("D(...) defaults must be expressions, not top-level statements")
    if type(ast).__name__ == "VarOp" and getattr(ast.op, "type", None) == SEMI:
        raise Exception("D(...) defaults must be a single expression")
    if type(ast).__name__ == "BinOp" and getattr(ast.op, "type", None) == ASSIGN:
        raise Exception("D(...) defaults must be expressions, not assignments")
    if type(ast).__name__ == "UnOp" and getattr(ast.op, "type", None) == PRINT:
        raise Exception("D(...) defaults must be expressions, not print statements")
    return DiceDefault(source, ast)


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    default_value: object = MISSING
    annotation: object = None

    @property
    def has_default(self):
        return self.default_value is not MISSING


@dataclass
class HostFunction:
    name: str
    function: object
    parameters: tuple[ParameterSpec, ...] = ()
    variadic: bool = False
    sweep_mode: bool = False


class Executor(ABC):
    """Abstract interpreter backend plus named host-callable registry."""

    def __init__(self, render_config=None):
        self.functions = {}
        self.render_config = render_config if render_config is not None else diceengine.RenderConfig()
        self._register_builtin_functions()

    def _identifier_names(self, node):
        names = set()
        if node is None:
            return names
        node_type = type(node).__name__
        if node_type == "Val" and getattr(getattr(node, "token", None), "type", None) == "ID":
            names.add(node.value)
        for value in getattr(node, "__dict__", {}).values():
            if isinstance(value, list):
                for item in value:
                    names.update(self._identifier_names(item))
            else:
                names.update(self._identifier_names(value))
        return names

    def _callable_parameters(self, function, variadic=False):
        if variadic:
            return ()
        signature = inspect.signature(function)
        parameters = list(signature.parameters.values())
        names = [parameter.name for parameter in parameters]
        specs = []
        for parameter in parameters:
            if parameter.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
                raise Exception("Python functions only support POSITIONAL_OR_KEYWORD parameters")
            default_value = MISSING
            if parameter.default is not inspect._empty:
                default_value = parameter.default
                if isinstance(default_value, DiceDefault):
                    referenced = self._identifier_names(default_value.ast)
                    forbidden = sorted(name for name in names if name in referenced)
                    if forbidden:
                        raise Exception(
                            "D(...) defaults may only reference globals, not parameters: {}".format(", ".join(forbidden))
                        )
            specs.append(
                ParameterSpec(
                    name=parameter.name,
                    default_value=default_value,
                    annotation=self._type_hints(function).get(parameter.name),
                )
            )
        return tuple(specs)

    def _type_hints(self, function):
        try:
            return get_type_hints(function)
        except Exception:
            return {}

    def _annotation_requests_sweep(self, function):
        hints = self._type_hints(function)
        for annotation in hints.values():
            if annotation is diceengine.Sweep or get_origin(annotation) is diceengine.Sweep:
                return True
        return False

    def _register_host_function(self, function, name=None, variadic=False, sweep_mode=None):
        callable_name = name if name is not None else function.__name__
        if not callable_name:
            raise Exception("Python functions must have a name")
        if callable_name in self.functions:
            raise Exception("Duplicate function definition for {}".format(callable_name))
        parameters = self._callable_parameters(function, variadic=variadic)
        entry = HostFunction(
            callable_name,
            function=function,
            parameters=parameters,
            variadic=variadic,
            sweep_mode=self._annotation_requests_sweep(function) if sweep_mode is None else sweep_mode,
        )
        self.functions[callable_name] = entry
        return function

    def _register_builtin_functions(self):
        for name in [
            "add",
            "sub",
            "mul",
            "div",
            "floordiv",
            "neg",
            "roll",
            "rollsingle",
            "rolladvantage",
            "rolldisadvantage",
            "rollhigh",
            "rolllow",
            "greaterorequal",
            "greater",
            "equal",
            "lessorequal",
            "less",
            "member",
            "res",
            "reselse",
            "reselsediv",
            "reselsefloordiv",
            "mean",
            "sample",
            "var",
            "std",
            "cum",
            "surv",
            "type",
            "shape",
            "repeat_sum",
            "sumover",
            "total",
            "set_render_mode",
            "set_probability_mode",
        ]:
            self._register_host_function(getattr(self, name), name=name, sweep_mode=True)
        self._register_host_function(self.render, name="render", variadic=True, sweep_mode=True)
        self._register_host_function(self.renderp, name="renderp", variadic=True, sweep_mode=True)

    def register_function(self, function, name=None):
        return self._register_host_function(function, name=name)

    def repeat_sum(self, count, value):
        return diceengine.repeat_sum_with(self.add, count, value)

    def sumover(self, axis_name: str, value: diceengine.Sweep[Any]) -> diceengine.Sweep[Any]:
        return diceengine.sumover_with(self.add, axis_name, value)

    def total(self, value: diceengine.Sweep[Any]) -> diceengine.Sweep[Any]:
        return diceengine.total_with(self.add, value)

    def render(self, *args):
        return diceengine.render(*args, render_config=self.render_config)

    def renderp(self, *args):
        return diceengine.renderp(*args, render_config=self.render_config)

    def set_render_mode(self, mode):
        self.render_config = self.render_config.with_mode(mode)
        return self.render_config.mode_name()

    def set_probability_mode(self, mode):
        self.render_config = self.render_config.with_probability_mode(mode)
        return self.render_config.effective_probability_mode()

    @abstractmethod
    def member(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def res(self, condition, distrib):
        raise NotImplementedError

    @abstractmethod
    def mean(self, value):
        raise NotImplementedError

    @abstractmethod
    def var(self, value):
        raise NotImplementedError

    @abstractmethod
    def std(self, value):
        raise NotImplementedError

    @abstractmethod
    def cum(self, value):
        raise NotImplementedError

    @abstractmethod
    def surv(self, value):
        raise NotImplementedError

    @abstractmethod
    def sample(self, value):
        raise NotImplementedError

    def type(self, value):
        return diceengine.runtime_type(value)

    def shape(self, value):
        return diceengine.runtime_shape(value)

    @abstractmethod
    def reselse(self, condition, distrib_if, distrib_else):
        raise NotImplementedError

    @abstractmethod
    def reselsediv(self, condition, distrib):
        raise NotImplementedError

    @abstractmethod
    def reselsefloordiv(self, condition, distrib):
        raise NotImplementedError

    @abstractmethod
    def roll(self, n, s):
        raise NotImplementedError

    @abstractmethod
    def rollsingle(self, dice):
        raise NotImplementedError

    @abstractmethod
    def rolladvantage(self, dice):
        raise NotImplementedError

    @abstractmethod
    def rolldisadvantage(self, dice):
        raise NotImplementedError

    @abstractmethod
    def rollhigh(self, n, s, nh):
        raise NotImplementedError

    @abstractmethod
    def rolllow(self, n, s, nl):
        raise NotImplementedError

    @abstractmethod
    def add(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def sub(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def mul(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def div(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def floordiv(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def neg(self, value):
        raise NotImplementedError

    @abstractmethod
    def greaterorequal(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def greater(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def equal(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def lessorequal(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def less(self, left, right):
        raise NotImplementedError


class ExactExecutor(Executor):
    """Exact backend delegating to pure functions in diceengine."""

    def member(self, left, right):
        return diceengine.member(left, right)

    def res(self, condition, distrib):
        return diceengine.res(condition, distrib)

    def mean(self, value):
        return diceengine.mean(value)

    def var(self, value):
        return diceengine.var(value)

    def std(self, value):
        return diceengine.std(value)

    def cum(self, value):
        return diceengine.cum(value)

    def surv(self, value):
        return diceengine.surv(value)

    def sample(self, value):
        return diceengine.sample(value)

    def reselse(self, condition, distrib_if, distrib_else):
        return diceengine.reselse(condition, distrib_if, distrib_else)

    def reselsediv(self, condition, distrib):
        return diceengine.reselsediv(condition, distrib)

    def reselsefloordiv(self, condition, distrib):
        return diceengine.reselsefloordiv(condition, distrib)

    def roll(self, n, s):
        return diceengine.roll(n, s)

    def rollsingle(self, dice):
        return diceengine.rollsingle(dice)

    def rolladvantage(self, dice):
        return diceengine.rolladvantage(dice)

    def rolldisadvantage(self, dice):
        return diceengine.rolldisadvantage(dice)

    def rollhigh(self, n, s, nh):
        return diceengine.rollhigh(n, s, nh)

    def rolllow(self, n, s, nl):
        return diceengine.rolllow(n, s, nl)

    def add(self, left, right):
        return diceengine.add(left, right)

    def sub(self, left, right):
        return diceengine.sub(left, right)

    def mul(self, left, right):
        return diceengine.mul(left, right)

    def div(self, left, right):
        return diceengine.div(left, right)

    def floordiv(self, left, right):
        return diceengine.floordiv(left, right)

    def neg(self, value):
        return diceengine.neg(value)

    def greaterorequal(self, left, right):
        return diceengine.greaterorequal(left, right)

    def greater(self, left, right):
        return diceengine.greater(left, right)

    def equal(self, left, right):
        return diceengine.equal(left, right)

    def lessorequal(self, left, right):
        return diceengine.lessorequal(left, right)

    def less(self, left, right):
        return diceengine.less(left, right)
