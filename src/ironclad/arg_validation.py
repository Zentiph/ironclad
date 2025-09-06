"""arg_validation.py

Argument validation functions, including type and value enforcing.
"""

import functools
import inspect
from typing import Callable, ParamSpec, Tuple, Type, TypeVar, Union

P = ParamSpec("P")
T = TypeVar("T")


def enforce_types(
    **type_map: Union[Type, Tuple[Type, ...]],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that enforces the types of function parameters.

    Arguments
    ---------
    type_map : Type | Tuple[Type, ...]
        A dictionary mapping argument names to expected type(s)
    """

    def decorator(func):
        sig = inspect.signature(func)

        # validate all arguments given exist in the function signature
        for arg_name in type_map:
            if arg_name not in sig.parameters:
                raise ValueError(
                    f"Argument to enforce '{arg_name}' not found "
                    + f"in function signature of '{func.__name__}'"
                )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for arg_name, type_or_tuple in type_map.items():
                arg_value = bound_args.arguments[arg_name]
                if not isinstance(arg_value, type_or_tuple):
                    # convert the type(s) to a string
                    # if a tuple of types, join each type around " or "
                    type_string = (
                        type_or_tuple.__name__
                        if isinstance(type_or_tuple, type)
                        else " or ".join(t.__name__ for t in type_or_tuple)
                    )

                    raise TypeError(
                        f"Argument '{arg_name}' must be of type '{type_string}' or a subclass, "
                        + f"not '{type(arg_value).__name__}'"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator
