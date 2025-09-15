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


ALWAYS = Predicate(lambda x: True, "always true")
NEVER = Predicate(lambda x: False, "always false")


def equals(value: Any) -> Predicate:
    """A predicate that checks if a value is equal to another.

    Args:
        value (Any): The value to store and use to check against.

    Returns:
        Predicate: A predicate that checks if a value is equal to another.
    """
    return Predicate(lambda x: x == value, lambda x: f"expected == {value!r}")


def is_in(
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
    return Predicate(
        lambda x: x in s, lambda x: f"expected one of {tuple(sorted(s))!r}"
    )


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
            lambda x: low <= x <= high, lambda x: f"expected {low!r} <= x <= {high!r}"
        )
    return Predicate(
        lambda x: low < x < high, lambda x: f"expected {low!r} < x < {high!r}"
    )


def is_instance(t: type | tuple[type, ...]) -> Predicate:
    """A predicate that checks if a value is an instance of a type/types.

    Args:
        t (type | tuple[type, ...]): The type/types to check.

    Returns:
        Predicate: A predicate that checks if a value is an instance of a type/types.
    """
    return Predicate(
        lambda x: isinstance(x, t), lambda x: f"expected instance of {t!r}"
    )


def non_empty() -> Predicate:
    """A predicate that checks if the given value is sized and is not empty.

    Returns:
        Predicate: A predicate that checks if the given value is sized and not empty.
    """
    return Predicate(
        lambda x: hasattr(x, "__len__") and len(x) > 0,
        lambda x: "expected non empty sized object",
    )


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
        lambda x: f"expected value to match regex/{pattern}/",
    )


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
        lambda x: f"{pred.render_msg(x)} for each key",
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
        lambda x: f"{pred.render_msg(x)} for each value",
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
        lambda kv: f"{key_validator.render_msg(kv[0])}for each key "
        f"and {val_validator.render_msg(kv[1])} for each value",
    )
