"""
Some pre-made predicate functions for ease of use.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

from ..repr import type_repr
from ..types import DEFAULT_ENFORCE_OPTIONS
from .compile import matches_hint
from .predicate import Predicate


class _Comparable(Protocol):
    def __lt__(self, other: _Comparable) -> bool: ...
    def __le__(self, other: _Comparable) -> bool: ...
    def __gt__(self, other: _Comparable) -> bool: ...
    def __ge__(self, other: _Comparable) -> bool: ...


_C = TypeVar("_C", bound=_Comparable)


def _ensure_pred(inner: Callable[[Any], bool] | Predicate | Any, /) -> Predicate:
    if isinstance(inner, Predicate):
        return inner

    # prefer typing-aware matcher
    return Predicate(
        lambda x: matches_hint(x, inner, DEFAULT_ENFORCE_OPTIONS),
        f"'{type_repr(inner)}'",
    )


def one_of(
    values: Iterable[Any],  # pylint:disable=redefined-outer-name
    /,
) -> Predicate:
    """A predicate that checks if a value is in an iterable.

    Args:
    values (Iterable[Any]): The iterable of valid values.

    Returns:
        Predicate: A predicate that checks if the given value
            is in the iterable of valid values.
    """
    s = set(values)
    return Predicate(lambda x: x in s, f"one of {sorted(s)}")


def between(low: _C, high: _C, /, *, inclusive: bool = True) -> Predicate:
    """A predicate that checks if a value is within a range of values.

    Args:
        low (_C): The lower bound (must be comparable).
        high (_C): The upper bound (must be comparable).
        inclusive (bool, optional): Whether the endpoints are inclusive.
            Defaults to True.

    Returns:
        Predicate: A predicate that checks if the given value
            is in the valid range.
    """
    if inclusive:
        return Predicate(
            lambda x: low <= x <= high, f"between {low} and {high}, inclusive"
        )
    return Predicate(lambda x: low < x < high, f"between {low} and {high}, exclusive")


def non_empty() -> Predicate:
    """A predicate that checks if the given value is sized and is not empty.

    Returns:
        Predicate: A predicate that checks if the given value is sized and not empty.
    """
    return Predicate(lambda x: hasattr(x, "__len__") and len(x) > 0, "non empty")


def regex(pattern: str, flags: int = 0) -> Predicate:
    """A predicate that checks if a string matches the given regex.

    Args:
        pattern (str): The regex pattern.
        flags (int, optional): The number of flags, by default 0.

    Returns:
        Predicate: A predicate that checks if a string matches the given regex.
    """
    rx = re.compile(pattern, flags)
    return Predicate(
        lambda x: isinstance(x, str) and rx.fullmatch(x) is not None,
        f"matches regex/{pattern}/",
    )


def each(inner: Callable[[Any], bool] | Predicate, /) -> Predicate:
    """A predicate that checks if every item in an iterable is accepted by a predicate.

    This predicate does not treat strings, bytes, or bytearrays as iterables;
    they should instead be converted to another iterable type.

    Args:
        inner (Callable[[Any], bool] | Predicate): The inner predicate.

    Returns:
        Predicate: A predicate that checks if all the elements
            in an iterable are accepted by the predicate.
    """
    pred = _ensure_pred(inner)

    def _check(it: Iterable[Any]) -> bool:
        if isinstance(it, (str, bytes, bytearray)):
            return False
        try:
            iterator = iter(it)
        except TypeError:
            return False
        return all(pred(ele) for ele in iterator)

    return Predicate(_check, f"all elements are {pred.msg}")


def keys(inner: Callable[[Any], bool] | Predicate, /) -> Predicate:
    """A predicate that checks if every key in a dictionary is accepted by a predicate.

    Args:
        inner (Callable[[Any], bool] | Predicate): The inner predicate.

    Returns:
        Predicate: A predicate that checks if every key
            in a dictionary is accepted by a predicate.
    """
    pred = _ensure_pred(inner)
    return Predicate(
        lambda d: all(pred(key) for key in getattr(d, "keys", list)()),
        f"for each key: {pred.msg}",
    )


def values(inner: Callable[[Any], bool] | Predicate, /) -> Predicate:
    """A predicate that checks if every value in a dict is accepted by a predicate.

    Args:
        inner (Callable[[Any], bool] | Predicate): The inner predicate.

    Returns:
        Predicate: A predicate that checks if every value
            in a dict is accepted by a predicate.
    """
    pred = _ensure_pred(inner)
    return Predicate(
        lambda d: all(pred(val) for val in getattr(d, "values", list)()),
        f"for each value: {pred.msg}",
    )


def items(
    key_predicate: Callable[[Any], bool] | Predicate,
    value_predicate: Callable[[Any], bool] | Predicate,
    /,
) -> Predicate:
    """A predicate that checks if every item in a dict is accepted by the predicates.

    Args:
        key_predicate (Callable[[Any], bool] | Predicate):
            The predicate for the keys.
        value_predicate (Callable[[Any], bool] | Predicate):
            The predicate for the values.

    Returns:
        Predicate: A predicate that checks if every item
            in a dict is accepted by the predicates.
    """
    key_validator = (
        key_predicate
        if isinstance(key_predicate, Predicate)
        else Predicate(key_predicate, "predicate")
    )
    val_validator = (
        value_predicate
        if isinstance(value_predicate, Predicate)
        else Predicate(value_predicate, "predicate")
    )
    return Predicate(
        lambda d: hasattr(d, "items")
        and all(key_validator(k) and val_validator(v) for k, v in d.items()),
        f"for each key: {key_validator.msg} and for each value: {val_validator.msg}",
    )
