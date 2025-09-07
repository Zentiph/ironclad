"""arg_validation.py

Argument validation functions, including type and value enforcing.
"""

import functools
import inspect
import reprlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    ParamSpec,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")

_SHORT = reprlib.Repr()
_SHORT.maxstring = 80
_SHORT.maxother = 80


@dataclass(frozen=True)
class EnforceOptions:
    allow_subclasses: bool = True
    check_defaults: bool = True
    strict_bools: bool = False


DEFAULT_ENFORCE_OPTIONS: EnforceOptions = EnforceOptions()


# pylint:disable=too-many-branches,too-many-return-statements
def _matches_hint(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
    if hint is Any:  # can be anything
        return True

    if hint is None or hint is type(None):  # hint is None, so x must be
        return x is None

    origin = get_origin(hint)

    if origin is Annotated:  # check if the base type matches
        base, *_ = get_args(hint)
        return _matches_hint(x, base, opts)

    if origin is Literal:  # see if x is a value in the literal
        return x in set(get_args(hint))

    if origin is type:  # see if x is a subclass of the type inside type[T]
        (t,) = get_args(hint) or (object,)
        return isinstance(x, type) and (t is object or issubclass(x, t))

    if origin is tuple:
        args = get_args(hint)
        if len(args) == 2 and args[1] is ...:  # any size tuple (tuple[T, ...])
            return isinstance(
                x, tuple
            ) and all(  # make sure all items inside the tuple match the type
                _matches_hint(elem, args[0], opts) for elem in x
            )
        return (
            isinstance(x, tuple)
            and len(x) == len(args)
            and all(  # make sure all items inside the tuple match the type
                _matches_hint(elem, ht, opts) for elem, ht in zip(x, args)
            )
        )

    if origin in (list, set, frozenset, Sequence):
        elem = (get_args(hint) or (Any,))[0]
        pytype = (
            list
            if origin is list
            else (
                set if origin is set else frozenset if origin is frozenset else Sequence
            )
        )
        return isinstance(x, pytype) and all(_matches_hint(e, elem, opts) for e in x)

    if origin in (dict, Mapping):
        k_hint, v_hint = get_args(hint) or (Any, Any)
        return isinstance(x, Mapping) and all(
            _matches_hint(k, k_hint, opts) and _matches_hint(v, v_hint, opts)
            for k, v in x.items()
        )

    if origin is Union:
        return any(_matches_hint(x, ht, opts) for ht in get_args(hint))

    if isinstance(hint, TypeVar):
        if hint.__constraints__:
            return any(_matches_hint(x, ht, opts) for ht in hint.__constraints__)
        if hint.__bound__:
            return _matches_hint(x, hint.__bound__, opts)
        return True

    try:  # normal classes/ABCs, @runtime_checkable Protocols
        if isinstance(hint, type):
            if not opts.allow_subclasses:
                return type(x) is hint  # pylint:disable=unidiomatic-typecheck
            # separate case for restriction on bools as ints
            if opts.strict_bools and hint is int:
                return type(x) is int  # pylint:disable=unidiomatic-typecheck

        return isinstance(x, hint)
    except TypeError:
        # fallback for typing objects on older Python versions
        return origin is not None and _matches_hint(x, origin, opts)


def enforce_types(
    options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    /,
    **type_map: Union[Type, Tuple[Type, ...]],
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator that enforces the types of function parameters.
    Supports typing types.

    Arguments
    ---------
    type_map : Type | Tuple[Type, ...]
        A dictionary mapping argument names to expected type(s)
    """

    def decorator(func):
        sig = inspect.signature(func)

        # validate all arguments given exist in the function signature
        for name in type_map:
            if name not in sig.parameters:
                raise ValueError(
                    f"Argument to enforce '{name}' not found "
                    + f"in function signature of '{func.__name__}'"
                )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            if options.check_defaults:
                bound.apply_defaults()

            for name, type_or_tuple_or_hint in type_map.items():
                val = bound.arguments[name]
                if not _matches_hint(val, type_or_tuple_or_hint, options):
                    # convert the type(s) to a string
                    # if a tuple of types, join each type around " or "
                    type_string = getattr(
                        type_or_tuple_or_hint, "__name__", str(type_or_tuple_or_hint)
                    )
                    raise TypeError(
                        f"{func.__qualname__}(): '{name}' expected type '{type_string}', "
                        + f"got '{type(val).__name__}' with value {_SHORT.repr(val)}"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator
