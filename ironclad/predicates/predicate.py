"""
The predicate class.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

from collections.abc import Callable, Sized
from typing import TYPE_CHECKING, Any, Generic, Never, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["Predicate"]

T = TypeVar("T")
U = TypeVar("U")
Obj = TypeVar("Obj", bound=object)

ExceptionFactory = Callable[[str, U, str], BaseException]


class Predicate(Generic[T]):
    """A predicate, containing a predicate function and a failure message.

    Predicates can be modified/combined using
    the logical operators and ('&'), or ('|'), and not ('~').
    """

    __slots__ = ("__context", "__func", "__msg", "__name")

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
        #      the context of pred3 is (pred1, pred2)
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
        """Get the function this predicate runs to test values.

        Returns:
            Callable[[T], bool]: The function this predicate uses.
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
    def render_msg(self, x: T | None = None, /) -> str:
        """Render this predicate's message with a given input value.

        Args:
            x (T | None, optional): The value given to the predicate. Defaults to None.

        Returns:
            str: The formatted message with the given test value.
        """
        m = self.__msg
        if callable(m):
            return m(x)

        s = str(m)
        try:
            return s.format(x=x)
        except KeyError:  # safeguard for missing format
            return s

    def render_with_context(self, x: T | None = None, /, *, max_chain: int = 6) -> str:
        """Render this predicate's message with a given input value and context.

        Args:
            x (T | None, optional): The value given to the predicate. Defaults to None.
            max_chain (int, optional): The maximum number of chains to report.
                Defaults to 6.

        Returns:
            str: The formatted message with the given test value.
        """
        msg = self.render_msg(x)
        if not self.__context:
            return msg

        chain = " -> ".join(
            "'" + pred.name + "'" for pred in (*self.__context[-max_chain + 1 :], self)
        )
        return f"{msg} [via {chain}]"

    def render_tree(self, x: T | None = None, /) -> str:
        """Render this predicate's message with a given input value as a tree.

        Args:
            x (T | None, optional): The value given to the predicate. Defaults to None.

        Returns:
            str: The formatted tree with the given test value.
        """
        lines: list[str] = [f"{self.__name}: {self.render_msg(x)}"]
        lines.extend(  # newest -> oldest top-down
            [
                f"\tfrom {pred.name}: {pred.render_msg(x)}"
                for pred in reversed(self.__context)
            ]
        )
        return "\n".join(lines)

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
        self,
        x: T,
        /,
        *,
        label: str = "value",
        exc: type[BaseException] | ExceptionFactory[T] = ValueError,
    ) -> T:
        """Return x if ok, otherwise raise an error with useful context.

        Args:
            x (T): The value to test.
            label (str, optional): A label for the tested value. Defaults to "value".
            exc (type[BaseException] | ExceptionFactory[T], optional):
                An exception or exception factory called on failure.
                If a factory, it should take a label, the tested value,
                and error message and return an exception to raise.
                Defaults to ValueError.

        Raises:
            BaseException: If the validation fails, the exception returned
            by exc_factory will be raised.

        Returns:
            T: x, if the predicate accepts it.
        """
        if not self(x):
            message = f"{label}: {self.render_msg(x)} (got {x!r})"
            if callable(exc):
                raise exc(label, x, message)
            raise exc(message)
        return x

    # --- ergonomics --- #
    def with_name(self, name: str) -> Predicate[T]:
        """Clone this predicate and give it a new name.

        Args:
            name (str): The new name.

        Returns:
            Predicate[T]: The cloned predicate with the new name.
        """
        return self.clone(name=name)

    def with_msg(self, msg: str | Callable[[T | None], str]) -> Predicate[T]:
        """Clone this predicate and give it a new message.

        Args:
            msg (str | Callable[[T | None], str]): The new message.

        Returns:
            Predicate[T]: The cloned predicate with the new message.
        """
        return self.clone(msg=msg)

    # --- combinators ---
    def __and__(self, other: Predicate[T]) -> Predicate[T]:
        """Combine this predicate with another, merging their conditions with an 'AND'.

        Args:
            other (Predicate[T]): The other predicate.

        Returns:
            Predicate[T]: The combined predicate.
        """
        return Predicate(
            lambda x: self(x) and other(x),
            self.__name + " & " + other.name,
            lambda x: f"({self.render_msg(x)}) and ({other.render_msg(x)})",
        )

    __rand__ = __and__

    def __or__(self, other: Predicate[T]) -> Predicate[T]:
        """Combine this predicate with another, merging their conditions with an 'OR'.

        Args:
            other (Predicate[T]): The other predicate.

        Returns:
            Predicate[T]: The combined predicate.
        """
        return Predicate(
            lambda x: self(x) or other(x),
            self.__name + " | " + other.name,
            lambda x: f"({self.render_msg(x)}) or ({other.render_msg(x)})",
        )

    __ror__ = __or__

    def __invert__(self) -> Predicate[T]:
        """Negate this predicate.

        Returns:
            Predicate[T]: The negated predicate.
        """
        return Predicate(
            lambda x: not self(x),
            "~" + self.__name,
            lambda x: f"not ({self.render_msg(x)})",
        )

    negate = __invert__

    def __xor__(self, other: Predicate[T]) -> Predicate[T]:
        """Combine this predicate with another, merging their conditions with an 'XOR'.

        Args:
            other (Predicate[T]): The other predicate.

        Returns:
            Predicate[T]: The combined predicate.
        """
        return (self | other) & ~(self & other)

    __rxor__ = __xor__

    xor = __xor__

    def implies(self, other: Predicate[T]) -> Predicate[T]:
        """A predicate which checks that this predicate implies another predicate.

        Args:
            other (Predicate[T]): The predicate to imply.

        Returns:
            Predicate[T]: The implication predicate.
        """
        return (~self) | other

    # --- lifters/cloning ---
    def clone(
        self,
        *,
        name: str | None = None,
        msg: str | Callable[[T | None], str] | None = None,
    ) -> Predicate[T]:
        """Clone this predicate.

        Args:
            name (str | None, optional): The new predicate's name.
                Copies the old one if None or "". Defaults to None.
            msg (str | Callable[[Any | None], str], None, optional):
                The new predicate's failure message.
                Copies the old one if None. Defaults to None.

        Returns:
            Predicate[T]: The cloned predicate.
        """
        p = Predicate(
            self.__func, name or self.__name, msg if msg is not None else self.__msg
        )
        p.__context = self.__context
        return p

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

        When lifting a predicate, the new function should utilize the original
        predicate's function in order to maintain a semantic hierarchy.

        Args:
            func (Callable[[Any], bool]): The new predicate function.
            name (str | None): The new predicate's name.
                Copies the old one if None.
            msg (str | Callable[[Any | None], str], None):
                The new predicate's failure message.

        Returns:
            Predicate[Any]: The lifted predicate.
        """
        pred = self.clone(name=name, msg=msg)
        pred.__func = func
        pred.__context = (*self.__context, self)
        return pred

    def on(
        self,
        getter: Callable[[Obj], T],
        /,
    ) -> Predicate[Obj]:
        """Check if a property of an object validates it.

        Args:
            getter (Callable[[Obj], T]): function to access the property of an object.

        Returns:
            Predicate[Obj]: The new predicate.
        """
        return Predicate(
            lambda o: self.__func(getter(o)),
            self.__name,
            lambda o: self.render_msg(getter(o) if o is not None else None),
        )

    def __msg_over_iter(
        self, prefix: str, /
    ) -> str | Callable[[Iterable[T] | None], str]:
        if isinstance(self.__msg, str):
            return prefix + self.__msg

        def new_msg(it: Iterable[T] | None) -> str:
            sample: T | None = None
            if it is not None:
                it_iter = iter(it)
                sample = next(it_iter, None)
            base = self.render_msg(sample)  # handle callable/format uniformly
            return f"{prefix}{base}" if prefix else base

        return new_msg

    def quantify(
        self,
        quantifier: Callable[[Iterable[bool]], bool],
        /,
        label: str,
        *,
        prefix: str,
    ) -> Predicate[Iterable[T]]:
        """Build a predicate that approves an iterable via a boolean quantifier.

        Args:
            quantifier (Callable[[Iterable[bool]], bool]):
                Function that takes an iterable of bools
                and determines if it is approved.
            label (str): A name label for the quantifier.
            prefix (str): A prefix for the predicate's failure message.

        Returns:
            Predicate[Iterable[T]]: The quantified predicate.
        """
        return self.lift(
            lambda i: quantifier(self.__func(x) for x in i),
            f"{label}({self.__name})",
            self.__msg_over_iter(prefix),
        )

    def all(self) -> Predicate[Iterable[T]]:
        """Check if every element in an iterable is accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.
        """
        return self.quantify(all, "all", prefix="for every element: ")

    def any(self) -> Predicate[Iterable[T]]:
        """Check if any element in an iterable is accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.
        """
        return self.quantify(any, "any", prefix="for at least one element: ")

    def at_least(self, n: int) -> Predicate[Iterable[T]]:
        """Check if at least n elements in an iterable are accepted.

        Args:
            n (int): The minimum number of elements that must be accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.

        Raises:
            ValueError: If n is less than 0.
        """
        if n < 0:
            raise ValueError("n must be nonnegative")

        def quantifier(bits: Iterable[bool]) -> bool:
            size = None if not isinstance(bits, Sized) else len(bits)
            if size is not None and size < n:
                return False  # break if n is unreachable

            count = 0
            for b in bits:
                count += 1 if b else 0
                if count >= n:
                    return True
            return False

        return self.quantify(
            quantifier, f"at least {n}", prefix=f"for at least {n} elements: "
        )

    def at_most(self, n: int) -> Predicate[Iterable[T]]:
        """Check if at most n elements in an iterable are accepted.

        Args:
            n (int): The maximum number of elements that must be accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.

        Raises:
            ValueError: If n is less than 0.
        """
        if n < 0:
            raise ValueError("n must be nonnegative")

        def quantifier(bits: Iterable[bool]) -> bool:
            count = 0
            for b in bits:
                count += 1 if b else 0
                if count > n:
                    return False
            return True

        return self.quantify(
            quantifier, f"at most {n}", prefix=f"for at most {n} elements: "
        )

    def exactly(self, n: int) -> Predicate[Iterable[T]]:
        """Check if exactly n elements in an iterable are accepted.

        Args:
            n (int): The exact number of elements that must be accepted.

        Returns:
            Predicate[Iterable[T]]: The new predicate.

        Raises:
            ValueError: If n is less than 0.
        """
        if n < 0:
            raise ValueError("n must be nonnegative")

        def quantifier(bits: Iterable[bool]) -> bool:
            size = None if not isinstance(bits, Sized) else len(bits)
            if size is not None and size < n:
                return False  # break if n is unreachable

            count = 0
            for b in bits:
                count += 1 if b else 0
                if count > n:
                    return False
            return count == n

        return self.quantify(
            quantifier, f"exactly {n}", prefix=f"for exactly {n} elements: "
        )

    # --- safety / debugging ---
    def __bool__(self) -> Never:
        """Raise a TypeError if a predicate object is converted to a bool.

        Raises:
            TypeError: If this function is called.
        """
        raise TypeError(
            "Predicate itself has no truth value; "
            "did you mean to call it? (e.g. pred(value))"
        )

    def __repr__(self) -> str:
        """Get a representation of this predicate.

        Returns:
            str: The repr.
        """
        fn = getattr(self.__func, "__name__", repr(self.__func))
        m = self.__msg.__qualname__ if callable(self.__msg) else self.__msg
        return f"Predicate(func={fn}, name={self.__name} msg={m!r})"
