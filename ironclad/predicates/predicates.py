"""
Some pre-made predicate functions for ease of use.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

import re
from types import UnionType
from typing import TYPE_CHECKING, Any, Protocol, Self, TypeAlias, TypeVar, get_args

if TYPE_CHECKING:
    from collections.abc import Iterable, Sized

    from ..types import ClassInfo

from .predicate import Predicate

__all__ = [
    "ALWAYS",
    "NEGATIVE",
    "NEVER",
    "NON_EMPTY",
    "NOT_NONE",
    "POSITIVE",
    "between",
    "equals",
    "instance_of",
    "length",
    "one_of",
    "regex",
]


class _Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...
    def __le__(self, other: Self, /) -> bool: ...
    def __gt__(self, other: Self, /) -> bool: ...
    def __ge__(self, other: Self, /) -> bool: ...


C = TypeVar("C", bound=_Comparable)
T = TypeVar("T")

AnyRealNumber: TypeAlias = int | float


def _flatten_type(t: ClassInfo) -> list[type]:
    stack = [t]
    types: list[type] = []

    while stack:
        current = stack.pop()
        if isinstance(current, UnionType):
            stack.extend(get_args(current))
        elif isinstance(current, tuple):
            stack.extend(current)
        else:
            types.append(current)

    types.reverse()  # preserve original left to right order

    # dedupe
    seen: set[type] = set()
    out: list[type] = []
    for tp in types:
        if tp not in seen:
            seen.add(tp)
            out.append(tp)

    return out


# TODO: think about moving this to repr.py
def _class_info_to_str(t: ClassInfo, /) -> str:
    if isinstance(t, type):
        return t.__name__
    return " | ".join(tp.__name__ for tp in _flatten_type(t))


ALWAYS: Predicate[Any] = Predicate(lambda _: True, "always", "always true")
NEVER: Predicate[Any] = Predicate(lambda _: False, "never", "always false")


# --- simple predicates ---
def equals(value: T) -> Predicate[T]:
    """A predicate that checks if a value is equal to another.

    Args:
        value (T): The value to store and use to check against.

    Returns:
        Predicate[T]: A predicate that checks if a value is equal to another.
    """
    return Predicate(lambda x: x == value, "equals", lambda _: f"expected == {value!r}")


def between(low: C, high: C, /, *, inclusive: bool = True) -> Predicate[C]:
    """A predicate that checks if a value is within a range of values.

    Args:
        low (C): The lower bound (must be comparable).
        high (C): The upper bound (must be comparable).
        inclusive (bool, optional): Whether the bounds are inclusive.
            Defaults to True.

    Returns:
        Predicate[C]: A predicate that checks if the given value
            is in the valid range.
    """
    if inclusive:
        return Predicate(
            lambda x: low <= x <= high,
            "between",
            lambda _: f"expected {low!r} <= x <= {high!r}",
        )
    return Predicate(
        lambda x: low < x < high,
        "between",
        lambda _: f"expected {low!r} < x < {high!r}",
    )


def instance_of(t: ClassInfo) -> Predicate[object]:
    """A predicate that checks if a value is an instance of a type/types.

    Args:
        t (ClassInfo): The type/types to check.

    Returns:
        Predicate[object]: A predicate that checks if a value is an instance of a type.
    """
    return Predicate(
        lambda x: isinstance(x, t),
        "instance of",
        lambda _: f"expected instance of {_class_info_to_str(t)}",
    )


NOT_NONE = Predicate[Any](
    lambda x: x is not None, "not None", lambda _: "expected a not-None value"
)
"""A predicate that checks if a value is not None.
"""


# --- numeric predicates ---
POSITIVE = Predicate[AnyRealNumber](
    lambda x: x > 0, "positive", lambda _: "expected a positive number"
)
"""A predicate that checks if a number is positive.
"""

NEGATIVE = Predicate[AnyRealNumber](
    lambda x: x < 0, "negative", lambda _: "expected a negative number"
)
"""A predicate that checks if a number is negative.
"""


# --- combinations ---
def all_of(*predicates: Predicate[T]) -> Predicate[T]:
    """Combine multiple predicates, merging their conditions with an 'AND'.

    Args:
        predicates (Predicate[T]): The predicates to merge.

    Raises:
        ValueError: If there are no predicates given.

    Returns:
        Predicate[T]: The combined predicate.
    """
    if len(predicates) < 1:
        raise ValueError("Cannot create a combined predicate from 0 predicates.")
    final = predicates[0]
    for pred in predicates[1::]:
        final = final & pred
    return final


def any_of(*predicates: Predicate[T]) -> Predicate[T]:
    """Combine multiple predicates, merging their conditions with an 'OR'.

    Args:
        predicates (Predicate[T]): The predicates to merge.

    Raises:
        ValueError: If there are no predicates given.

    Returns:
        Predicate[T]: The combined predicate.
    """
    if len(predicates) < 1:
        raise ValueError("Cannot create a combined predicate from 0 predicates.")
    final = predicates[0]
    for pred in predicates[1::]:
        final = final | pred
    return final


# --- sequence predicates ---
def one_of(
    values: Iterable[T],  # pylint:disable=redefined-outer-name
    /,
) -> Predicate[T]:
    """A predicate that checks if a value is one of the values in an iterable.

    Args:
    values (Iterable[T]): The iterable of valid values.

    Returns:
        Predicate[T]: A predicate that checks if the given value
            is in the iterable of valid values.
    """
    return Predicate(
        lambda x: x in values,
        "one of",
        lambda _: f"expected one of {values!r}",
    )


def length(size: int, /) -> Predicate[Sized]:
    """A predicate that checks if the given value has a size matching the given length.

    Args:
        size (int): The approved length of the sized object.

    Returns:
        Predicate[Sized]: A predicate that checks
            if the object's size matches the length.
    """
    return Predicate(
        lambda s: len(s) == size,
        "length",
        lambda _: "expected sized object with length " + str(size),
    )


def length_between(
    low: int, high: int, /, *, inclusive: bool = True
) -> Predicate[Sized]:
    """A predicate that checks if the size of a sized object is within a range of sizes.

    Args:
        low (int): The lower bound.
        high (int): The upper bound.
        inclusive (bool, optional): Whether the bounds are inclusive.
            Defaults to True.

    Returns:
        Predicate[Sized]: A predicate that checks if the size of
            a given sized object is in the valid range.
    """
    if inclusive:
        return Predicate(
            lambda i: low <= len(i) <= high,
            "between",
            lambda _: f"expected {low!r} <= len(it) <= {high!r}",
        )
    return Predicate(
        lambda i: low < len(i) < high,
        "between",
        lambda _: f"expected {low!r} < len(it) < {high!r}",
    )


NON_EMPTY = (
    (~length(0))
    .with_name("non empty")
    .with_msg(lambda _: "expected non empty sized object")
)
"""A predicate that checks if the given value is sized and non empty.
"""


# --- string predicates ---
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
        lambda s: rx.fullmatch(s) is not None,
        "regex",
        lambda _: f"expected value to match regex/{pattern}/ with {flags} flags",
    )
