"""
Argument validation functions, including type and value enforcing.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import functools
import inspect
import reprlib
from collections.abc import Callable
from typing import (
    ParamSpec,
    TypeVar,
    get_type_hints,
)

from .predicates import Predicate
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions
from .util import (
    as_predicate,
    fast_bind,
    make_plan,
    matches_hint,
    spec_contains_int,
    to_call_args,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")

_SHORT = reprlib.Repr()
_SHORT.maxstring = 80
_SHORT.maxother = 80


def enforce_types(
    options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    /,
    **types: type | tuple[type, ...],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces the types of function parameters.

    Supports typing types.

    Args:
        options (EnforceOptions, optional): Type enforcement options.
            Defaults to DEFAULT_ENFORCE_OPTIONS.
        types (Type | Tuple[Type, ...]): A mapping of argument names to expected types.
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        sig = inspect.signature(func)

        # validate all arguments given exist in the function signature
        for name in types:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = make_plan(sig)

        # compile once
        validators: dict[str, Predicate] = {
            name: as_predicate(spec, options) for name, spec in types.items()
        }

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            bound = fast_bind(
                plan, sig, args, kwargs, apply_defaults=options.check_defaults
            )

            for name, pred in validators.items():
                val = bound[name]
                if not pred(val):
                    conditions = "("
                    if not options.allow_subclasses:
                        conditions += "no subclasses"
                    if options.strict_bools and any(
                        # only add bool info if there's an int in the types
                        spec_contains_int(v)
                        for v in types.values()
                    ):
                        if not options.allow_subclasses:
                            conditions += ", "
                        conditions += "no bools as ints"
                    conditions += ")"

                    raise TypeError(
                        f"{func.__qualname__}(): '{name}' expected {pred.msg} "
                        f"{conditions if conditions != '()' else ''}, "
                        f"got '{type_repr(type(val))}' with value {_SHORT.repr(val)}"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def enforce_annotations(
    *, check_return: bool = True
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces the function's type hints at runtime.

    Args:
        check_return (bool, optional): Whether to enforce the return type.
            Defaults to True.
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        hints = get_type_hints(func, include_extras=True)
        param_hints = {k: v for k, v in hints.items() if k != "return"}

        wrapped = enforce_types(**param_hints)(func)
        if not check_return or "return" not in hints:
            return wrapped

        @functools.wraps(wrapped)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            out = wrapped(*args, **kwargs)

            if not matches_hint(out, hints["return"], DEFAULT_ENFORCE_OPTIONS):
                raise TypeError(
                    f"{func.__qualname__}(): return expected "
                    f"{type_repr(hints['return'])}, got {type_repr(type(out))}"
                )

            return out

        return wrapper

    return decorator


def coerce_types(
    **coercers: Callable[[object], object],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that coerces the types of function parameters using coercer functions.

    This decorator is particularly useful for coercing string arguments into
    their proper types when using CLI/ENV arguments, web handlers, enums, and JSONs.

    Args:
        coercers (Callable[[object], object]): A mapping of argument names
            to coercer functions
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        sig = inspect.signature(func)
        plan = make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            bound = fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, coerce in coercers.items():
                if name in bound:
                    bound[name] = coerce(bound[name])

            # rebuild call args and invoke
            call_args, call_kwargs = to_call_args(bound, plan)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator


def enforce_values(
    **predicate_map: Predicate,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces value constraints on function parameters.

    Args:
        predicate_map (Predicate): A mapping of argument names to predicates
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        sig = inspect.signature(func)

        for name in predicate_map:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            bound = fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, pred in predicate_map.items():
                val = bound[name]
                if not pred(val):
                    raise ValueError(
                        f"{func.__qualname__}(): '{name}' failed constraint: "
                        f"{pred.msg}; got {_SHORT.repr(val)}"
                    )

            call_args, call_kwargs = to_call_args(bound, plan)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator
