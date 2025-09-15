"""
The predicate class.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Never

if TYPE_CHECKING:
    from collections.abc import Callable


class Predicate:
    """A predicate, containing a predicate function and a failure message.

    Predicates can be modified/combined using
    the logical operators and ('&'), or ('|'), and not ('~').
    """

    __slots__ = ("__func", "__msg")

    def __init__(
        self, func: Callable[[Any], bool], msg: str | Callable[[Any], str], /
    ) -> None:
        """A predicate, containing a predicate function and a failure message.

        Args:
            func (Callable[[Any], bool]): The function that accepts or rejects values.
            msg (str | Callable[[Any], str]): The rejection message or message supplier.
        """
        self.__func = func
        self.__msg = msg

    # --- core ---
    def __call__(self, x: Any) -> bool:
        """Evaluate this predicate with a value.

        Args:
            x (Any): Value to pass to the predicate.

        Returns:
            bool: Whether the given value is accepted by this predicate.
        """
        return bool(self.__func(x))

    def render_msg(self, x: Any = None) -> str:
        """Render this predicate's message with a given input value.

        Args:
            x (Any): The value given to the predicate.

        Returns:
            str: The formatted message with the given test value.
        """
        m = self.__msg
        return m(x) if callable(m) else str(m).format(x=x)

    # --- diagnostics / ergonomics ---
    def explain(self, x: Any) -> str | None:
        """Explain this predicate's output for x.

        Args:
            x (Any): The value to test.

        Returns:
            str | None: None if ok, otherwise an explanation
                of why this predicate will fail for x.
        """
        return None if self(x) else self.render_msg(x)

    def validate(
        self, x: Any, *, label: str = "value", exc: type[Exception] = ValueError
    ) -> Any:
        """Return x if ok, otherwise raise an error with useful context.

        Args:
            x (Any): The value to test.
            label (str, optional): A label for the tested value. Defaults to "value".
            exc (type[Exception], optional): The exception to raise on failure.
                Defaults to ValueError.

        Returns:
            Any: x if the predicate accepts it.
        """
        if not self(x):
            raise exc(f"{label}: {self.render_msg(x)} (got {x!r})")
        return x

    def with_msg(self, msg: str | Callable[[Any], str]) -> Predicate:
        """Clone this predicate and give it a new message.

        Args:
            msg (str | Callable[[Any], str]): The new message.

        Returns:
            Predicate: The cloned predicate with the new message.
        """
        return Predicate(self.__func, msg)

    # --- combinators ---
    # pylint: disable=protected-access
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
            return NotImplemented

        return Predicate(
            lambda x: self(x) and other(x),
            lambda x: f"({self.render_msg(x)}) and ({other.render_msg(x)})",
        )

    # pylint: disable=protected-access
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
            return NotImplemented

        return Predicate(
            lambda x: self(x) or other(x),
            lambda x: f"({self.render_msg(x)}) or ({other.render_msg(x)})",
        )

    def __invert__(self) -> Predicate:
        """Invert this predicate.

        Returns:
            Predicate: The inverted predicate.
        """
        return Predicate(lambda x: not self(x), lambda x: f"not ({self.render_msg(x)})")

    __rand__ = __and__
    __ror__ = __or__

    def implies(self, other: Predicate) -> Predicate:
        """A predicate which checks that this predicate implies another predicate.

        Args:
            other (Predicate): The predicate to imply.

        Raises:
            TypeError: If the other value is not a Predicate.

        Returns:
            Predicate: The implication predicate.
        """
        return (~self) | other

    # --- lifters ---
    def all(self) -> Predicate:
        """Lift this predicate to check if every element in an iterable is accepted.

        Returns:
            Predicate: The new predicate.
        """
        return Predicate(
            lambda i: all(self(e) for e in i),
            lambda i: f"every element: {self.render_msg('<elem>')}",
        )

    def any(self) -> Predicate:
        """Lift this predicate to check if any element in an iterable is accepted.

        Returns:
            Predicate: The new predicate.
        """
        return Predicate(
            lambda i: any(self(e) for e in i),
            lambda i: f"at least one element: {self.render_msg('<elem>')}",
        )

    # --- safety / debugging ---
    def __bool__(self) -> Never:
        """Raise a TypeError if a predicate object is converted to a bool.

        Raises:
            TypeError: If this function is called
        """
        raise TypeError(
            "Predicate has no truth value; make sure to call it with a value"
        )

    def __repr__(self) -> str:
        """Get a representation of this predicate.

        Returns:
            str: The repr.
        """
        fn = getattr(self.__func, "__name__", repr(self.__func))
        return f"Predicate(func={fn}, msg={self.__msg!r})"
