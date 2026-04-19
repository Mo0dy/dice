#!/usr/bin/env python3

"""Interpreter-facing execution backends for dice semantics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import diceengine
from hostfunctions import (
    D,
    DiceDefault,
    ParameterSpec,
    callable_parameters,
    dicefunction,
    get_dicefunction_metadata,
    validate_runtime_value,
)


@dataclass
class HostFunction:
    name: str
    function: object
    parameters: tuple[ParameterSpec, ...] = ()
    variadic: bool = False
    variadic_keyword_arguments: bool = False
    sweep_mode: bool = False

class Executor(ABC):
    """Abstract interpreter backend plus named host-callable registry."""

    def __init__(self, render_config=None):
        self.functions = {}
        self.render_config = render_config if render_config is not None else diceengine.RenderConfig()
        self.pending_report = diceengine.ReportSpec()
        self._register_builtin_functions()

    def _callable_parameters(self, function, variadic=False):
        metadata = get_dicefunction_metadata(function)
        if metadata is not None and not variadic:
            return metadata.parameters
        return callable_parameters(function, variadic=variadic)

    def _annotation_requests_sweep(self, function):
        metadata = get_dicefunction_metadata(function)
        if metadata is not None:
            return any(parameter.annotation is diceengine.Sweep for parameter in metadata.parameters)
        hints = getattr(function, "__annotations__", {})
        return any(annotation is diceengine.Sweep for annotation in hints.values())

    def _register_host_function(
        self,
        function,
        name=None,
        variadic=False,
        sweep_mode=None,
        require_decorated=False,
        parameters=None,
        variadic_keyword_arguments=False,
    ):
        metadata = get_dicefunction_metadata(function)
        if require_decorated and metadata is None:
            raise Exception("Python functions must be decorated with @dicefunction to be registered")
        callable_name = name if name is not None else (metadata.export_name if metadata is not None else function.__name__)
        if not callable_name:
            raise Exception("Python functions must have a name")
        if callable_name in self.functions:
            raise Exception("Duplicate function definition for {}".format(callable_name))
        parameters = parameters if parameters is not None else self._callable_parameters(function, variadic=variadic)
        entry = HostFunction(
            callable_name,
            function=function,
            parameters=parameters,
            variadic=variadic,
            variadic_keyword_arguments=variadic_keyword_arguments,
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
            "meanover",
            "maxover",
            "argmaxover",
            "total",
            "set_render_mode",
            "set_render_backend",
            "set_render_autoflush",
            "set_render_omit_dominant_zero",
            "set_probability_mode",
            "r_title",
            "r_note",
            "r_hero",
            "r_wide",
            "r_narrow",
        ]:
            self._register_host_function(getattr(self, name), name=name, sweep_mode=True)
        self._register_host_function(
            self.r_row,
            name="r_row",
            variadic=True,
            sweep_mode=True,
        )
        chart_kw_parameters = (
            ParameterSpec("x", default_value=None, keyword_only=True),
            ParameterSpec("y", default_value=None, keyword_only=True),
            ParameterSpec("title", default_value=None, keyword_only=True),
        )
        compare_kw_parameters = (
            ParameterSpec("x", default_value=None, keyword_only=True),
            ParameterSpec("y", default_value=None, keyword_only=True),
            ParameterSpec("title", default_value=None, keyword_only=True),
        )
        self._register_host_function(self.r_auto, name="r_auto", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_dist, name="r_dist", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_cdf, name="r_cdf", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_surv, name="r_surv", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_compare, name="r_compare", sweep_mode=True, parameters=compare_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_diff, name="r_diff", sweep_mode=True, parameters=compare_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_best, name="r_best", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(
            self.render,
            name="render",
            sweep_mode=True,
            parameters=(
                ParameterSpec("path", default_value=None),
                ParameterSpec("format", default_value=None),
                ParameterSpec("dpi", default_value=None),
            ),
        )

    def register_function(self, function, name=None):
        return self._register_host_function(function, name=name, require_decorated=True)

    def repeat_sum(self, count, value):
        return diceengine.repeat_sum(count, value)

    def sumover(self, value, axes=None):
        return diceengine.sumover_with(self.add, value, diceengine._OMITTED if axes is None else axes)

    def meanover(self, value, axes=None):
        return diceengine.meanover(value, diceengine._OMITTED if axes is None else axes)

    def maxover(self, value, axes=None):
        return diceengine.maxover(value, diceengine._OMITTED if axes is None else axes)

    def argmaxover(self, value, axes=None):
        return diceengine.argmaxover(value, diceengine._OMITTED if axes is None else axes)

    def total(self, value: diceengine.Sweep[Any]) -> diceengine.Sweep[Any]:
        return diceengine.total_with(self.add, value)

    def _normalize_chart_arguments(self, args, x=None, y=None, title=None):
        if len(args) != 1:
            raise Exception("chart constructors expect exactly one expression")
        return args[0], x, y, title

    def r_auto(self, *args, x=None, y=None, title=None):
        value, x, y, title = self._normalize_chart_arguments(args, x=x, y=y, title=title)
        return diceengine.ChartSpec("auto", payload=value, x_label=x, y_label=y, title=title)

    def r_dist(self, *args, x=None, y=None, title=None):
        value, x, y, title = self._normalize_chart_arguments(args, x=x, y=y, title=title)
        return diceengine.ChartSpec("dist", payload=value, x_label=x, y_label=y, title=title)

    def r_cdf(self, *args, x=None, y=None, title=None):
        value, x, y, title = self._normalize_chart_arguments(args, x=x, y=y, title=title)
        return diceengine.ChartSpec("cdf", payload=value, x_label=x, y_label=y, title=title)

    def r_surv(self, *args, x=None, y=None, title=None):
        value, x, y, title = self._normalize_chart_arguments(args, x=x, y=y, title=title)
        return diceengine.ChartSpec("surv", payload=value, x_label=x, y_label=y, title=title)

    def r_compare(self, *entries, x=None, y=None, title=None):
        return diceengine.ChartSpec("compare", payload=tuple(entries), x_label=x, y_label=y, title=title)

    def r_diff(self, *entries, x=None, y=None, title=None):
        return diceengine.ChartSpec("diff", payload=tuple(entries), x_label=x, y_label=y, title=title)

    def r_best(self, *args, x=None, y=None, title=None):
        value, x, y, title = self._normalize_chart_arguments(args, x=x, y=y, title=title)
        return diceengine.ChartSpec("best", payload=value, x_label=x, y_label=y, title=title)

    def r_title(self, text):
        self.pending_report = diceengine.report_set_title(self.pending_report, text)
        return None

    def r_note(self, text):
        self.pending_report = diceengine.report_add_note(self.pending_report, text)
        return None

    def r_hero(self, chart):
        self.pending_report = diceengine.report_set_hero(self.pending_report, chart)
        return None

    def r_row(self, *charts):
        self.pending_report = diceengine.report_add_row(self.pending_report, charts)
        return None

    def r_wide(self, chart):
        return diceengine.chart_with_width(chart, "wide")

    def r_narrow(self, chart):
        return diceengine.chart_with_width(chart, "narrow")

    def append_chart(self, chart):
        self.pending_report = diceengine.report_append_chart(self.pending_report, chart)

    def render(self, path=None, format=None, dpi=None):
        output_path = diceengine.render_report(
            self.pending_report,
            render_config=self.render_config,
            path=path,
            format=format,
            dpi=dpi,
        )
        self.pending_report = diceengine.ReportSpec()
        return output_path

    def flush_pending_report_at_end(self):
        if not self.render_config.auto_render_pending_on_exit:
            return None
        if not self.pending_report.has_renderable_content():
            return None
        return self.render()

    def set_render_mode(self, mode):
        self.render_config = self.render_config.with_mode(mode)
        return self.render_config.mode_name()

    def set_render_backend(self, backend):
        self.render_config = self.render_config.with_backend(backend)
        return self.render_config.backend

    def set_render_autoflush(self, enabled):
        self.render_config = self.render_config.with_auto_render_pending(enabled)
        return "on" if self.render_config.auto_render_pending_on_exit else "off"

    def set_render_omit_dominant_zero(self, enabled):
        self.render_config = self.render_config.with_omit_dominant_zero_outcome(enabled)
        return "on" if self.render_config.omit_dominant_zero_outcome else "off"

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
    def meanover(self, value, axes=None):
        raise NotImplementedError

    @abstractmethod
    def maxover(self, value, axes=None):
        raise NotImplementedError

    @abstractmethod
    def argmaxover(self, value, axes=None):
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

    def _register_builtin_functions(self):
        for value in diceengine.__dict__.values():
            metadata = get_dicefunction_metadata(value)
            if metadata is None or getattr(value, "__module__", None) != diceengine.__name__:
                continue
            self._register_host_function(value)
        for name in [
            "type",
            "shape",
            "set_render_mode",
            "set_render_backend",
            "set_render_autoflush",
            "set_render_omit_dominant_zero",
            "set_probability_mode",
            "r_title",
            "r_note",
            "r_hero",
            "r_wide",
            "r_narrow",
        ]:
            self._register_host_function(getattr(self, name), name=name, sweep_mode=True)
        self._register_host_function(
            self.r_row,
            name="r_row",
            variadic=True,
            sweep_mode=True,
        )
        chart_kw_parameters = (
            ParameterSpec("x", default_value=None, keyword_only=True),
            ParameterSpec("y", default_value=None, keyword_only=True),
            ParameterSpec("title", default_value=None, keyword_only=True),
        )
        compare_kw_parameters = (
            ParameterSpec("x", default_value=None, keyword_only=True),
            ParameterSpec("y", default_value=None, keyword_only=True),
            ParameterSpec("title", default_value=None, keyword_only=True),
        )
        self._register_host_function(self.r_auto, name="r_auto", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_dist, name="r_dist", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_cdf, name="r_cdf", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_surv, name="r_surv", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_compare, name="r_compare", sweep_mode=True, parameters=compare_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_diff, name="r_diff", sweep_mode=True, parameters=compare_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(self.r_best, name="r_best", sweep_mode=True, parameters=chart_kw_parameters, variadic=True, variadic_keyword_arguments=True)
        self._register_host_function(
            self.render,
            name="render",
            sweep_mode=True,
            parameters=(
                ParameterSpec("path", default_value=None),
                ParameterSpec("format", default_value=None),
                ParameterSpec("dpi", default_value=None),
            ),
        )

    def member(self, left, right):
        return diceengine.member(left, right)

    def res(self, condition, distrib):
        return diceengine.res(condition, distrib)

    def mean(self, value):
        return diceengine.mean(value)

    def meanover(self, value, axes=None):
        return diceengine.meanover(value, diceengine._OMITTED if axes is None else axes)

    def maxover(self, value, axes=None):
        return diceengine.maxover(value, diceengine._OMITTED if axes is None else axes)

    def argmaxover(self, value, axes=None):
        return diceengine.argmaxover(value, diceengine._OMITTED if axes is None else axes)

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
