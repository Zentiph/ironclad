"""
The predicate class.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Never, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

__all__ = ["Predicate"]

T = TypeVar("T")
U = TypeVar("U")
Obj = TypeVar("Obj", bound=object)


class Predicate(Generic[T]):
    """A predicate, containing a predicate function and a failure message.

    Predicates can be modified/combined using
    the logical operators and ('&'), or ('|'), and not ('~').
    """

    __slots__ = ("__context", "__func", "__msg", "__name")

    @overload
    def __init__(self, func: Callable[[T], bool], /, name: str, msg: str) -> None: ...
    @overload
    def __init__(
        self, func: Callable[[T], bool], /, name: str, msg: Callable[[T | None], str]
    ) -> None: ...
    @overload
    def __init__(
        self, func: Callable[[T], bool], /, name: str, msg: None = None
    ) -> None: ...
    def __init__(
        self,
        func: Callable[[T], bool],
        /,
        name: str,
        msg: str | Callable[[T | None], str] | None = None,
    ) -> None:
        """A predicate, containing a predicate function, a name, and a failure message.

        Args:
            func (Callable[[T], bool]): The function that accepts or rejects values.
            name (str): The name of the predicate.
            msg (str | Callable[[T | None], str] | None): The rejection message,
                message supplier, or None for a default message. Defaults to None.
        """
        self.__func = func
        self.__name = name
        self.__msg = msg if msg is not None else name
        # a stack containing other predicates that are context for this predicate
        # e.g. if a predicate, pred3, is lifted from pred2 which is lifted from pred1,
        #      the context of pred3 is [pred1, pred2]
        self.__context: tuple[Predicate[Any], ...] = ()

    # --- core --- #
    def __call__(self, x: T) -> bool:
        """Evaluate this predicate with a value.

        Args:
            x (T): Value to pass to the predicate.

        Returns:
            bool: Whether the given value is accepted by this predicate.
        """
        return bool(self.__func(x))

    # --- props --- #
    @property
    def func(self) -> Callable[[T], bool]:
        """Get the predicate function of this predicate object.

        Returns:
            Callable[[T], bool]: The predicate function.
        """
        return self.__func

    @property
    def name(self) -> str:
        """Get the name of this predicate.

        Returns:
            str: The name of this predicate.
        """
        return self.__name

    @property
    def msg(self) -> str | Callable[[T | None], str]:
        """Get the failure name of this predicate.

        Returns:
            str | Callable[[T | None], str]: The failure message of this predicate.
        """
        return self.__msg

    # --- pretty strings ---
    @overload
    def render_msg(self, x: T, /, *, max_chain: int = 6) -> str: ...
    @overload
    def render_msg(self, x: None = ..., /, *, max_chain: int = 6) -> str: ...
    def render_msg(self, x: T | None = None, /, *, max_chain: int = 6) -> str:
        """Render this predicate's message with a given input value.

        Args:
            x (T | None, optional): The value given to the predicate. Defaults to None.
            max_chain (int, optional): The maximum number of chains to report.
                Defaults to 6.

        Returns:
            str: The formatted message with the given test value.
        """
        return self.__add_context_to_msg(
            self.__render_msg_no_context(x), list(self.__context), max_chain=max_chain
        )

    @overload
    def render_tree(self, x: T, /) -> str: ...
    @overload
    def render_tree(self, x: None = ..., /) -> str: ...
    def render_tree(self, x: T | None = None, /) -> str:
        """Render this predicate's message with a given input value as a tree.

        Args:
            x (T | None, optional): The value given to the predicate. Defaults to None.

        Returns:
            str: The formatted tree with the given test value.
        """
        lines: list[str] = [f"{self.__name}: {self.__render_msg_no_context(x)}"]
        lines.extend(  # newest -> oldest top-down
            [
                # pylint:disable=protected-access
                f"\tfrom {pred.__name}: {pred.__render_msg_no_context(x)}"
                for pred in reversed(self.__context)
            ]
        )
        return "\n".join(lines)

    def __render_msg_no_context(self, x: T | None = None, /) -> str:
        m = self.__msg
        if callable(m):
            return m(x)

        s = str(m)
        try:
            return s.format(x=x)
        except KeyError:  # safeguard for missing format
            return s

    # pylint:disable=protected-access
    def __add_context_to_msg(
        self, msg: str, context: list[Predicate[Any]], /, *, max_chain: int = 6
    ) -> str:
        if not context:
            return msg

        chain = " -> ".join(
            "'" + pred.__name + "'" for pred in (*context[-max_chain + 1 :], self)
        )
        return f"{msg} [via {chain}]"

    def _set_context(self, context: tuple[Predicate[Any], ...]) -> None:
        self.__context = context

    # --- diagnostics --- #
    def explain(self, x: T) -> str | None:
        """Explain this predicate's output for x.

        Args:
            x (T): The value to test.

        Returns:
            str | None: None if ok, otherwise an explanation
                of why this predicate will fail for x.
        """
        return None if self(x) else self.render_msg(x)

    def validate(
        self, x: T, *, label: str = "value", exc: type[Exception] = ValueError
    ) -> T:
        """Return x if ok, otherwise raise an error with useful context.

        Args:
            x (T): The value to test.
            label (str, optional): A label for the tested value. Defaults to "value".
            exc (type[Exception], optional): The exception to raise on failure.
                Defaults to ValueError.

        Returns:
            T: x if the predicate accepts it.
        """
        if not self(x):
            raise exc(f"{label}: {self.render_msg(x)} (got {x!r})")
        return x

    # --- ergonomics --- #
    def with_name(self, name: str) -> Predicate[T]:
        """Clone this predicate and give it a new name.

        Args:
            name (str): The new name.

        Returns:
            Predicate[T]: The cloned predicate with the new name.
        """
        pred = Predicate(self.__func, name, self.__msg)
        pred._set_context(self.__context)
        return pred

    @overload
    def with_msg(self, msg: str) -> Predicate[T]: ...
    @overload
    def with_msg(self, msg: Callable[[T | None], str]) -> Predicate[T]: ...
    def with_msg(self, msg: str | Callable[[T | None], str]) -> Predicate[T]:
        """Clone this predicate and give it a new message.

        Args:
            msg (str | Callable[[T | None], str]): The new message.

        Returns:
            Predicate[T]: The cloned predicate with the new message.
        """
        pred = Predicate(self.__func, self.__name, msg)
        pred._set_context(self.__context)
        return pred

    # --- combinators ---
    # pylint: disable=protected-access
    def __and__(self, other: Predicate[T]) -> Predicate[T]:
        """Combine this predicate with another, merging their conditions with an 'AND'.

        Args:
            other (Predicate[T]): The other predicate.

        Returns:
            Predicate[T]: The combined predicate.
        """
        return Predicate(
            lambda x: self(x) and other(x),
            self.__name + " & " + other.__name,
            lambda x: f"({self.__render_msg_no_context(x)}) and "
            f"({other.__render_msg_no_context(x)})",
        )

    __rand__ = __and__

    # pylint: disable=protected-access
    def __or__(self, other: Predicate[T]) -> Predicate[T]:
        """Combine this predicate with another, merging their conditions with an 'OR'.

        Args:
            other (Predicate[T]): The other predicate.

        Returns:
            Predicate[T]: The combined predicate.
        """
        return Predicate(
            lambda x: self(x) or other(x),
            self.__name + " | " + other.__name,
            lambda x: f"({self.__render_msg_no_context(x)}) or "
            f"({other.__render_msg_no_context(x)})",
        )

    __ror__ = __or__

    def __invert__(self) -> Predicate[T]:
        """Invert this predicate.

        Returns:
            Predicate[T]: The inverted predicate.
        """
        return Predicate(
            lambda x: not self(x),
            "~" + self.__name,
            lambda x: f"not ({self.__render_msg_no_context(x)})",
        )

    negate = __invert__

    def implies(self, other: Predicate[T]) -> Predicate[T]:
        """A predicate which checks that this predicate implies another predicate.

        Args:
            other (Predicate[T]): The predicate to imply.

        Returns:
            Predicate[T]: The implication predicate.
        """
        return (~self) | other

    # --- lifters ---
    @overload
    def lift(
        self,
        func: Callable[[T], bool],
        /,
        name: str | None,
        msg: str | Callable[[T | None], str],
    ) -> Predicate[T]: ...
    @overload
    def lift(
        self,
        func: Callable[[U], bool],
        /,
        name: str | None,
        msg: str | Callable[[U | None], str],
    ) -> Predicate[U]: ...
    def lift(
        self,
        func: Callable[[Any], bool],
        /,
        name: str | None,
        msg: str | Callable[[Any | None], str],
    ) -> Predicate[Any]:
        """Lift this predicate to create a new one.

        This is the ideal way to create a predicate based on another one, because
        this method adds the previous predicate to the new predicate's failure context.


        Args:
            func (Callable[[Any], bool]): The new predicate function.
            name (str | None): The new predicate's name.
                Copies the old one if None.
            msg (str | Callable[[Any | None], str], None):
                The new predicate's failure message.

        Returns:
            Predicate[Any]: The lifted predicate.
        """
        if name is None:
            name = self.__name

        pred = Predicate(func, name, msg)
        pred._set_context((*self.__context, self))
        return pred

    def on(
        self,
        getter: Callable[[Obj], T],
        /,
    ) -> Predicate[Obj]:
        """Modify this predicate to check if a property of an object validates it.

        Args:
            getter (Callable[[Obj], T]): function to access the property of an object.

        Returns:
            Predicate[Obj]: The new predicate.
        """
        return Predicate(
            lambda o: self.__func(getter(o)),
            self.__name,
            lambda o: self.__render_msg_no_context(
                getter(o) if o is not None else None
            ),
        )

    # TODO: there's gotta be a better way to do this
    def all(self) -> Predicate[Iterable[T]]:
        """Modify this predicate to check if every element in an iterable is accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.
        """

        def f(it: Iterable[T]) -> bool:
            return all(self.__func(x) for x in it)

        name = f"all({self.__name})"
        if isinstance(self.__msg, str):
            return self.lift(f, name, self.__msg)

        # get a representative from the iterable
        def new_msg(it: Iterable[T] | None) -> str:
            if it is None:
                rep: T | None = None
            else:
                conv_it = iter(it)
                rep = next(conv_it, None)
            # redundant if callable check here, since we check if self.__msg
            # is a str above, but mypy gets angry if we don't do this.
            return (
                f"for every element: {self.__msg(rep)}"
                if callable(self.__msg)
                else "predicate failed"
            )

        return self.lift(
            f,
            name,
            new_msg,
        )

    def any(self) -> Predicate[Iterable[T]]:
        """Modify this predicate to check if any element in an iterable is accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.
        """

        def f(it: Iterable[T]) -> bool:
            return any(self.__func(x) for x in it)

        name = f"any({self.__name})"

        if isinstance(self.__msg, str):
            return self.lift(f, name, self.__msg)

        # get a representative from the iterable
        def new_msg(it: Iterable[T] | None) -> str:
            if it is None:
                rep: T | None = None
            else:
                conv_it = iter(it)
                rep = next(conv_it, None)
            # redundant if callable check here, since we check if self.__msg
            # is a str above, but mypy gets angry if we don't do this.
            return (
                f"for at least one element: {self.__msg(rep)}"
                if callable(self.__msg)
                else "predicate failed"
            )

        return self.lift(
            f,
            name,
            new_msg,
        )

    # --- safety / debugging ---
    def __bool__(self) -> Never:
        """Raise a TypeError if a predicate object is converted to a bool.

        Raises:
            TypeError: If this function is called
        """
        raise TypeError(
            "Predicate has no truth value; did you mean to call it? (e.g. pred(value))"
        )

    def __repr__(self) -> str:
        """Get a representation of this predicate.

        Returns:
            str: The repr.
        """
        fn = getattr(self.__func, "__name__", repr(self.__func))
        m = self.__msg.__qualname__ if callable(self.__msg) else self.__msg
        return f"Predicate(func={fn}, name={self.__name} msg={m!r})"
