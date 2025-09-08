"""predicates.py

Some pre-made predicate functions for ease of use with enforce_values.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol, TypeVar, Union

from .repr import type_repr


class _Comparable(Protocol):
    def __lt__(self, other: "_Comparable") -> bool: ...
    def __le__(self, other: "_Comparable") -> bool: ...
    def __gt__(self, other: "_Comparable") -> bool: ...
    def __ge__(self, other: "_Comparable") -> bool: ...


_C = TypeVar("_C", bound=_Comparable)


@dataclass(frozen=True)
class Predicate:
    """An object representing a predicate, containing a predicate function and a failure message.

    Predicates can be modified/combined using the logical operators 'and', 'or', and 'not'.
    """

    func: Callable[[Any], bool]
    """Predicate function that determines if a value is accepted by this predicate or not."""
    msg: str = "predicate failed"
    """A message representing this predicate."""

    def __call__(self, x: Any) -> bool:
        return self.func(x)

    def __and__(self, other: Any) -> "Predicate":
        if not isinstance(other, Predicate):
            raise TypeError(
                f"Cannot perform logical operations on 'Predicate' and '{type(other).__name__}'"
            )

        return Predicate(lambda x: self(x) and other(x), f"{self.msg} and {other.msg}")

    def __or__(self, other: Any) -> "Predicate":
        if not isinstance(other, Predicate):
            raise TypeError(
                f"Cannot perform logical operations on 'Predicate' and '{type(other).__name__}'"
            )

        return Predicate(lambda x: self(x) or other(x), f"{self.msg} or {other.msg}")

    def __invert__(self):
        return Predicate(lambda x: not self(x), f"not ({self.msg})")


def _ensure_pred(inner: Union[Predicate, Callable[[Any], bool], Any], /) -> Predicate:
    if isinstance(inner, Predicate):
        return inner

    # lazy import to prevent circular import
    from ._util import matches_hint  # pylint:disable=import-outside-toplevel
    from .types import DEFAULT_ENFORCE_OPTIONS  # pylint:disable=import-outside-toplevel

    # prefer typing-aware matcher
    return Predicate(
        lambda x: matches_hint(x, inner, DEFAULT_ENFORCE_OPTIONS),
        f"'{type_repr(inner)}'",
    )


def one_of(
    values: Iterable[Any], /  # pylint:disable=redefined-outer-name
) -> Predicate:
    """Create a predicate that checks if a value is in the given iterable.

    Parameters
    ----------
    values : Iterable[Any]
        The iterable of valid values

    Returns
    -------
    Predicate
        A predicate that checks if the given value is in the iterable of valid values
    """

    s = set(values)
    return Predicate(lambda x: x in s, f"one of {sorted(s)}")


def between(low: _C, high: _C, /, *, inclusive: bool = True) -> Predicate:
    """Create a predicate that checks if a value is between two values.

    Parameters
    ----------
    low : _C (_Comparable)
        The lower bound (must be comparable)
    high : _C (_Comparable)
        The upper bound (must be comparable)
    inclusive : bool, optional
        Whether the endpoints are inclusive, by default True

    Returns
    -------
    Predicate
        A predicate that checks if the given value is in the iterable of valid values
    """

    if inclusive:
        return Predicate(
            lambda x: low <= x <= high, f"between {low} and {high}, inclusive"
        )
    return Predicate(lambda x: low < x < high, f"between {low} and {high}, exclusive")


def non_empty() -> Predicate:
    """Create a predicate that checks if the given value is sized and is not empty.

    Returns
    -------
    Predicate
        A predicate that checks if the given value is sized and not empty
    """

    return Predicate(lambda x: hasattr(x, "__len__") and len(x) > 0, "non empty")


def regex(pattern: str, flags: int = 0) -> Predicate:
    """Create a predicate that checks if a string matches the given regex.

    Parameters
    ----------
    pattern : str
        The regex pattern
    flags : int, optional
        The number of flags, by default 0

    Returns
    -------
    Predicate
        A predicate that checks if a string matches the given regex.
    """

    rx = re.compile(pattern, flags)
    return Predicate(
        lambda x: isinstance(x, str) and rx.fullmatch(x) is not None,
        f"matches regex/{pattern}/",
    )


def each(inner: Union[Predicate, Callable[[Any], bool]], /) -> Predicate:
    """Create a predicate that checks if all the elements
    in a given iterable match the given predicate.

    This predicate does not treat strings, bytes, or bytearrays as iterables;
    they should instead be converted to another iterable type.

    Parameters
    ----------
    inner : Predicate | Callable[[Any], bool]
        The inner predicate

    Returns
    -------
    Predicate
        A predicate that checks if all the elements in an iterable match the given predicate.
    """

    pred = _ensure_pred(inner)

    def _check(it):
        if isinstance(it, (str, bytes, bytearray)):
            return False
        try:
            iterator = iter(it)
        except TypeError:
            return False
        return all(pred(ele) for ele in iterator)

    return Predicate(_check, f"all elements are {pred.msg}")


def keys(inner: Union[Predicate, Callable[[Any], bool]], /) -> Predicate:
    """Create a predicate that checks if all the keys
    in a given dictionary match the given predicate.

    Parameters
    ----------
    inner : Predicate | Callable[[Any], bool]
        The inner predicate

    Returns
    -------
    Predicate
        A predicate that checks if all the keys in a given dictionary match the given predicate.
    """

    pred = _ensure_pred(inner)
    return Predicate(
        lambda d: all(pred(key) for key in getattr(d, "keys", lambda: [])()),
        f"for each key: {pred.msg}",
    )


def values(inner: Union[Predicate, Callable[[Any], bool]], /) -> Predicate:
    """Create a predicate that checks if all the values
    in a given dictionary match the given predicate.

    Parameters
    ----------
    inner : Predicate | Callable[[Any], bool]
        The inner predicate

    Returns
    -------
    Predicate
        A predicate that checks if all the values in a given dictionary match the given predicate.
    """

    pred = _ensure_pred(inner)
    return Predicate(
        lambda d: all(pred(val) for val in getattr(d, "values", lambda: [])()),
        f"for each value: {pred.msg}",
    )


def items(
    key_predicate: Union[Predicate, Callable[[Any], bool]],
    value_predicate: Union[Predicate, Callable[[Any], bool]],
    /,
) -> Predicate:
    """Create a predicate that checks if all the items
    in a given dictionary match the given predicates.

    Parameters
    ----------
    key_predicate : Union[Predicate, Callable[[Any], bool]]
        The predicate for the keys
    value_predicate : Union[Predicate, Callable[[Any], bool]]
        The predicate for the values

    Returns
    -------
    Predicate
        A predicate that checks if all the items in a given dictionary match the given predicates.
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
