"""arg_validation.py

Argument validation functions, including type and value enforcing.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import functools
import inspect
import reprlib
from typing import (
    Callable,
    Dict,
    ParamSpec,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

from .predicates import Predicate
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions
from .util import (
    _fast_bind,
    _make_plan,
    _spec_contains_int,
    _to_call,
    as_predicate,
    matches_hint,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")

_SHORT = reprlib.Repr()
_SHORT.maxstring = 80
_SHORT.maxother = 80


def enforce_types(
    options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    /,
    **types: Union[Type, Tuple[Type, ...]],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    # pylint:disable=line-too-long
    """Decorator that enforces the types of function parameters.
    Supports typing types.

    Arguments
    ---------
    options : EnforceOptions, optional
        Any options to change how types are enforced, by default DEFAULT_ENFORCE_OPTIONS
    types : Type | Tuple[Type, ...]
        A mapping of argument names to expected type(s)

    Examples
    --------
    Basic usage:
    >>> from ironclad import enforce_types
    >>>
    >>> @enforce_types(enable=bool, limit=int)
    ... def config(enable, limit)
    ...     print("Config changed")
    ...
    >>> config(True, 10)
    Config changed
    >>> config(False, 2.3)
    Traceback (most recent call last):
      ...
    TypeError: config(): 'limit' expected 'int' (no bools as ints), got 'float' with value 2.3

    Type unions (native Python style and typing style):
    >>> from ironclad import enforce_types
    >>> from typing import Union
    >>>
    >>> @enforce_types(x=(int, float), y=Union[int, float])
    ... def add(x, y):
    ...     return x + y
    ...
    >>> add(2, 4.3)
    6.3
    >>> add(4.3, 2)
    6.3
    >>> add(3, "2.3")
    Traceback (most recent call last):
      ...
    TypeError: add(): 'y' expected 'int or float', got 'str' with value '2.3'

    Typing module support:
    >>> from ironclad import enforce_types
    >>> from typing import Literal
    >>>
    >>> @enforce_types(level=Literal[0, 1, 2, 3, 4], msg=str)
    ... def log(level, msg):
    ...     print("Logging...")
    ...
    >>> log(2, "Uh oh")
    Logging...
    >>> log(6, "BIG UH OH")
    Traceback (most recent call last):
      ...
    TypeError: log(): 'level' expected '0 or 1 or 2 or 3 or 4', got 'int' with value 6

    Typing args and kwargs with predicates:
    >>> from ironclad import enforce_types, predicates
    >>>
    >>> @enforce_types(nos=predicates.each(int), meta=predicates.values(str))
    >>> def sanitize(*nos, **meta):
    ...     print("Sanitizing...")
    ...
    >>> sanitize(1, 2, kw1="a")
    Sanitizing...
    >>> sanitize(1, "2", kw1="a")
    Traceback (most recent call last):
      ...
    TypeError: sanitize(): 'nos' expected all elements are 'int', got 'tuple' with value (1, '2')

    With options:
    >>> from ironclad import enforce_types, EnforceOptions
    >>>
    >>> class Super:
    ...     ...
    ...
    >>> class Sub(Super):
    ...     ...
    ...
    >>> options = EnforceOptions(allow_subclasses=False)
    >>> @enforce_types(options, obj=Super)
    ... def approve(obj):
    ...     print("No subclasses please!")
    ...
    >>> approve(Super())
    No subclasses please!
    >>> approve(Sub())
    Traceback (most recent call last):
      ...
    TypeError: approve(): 'obj' expected 'Super' (no subclasses), got 'Sub' with value <__main__.Sub object at 0x...>
    """

    def decorator(func: Callable[_P, _T]):
        sig = inspect.signature(func)

        # validate all arguments given exist in the function signature
        for name in types:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = _make_plan(sig)

        # compile once
        validators: Dict[str, Predicate] = {
            name: as_predicate(spec, options) for name, spec in types.items()
        }

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            bound = _fast_bind(plan, sig, args, kwargs, options.check_defaults)

            for name, pred in validators.items():
                val = bound[name]
                if not pred(val):
                    conditions = "("
                    if not options.allow_subclasses:
                        conditions += "no subclasses"
                    if options.strict_bools and any(
                        # only add bool info if there's an int in the types
                        _spec_contains_int(v)
                        for v in types.values()
                    ):
                        if not options.allow_subclasses:
                            conditions += ", "
                        conditions += "no bools as ints"
                    conditions += ")"

                    raise TypeError(
                        f"{func.__qualname__}(): '{name}' expected {pred.msg} "
                        + f"{conditions if conditions != "()" else ""}, "
                        + f"got '{type_repr(type(val))}' with value {_SHORT.repr(val)}"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def enforce_annotations(
    *, check_return: bool = True
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces the types of function parameters using the function's type hints.

    Parameters
    ----------
    check_return : bool, optional
        Whether to enforce the return type, by default True
    """

    def decorator(func: Callable[_P, _T]):
        hints = get_type_hints(func, include_extras=True)
        param_hints = {k: v for k, v in hints.items() if k != "return"}

        wrapped = enforce_types(**param_hints)(func)
        if not check_return or "return" not in hints:
            return wrapped

        @functools.wraps(wrapped)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            out = wrapped(*args, **kwargs)

            if not matches_hint(out, hints["return"], DEFAULT_ENFORCE_OPTIONS):
                raise TypeError(
                    f"{func.__qualname__}(): return expected "
                    + f"{type_repr(hints['return'])}, got {type_repr(type(out))}"
                )

            return out

        return wrapper

    return decorator


def coerce_types(
    **coercers: Callable[[object], object],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that coerces the types of function parameters using coercer functions.
    This decorator is particularly useful for coercing string arguments into their proper types
    when using CLI/ENV arguments, web handlers, enums, and JSONs.

    Parameters
    ----------
    coercers : Callable[[object], object]
        A mapping of argument names to coercer functions

    Example(s)
    ----------
    >>> import json
    >>>
    >>> @coerce_types(limit=int, threshold=float, config=json.loads)
    ... def run(limit, threshold, config):
    ...     print(repr(limit), repr(threshold), repr(config))
    ...
    >>> run(limit="10", threshold="0.25", config='{"retries": 3}')
    10 0.25 {'retries': 3}
    """

    def decorator(func: Callable[_P, _T]):
        sig = inspect.signature(func)
        plan = _make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            bound = _fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, coerce in coercers.items():
                if name in bound:
                    bound[name] = coerce(bound[name])

            # rebuild call args and invoke
            call_args, call_kwargs = _to_call(plan, bound)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator


def enforce_values(
    **predicate_map: Predicate,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces value constraints on function parameters."""

    def decorator(func: Callable[_P, _T]):
        sig = inspect.signature(func)

        for name in predicate_map:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = _make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            bound = _fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, pred in predicate_map.items():
                val = bound[name]
                if not pred(val):
                    raise ValueError(
                        f"{func.__qualname__}(): '{name}' failed constraint: "
                        + f"{pred.msg}; got {_SHORT.repr(val)}"
                    )

            call_args, call_kwargs = _to_call(plan, bound)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator
