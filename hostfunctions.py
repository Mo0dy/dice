#!/usr/bin/env python3

"""Shared host-function decorator and metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass
import functools
import inspect
from itertools import product
from typing import Any, get_origin, get_type_hints

from diceparser import DiceParser
from lexer import Lexer, ASSIGN, SEMI, PRINT


MISSING = object()
_DICEFUNCTION_ATTR = "_dicefunction_metadata"


def _diceengine():
    import diceengine

    return diceengine


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
    keyword_only: bool = False
    wants_sweep: bool = False
    coercion_kind: str | None = None

    @property
    def has_default(self):
        return self.default_value is not MISSING


@dataclass(frozen=True)
class DiceFunctionMetadata:
    export_name: str
    raw_function: object
    parameters: tuple[ParameterSpec, ...]
    signature: inspect.Signature
    cache_enabled: bool
    requests_sweep: bool
    bind_arguments: object


def validate_runtime_value(value):
    diceengine = _diceengine()
    if value is None:
        return value
    if isinstance(
        value,
        (
            int,
            float,
            str,
            diceengine.TupleValue,
            diceengine.RecordValue,
            diceengine.SweepValues,
            diceengine.FiniteMeasure,
            diceengine.Distribution,
            diceengine.Sweep,
            diceengine.ChartSpec,
            diceengine.ReportSpec,
        ),
    ):
        return value
    raise Exception("Unsupported host value type {}".format(type(value)))


def _identifier_names(node):
    names = set()
    if node is None:
        return names
    node_type = type(node).__name__
    if node_type == "Val" and getattr(getattr(node, "token", None), "type", None) == "ID":
        names.add(node.value)
    for value in getattr(node, "__dict__", {}).values():
        if isinstance(value, list):
            for item in value:
                names.update(_identifier_names(item))
        else:
            names.update(_identifier_names(value))
    return names


def _function_type_hints(function):
    try:
        return get_type_hints(function)
    except Exception:
        return {}


def callable_parameters(function, variadic=False):
    if variadic:
        return ()
    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())
    names = [parameter.name for parameter in parameters]
    hints = _function_type_hints(function)
    specs = []
    for parameter in parameters:
        if parameter.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise Exception("Python functions only support POSITIONAL_OR_KEYWORD parameters")
        default_value = MISSING
        if parameter.default is not inspect._empty:
            default_value = parameter.default
            if isinstance(default_value, DiceDefault):
                referenced = _identifier_names(default_value.ast)
                forbidden = sorted(name for name in names if name in referenced)
                if forbidden:
                    raise Exception(
                        "D(...) defaults may only reference globals, not parameters: {}".format(", ".join(forbidden))
                    )
        specs.append(
            ParameterSpec(
                name=parameter.name,
                default_value=default_value,
                annotation=hints.get(parameter.name),
                wants_sweep=_annotation_is_sweep(hints.get(parameter.name)),
                coercion_kind=_annotation_coercion_kind(hints.get(parameter.name)),
            )
        )
    return tuple(specs)


def _annotation_requests_sweep(function):
    hints = _function_type_hints(function)
    for annotation in hints.values():
        if _annotation_is_sweep(annotation):
            return True
    return False


def _annotation_is_sweep(annotation):
    diceengine = _diceengine()
    return annotation is diceengine.Sweep or get_origin(annotation) is diceengine.Sweep


def _annotation_coercion_kind(annotation):
    diceengine = _diceengine()
    if annotation is diceengine.Distribution:
        return "distribution"
    if annotation is diceengine.FiniteMeasure:
        return "measure"
    return None


def _convert_projected_argument(projected, parameter):
    diceengine = _diceengine()
    if parameter.coercion_kind == "distribution":
        return diceengine._coerce_to_distribution_cell(projected)
    if parameter.coercion_kind == "measure":
        return diceengine._coerce_to_measure_cell(projected)
    return projected


def _build_argument_binder(parameters, export_name):
    parameter_count = len(parameters)
    required_count = sum(1 for parameter in parameters if not parameter.has_default)
    parameter_names = tuple(parameter.name for parameter in parameters)
    name_to_index = {name: index for index, name in enumerate(parameter_names)}

    def missing_error(missing_names):
        quoted = ", ".join("'{}'".format(name) for name in missing_names)
        plural = "s" if len(missing_names) != 1 else ""
        raise TypeError("{}() missing required positional argument{}: {}".format(export_name, plural, quoted))

    def bind_arguments(*args, **kwargs):
        positional_count = len(args)
        if positional_count > parameter_count:
            raise TypeError(
                "{}() takes {} positional argument{} but {} were given".format(
                    export_name,
                    parameter_count,
                    "" if parameter_count == 1 else "s",
                    positional_count,
                )
            )
        if not kwargs:
            if positional_count == parameter_count:
                return tuple(args)
            if positional_count < required_count:
                missing_error(parameter_names[positional_count:required_count])
            return tuple(args) + tuple(parameter.default_value for parameter in parameters[positional_count:])

        bound = [MISSING] * parameter_count
        for index, value in enumerate(args):
            bound[index] = value
        for name, value in kwargs.items():
            index = name_to_index.get(name)
            if index is None:
                raise TypeError("{}() got an unexpected keyword argument '{}'".format(export_name, name))
            if bound[index] is not MISSING:
                raise TypeError("{}() got multiple values for argument '{}'".format(export_name, name))
            bound[index] = value
        missing = []
        for index, parameter in enumerate(parameters):
            if bound[index] is MISSING:
                if parameter.has_default:
                    bound[index] = parameter.default_value
                else:
                    missing.append(parameter.name)
        if missing:
            missing_error(tuple(missing))
        return tuple(bound)

    return bind_arguments


def _lifted_python_call(function, parameters, values):
    diceengine = _diceengine()
    projected_arguments = []
    combined_sweeps = []
    for index, value in enumerate(values):
        parameter = parameters[index] if index < len(parameters) else None
        if parameter is not None and parameter.wants_sweep:
            projected_arguments.append((False, value, parameter))
            continue
        sweep = diceengine._coerce_value_to_sweep(value)
        projected_arguments.append((True, sweep, parameter))
        combined_sweeps.append(sweep)
    combined_axes = diceengine._union_axes(combined_sweeps)
    if not combined_axes:
        projected = []
        for is_projected, value, parameter in projected_arguments:
            if not is_projected:
                projected.append(value)
                continue
            projected.append(_convert_projected_argument(value.only_value(), parameter))
        return validate_runtime_value(function(*projected))
    cells = {}
    for coordinates in ([()] if not combined_axes else product(*(axis.values for axis in combined_axes))):
        projected = []
        for is_projected, value, parameter in projected_arguments:
            if not is_projected:
                projected.append(value)
                continue
            projected.append(_convert_projected_argument(value.lookup(combined_axes, coordinates), parameter))
        result = validate_runtime_value(function(*projected))
        if isinstance(result, diceengine.Sweep) and result.is_unswept():
            result = result.only_value()
        cells[coordinates] = result
    return diceengine.Sweep(combined_axes, cells)


def dicefunction(function=None, *, name=None, cache=False):
    def decorate(raw_function):
        export_name = name if name is not None else raw_function.__name__
        if not export_name:
            raise Exception("Python functions must have a name")
        parameters = callable_parameters(raw_function)
        signature = inspect.signature(raw_function)
        requests_sweep = _annotation_requests_sweep(raw_function)
        bind_arguments = _build_argument_binder(parameters, export_name)
        if cache and requests_sweep:
            raise Exception("@dicefunction(cache=True) is not supported for sweep functions")
        wrapped_function = functools.lru_cache(maxsize=None)(raw_function) if cache else raw_function

        @functools.wraps(raw_function)
        def wrapped(*args, **kwargs):
            values = []
            for parameter, value in zip(parameters, bind_arguments(*args, **kwargs)):
                if isinstance(value, DiceDefault):
                    raise Exception("D(...) defaults are only resolved by dice-session invocation")
                values.append(value)
            return _lifted_python_call(wrapped_function, parameters, values)

        setattr(
            wrapped,
            _DICEFUNCTION_ATTR,
            DiceFunctionMetadata(
                export_name=export_name,
                raw_function=raw_function,
                parameters=parameters,
                signature=signature,
                cache_enabled=cache,
                requests_sweep=requests_sweep,
                bind_arguments=bind_arguments,
            ),
        )
        return wrapped

    if function is None:
        return decorate
    return decorate(function)


def get_dicefunction_metadata(function):
    return getattr(function, _DICEFUNCTION_ATTR, None)
