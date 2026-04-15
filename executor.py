#!/usr/bin/env python3

"""Interpreter-facing execution backends for dice semantics."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import inspect

import diceengine


@dataclass
class HostFunction:
    name: str
    function: object
    arity: int | None = None
    variadic: bool = False


class Executor(ABC):
    """Abstract interpreter backend plus named host-callable registry."""

    def __init__(self):
        self.functions = {}
        self._register_builtin_functions()

    def _callable_arity(self, function):
        signature = inspect.signature(function)
        arity = 0
        for parameter in signature.parameters.values():
            if parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                raise Exception("Python functions only support fixed positional arguments")
            if parameter.default is not inspect._empty:
                raise Exception("Python functions only support fixed positional arguments")
            arity += 1
        return arity

    def _register_host_function(self, function, name=None, variadic=False):
        callable_name = name if name is not None else function.__name__
        if not callable_name:
            raise Exception("Python functions must have a name")
        if callable_name in self.functions:
            raise Exception("Duplicate function definition for {}".format(callable_name))
        arity = None if variadic else self._callable_arity(function)
        entry = HostFunction(callable_name, function=function, arity=arity, variadic=variadic)
        self.functions[callable_name] = entry
        return function

    def _register_builtin_functions(self):
        for name in [
            "add",
            "sub",
            "mul",
            "div",
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
            "res",
            "reselse",
            "reselsediv",
            "choose",
            "choose_single",
            "mean",
            "sample",
            "mass",
            "var",
            "std",
            "repeat_sum",
            "sumover",
            "total",
        ]:
            self._register_host_function(getattr(self, name), name=name)
        self._register_host_function(self.render, name="render", variadic=True)

    def register_function(self, function, name=None):
        return self._register_host_function(function, name=name)

    def repeat_sum(self, count, value):
        return diceengine.repeat_sum_with(self.add, count, value)

    def sumover(self, axis_name, value):
        return diceengine.sumover_with(self.add, axis_name, value)

    def total(self, value):
        return diceengine.total_with(self.add, value)

    def render(self, *args):
        return diceengine.render(*args)

    @abstractmethod
    def choose(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def choose_single(self, left, right):
        raise NotImplementedError

    @abstractmethod
    def res(self, condition, distrib):
        raise NotImplementedError

    @abstractmethod
    def mean(self, value):
        raise NotImplementedError

    @abstractmethod
    def mass(self, value):
        raise NotImplementedError

    @abstractmethod
    def var(self, value):
        raise NotImplementedError

    @abstractmethod
    def std(self, value):
        raise NotImplementedError

    @abstractmethod
    def sample(self, value):
        raise NotImplementedError

    @abstractmethod
    def reselse(self, condition, distrib_if, distrib_else):
        raise NotImplementedError

    @abstractmethod
    def reselsediv(self, condition, distrib):
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

    def choose(self, left, right):
        return diceengine.choose(left, right)

    def choose_single(self, left, right):
        return diceengine.choose_single(left, right)

    def res(self, condition, distrib):
        return diceengine.res(condition, distrib)

    def mean(self, value):
        return diceengine.mean(value)

    def mass(self, value):
        return diceengine.mass(value)

    def var(self, value):
        return diceengine.var(value)

    def std(self, value):
        return diceengine.std(value)

    def sample(self, value):
        return diceengine.sample(value)

    def reselse(self, condition, distrib_if, distrib_else):
        return diceengine.reselse(condition, distrib_if, distrib_else)

    def reselsediv(self, condition, distrib):
        return diceengine.reselsediv(condition, distrib)

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
