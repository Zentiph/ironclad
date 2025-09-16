"""
Some pre-made predicate functions for ease of use.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol, Self, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Sized

from ..repr import type_repr
from ..types import DEFAULT_ENFORCE_OPTIONS
from .compile import matches_hint
from .predicate import Predicate


class _Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...
    def __le__(self, other: Self, /) -> bool: ...
    def __gt__(self, other: Self, /) -> bool: ...
    def __ge__(self, other: Self, /) -> bool: ...


C = TypeVar("C", bound=_Comparable)
T = TypeVar("T")


def _ensure_pred(inner: Callable[[T], bool] | Predicate[T] | Any, /) -> Predicate[T]:
    if isinstance(inner, Predicate):
        return inner

    # prefer typing-aware matcher
    return Predicate[T](
        lambda x: matches_hint(x, inner, DEFAULT_ENFORCE_OPTIONS),
        "predicate",
        f"'{type_repr(inner)}'",
    )


ALWAYS: Predicate[Any] = Predicate(lambda x: True, "always", "always true")
NEVER: Predicate[Any] = Predicate(lambda x: False, "never", "always false")


def equals(value: T) -> Predicate[T]:
    """A predicate that checks if a value is equal to another.

    Args:
        value (T): The value to store and use to check against.

    Returns:
        Predicate[T]: A predicate that checks if a value is equal to another.
    """
    return Predicate(lambda x: x == value, "equals", lambda x: f"expected == {value!r}")


def is_in(
    values: Iterable[T],  # pylint:disable=redefined-outer-name
    /,
) -> Predicate[T]:
    """A predicate that checks if a value is in an iterable.

    Args:
    values (Iterable[T]): The iterable of valid values.

    Returns:
        Predicate[T]: A predicate that checks if the given value
            is in the iterable of valid values.
    """
    return Predicate(
        lambda x: x in values,
        "is in",
        lambda x: f"expected one of {tuple(values)!r}",
    )


def between(low: C, high: C, /, *, inclusive: bool = True) -> Predicate[C]:
    """A predicate that checks if a value is within a range of values.

    Args:
        low (C): The lower bound (must be comparable).
        high (C): The upper bound (must be comparable).
        inclusive (bool, optional): Whether the endpoints are inclusive.
            Defaults to True.

    Returns:
        Predicate[C]: A predicate that checks if the given value
            is in the valid range.
    """
    if inclusive:
        return Predicate(
            lambda x: low <= x <= high,
            "between",
            lambda x: f"expected {low!r} <= x <= {high!r}",
        )
    return Predicate(
        lambda x: low < x < high,
        "between",
        lambda x: f"expected {low!r} < x < {high!r}",
    )


def is_instance(t: type | tuple[type, ...]) -> Predicate[object]:
    """A predicate that checks if a value is an instance of a type/types.

    Args:
        t (type | tuple[type, ...]): The type/types to check.

    Returns:
        Predicate[object]: A predicate that checks if a value is an instance of a type.
    """
    type_name = (
        " | ".join(tn.__name__ for tn in t) if isinstance(t, tuple) else t.__name__
    )
    return Predicate(
        lambda x: isinstance(x, t),
        "is instance",
        lambda x: f"expected instance of {type_name}",
    )


def non_empty() -> Predicate[Sized]:
    """A predicate that checks if the given value is sized and is not empty.

    Returns:
        Predicate: A predicate that checks if the given value is sized and not empty.
    """
    return Predicate(
        lambda x: hasattr(x, "__len__") and len(x) > 0,
        "non empty",
        lambda x: "expected non empty sized object",
    )


def regex(pattern: str, flags: int = 0) -> Predicate[str]:
    """A predicate that checks if a string matches the given regex.

    Args:
        pattern (str): The regex pattern.
        flags (int, optional): The number of flags, by default 0.

    Returns:
        Predicate[str]: A predicate that checks if a string matches the given regex.
    """
    rx = re.compile(pattern, flags)
    return Predicate(
        lambda x: rx.fullmatch(x) is not None,
        "regex",
        lambda x: f"expected value to match regex/{pattern}/",
    )


def keys(
    inner: Callable[[Hashable], bool] | Predicate[Hashable], /
) -> Predicate[Iterable[Hashable]]:
    """A predicate that checks if every key in a dictionary is accepted by a predicate.

    Args:
        inner (Callable[[Hashable], bool] | Predicate[Hashable]): The inner predicate.

    Returns:
        Predicate[Iterable[Hashable]]: A predicate that checks if every key
            in a dictionary is accepted by a predicate.
    """
    pred: Predicate[Hashable] = _ensure_pred(inner)
    return Predicate.lift_from(
        pred,
        lambda d: all(pred(key) for key in getattr(d, "keys", list)()),
        "keys",
        lambda x: f"every key: ({pred.render_msg()})",
    )


def values(inner: Callable[[T], bool] | Predicate[T], /) -> Predicate[Iterable[T]]:
    """A predicate that checks if every value in a dict is accepted by a predicate.

    Args:
        inner (Callable[[T], bool] | Predicate[T]): The inner predicate.

    Returns:
        Predicate[T]: A predicate that checks if every value
            in a dict is accepted by a predicate.
    """
    pred: Predicate[T] = _ensure_pred(inner)
    return Predicate.lift_from(
        pred,
        lambda d: all(pred(val) for val in getattr(d, "values", list)()),
        "values",
        lambda x: f"every value: ({pred.render_msg()})",
    )


def items(
    key_predicate: Callable[[Hashable], bool] | Predicate[Hashable],
    value_predicate: Callable[[T], bool] | Predicate[T],
    /,
) -> Predicate[dict[Hashable, T]]:
    """A predicate that checks if every item in a dict is accepted by the predicates.

    Args:
        key_predicate (Callable[[Hashable], bool] | Predicate[Hashable]):
            The predicate for the keys.
        value_predicate (Callable[[T], bool] | Predicate[T]):
            The predicate for the values.

    Returns:
        Predicate[tuple[Hashable, T]]: A predicate that checks if every item
            in a dict is accepted by the predicates.
    """
    key_validator = keys(key_predicate)
    val_validator = values(value_predicate)

    return Predicate(
        lambda d: hasattr(d, "keys")
        and hasattr(d, "values")
        and key_validator(d.keys())
        and val_validator(d.values()),
        "items",
        lambda kv: f"every item: ({key_validator.render_msg()}, "
        + val_validator.render_msg()
        + ")",
    )
