"""
The predicate class.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Predicate:
    """A predicate, containing a predicate function and a failure message.

    Predicates can be modified/combined using
    the logical operators and ('&'), or ('|'), and not ('~').
    """

    func: Callable[[Any], bool]
    """A function that determines if a value is accepted by this predicate or not."""
    msg: str = "predicate failed"
    """A message representing this predicate."""

    def __call__(self, x: Any) -> bool:
        """Evaluate this predicate with a value.

        Args:
            x (Any): Value to pass to the predicate.

        Returns:
            bool: Whether the given value is accepted by this predicate.
        """
        return self.func(x)

    def __and__(self, other: Any) -> Predicate:
        """Combine this predicate with another, merging their conditions with an 'AND'.

        Args:
            other (Any): The other predicate.

        Raises:
            TypeError: If the other object is not a Predicate.

        Returns:
            Predicate: The combined predicate.
        """
        if not isinstance(other, Predicate):
            raise TypeError(
                "Cannot perform logical operations on 'Predicate' and "
                f"'{type(other).__name__}'"
            )

        return Predicate(lambda x: self(x) and other(x), f"{self.msg} and {other.msg}")

    def __or__(self, other: Any) -> Predicate:
        """Combine this predicate with another, merging their conditions with an 'OR'.

        Args:
            other (Any): The other predicate.

        Raises:
            TypeError: If the other object is not a Predicate.

        Returns:
            Predicate: The combined predicate.
        """
        if not isinstance(other, Predicate):
            raise TypeError(
                "Cannot perform logical operations on 'Predicate' and "
                f"'{type(other).__name__}'"
            )

        return Predicate(lambda x: self(x) or other(x), f"{self.msg} or {other.msg}")

    def __invert__(self) -> Predicate:
        """Invert this predicate.

        Returns:
            Predicate: The inverted predicate.
        """
        return Predicate(lambda x: not self(x), f"not ({self.msg})")
