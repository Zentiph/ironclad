"""The Multimethod, an object that creates runtime overloads with type-hint matching."""

# TODO: see if it's possible to make Multimethod type-strict with calls
# e.g. if two overloads (one for int, one for str) then make type-checkers
#      angry if call tried with a float

# TODO: raise an error if two overloads with identical param
#       type specs are created

from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any

from ._utils import as_predicate
from .type_repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions

if TYPE_CHECKING:
    from collections.abc import Callable


__all__ = ["InvalidOverloadError", "Multimethod", "runtime_overload"]

__author__ = "Zentiph"
__license__ = "MIT"


class InvalidOverloadError(TypeError):
    """Raised when an invalid overload is called for a Multimethod."""


class Multimethod:
    """Runtime overloads with type-hint matching.

    It is generally recommended to use the `runtime_overload` decorator instead of this
    class directly to create runtime overloads, as the error message diagnostics are
    better.
    """

    def __init__(
        self,
        func: Callable[..., Any] | None = None,
        /,
        *,
        options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    ) -> None:
        """Runtime overloads with type-hint matching.

        It is generally recommended to use the `runtime_overload` decorator instead of
        this class directly to create runtime overloads, as the error message
        diagnostics are better.

        Args:
            func (Callable[..., Any] | None, optional): The function to overload.
                Defaults to None.
            options (EnforceOptions, optional): Type enforcement options.
                Defaults to DEFAULT_ENFORCE_OPTIONS.
        """
        self.__implementations: list[
            tuple[
                inspect.Signature,
                dict[str, Callable[[Any], bool]],
                Callable[..., Any],
                dict[str, Any],
            ]
        ] = []
        self.options = options
        self.__name__ = getattr(func, "__name__", "overloaded")
        if func is not None:
            self.overload(func)
            functools.update_wrapper(self, func)

    def overload(self, func: Callable[..., Any], /) -> Multimethod:
        """Register a new function overload to this Multimethod.

        Args:
            func (Callable[..., Any]): The function to register.

        Returns:
            Multimethod: The updated Multimethod now including the given function.
        """
        sig = inspect.signature(func)
        validators: dict[str, Callable[[Any], bool]] = {}
        norm_annotation: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            annotation = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )

            norm_annotation[name] = annotation
            validators[name] = as_predicate(annotation, self.options)

        self.__implementations.append((sig, validators, func, norm_annotation))
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call this Multimethod with the given argument overload.

        Raises:
            InvalidOverloadError: If an overload that does not exist is called.

        Returns:
            Any: The return value matching the overload and arguments called.
        """
        matches: list[tuple[int, Callable[..., Any]]] = []

        for sig, validators, func, norm_annotation in self.__implementations:
            try:
                bound = sig.bind(*args, **kwargs)
            except TypeError:
                continue

            ok = True
            for name, val in bound.arguments.items():
                if not validators[name](val):
                    ok = False
                    break

            if ok:
                # prefer more specific signatures (less Any)
                # stable tie-breaker = registration order
                score = sum(
                    annotation is not Any for annotation in norm_annotation.values()
                )
                matches.append((score, func))

        if not matches:
            want = " | ".join(self.__sig_str(sig) for sig, *_ in self.__implementations)
            got = ", ".join(type_repr(type(arg)) for arg in args)
            if kwargs:
                got += (", " if got else "") + "**kwargs"

            raise InvalidOverloadError(
                f"No overload of {self.__name__}() matches ({got}). Candidates: {want}"
            )

        matches.sort(key=lambda t: t[0], reverse=True)
        return matches[0][1](*args, **kwargs)

    def __sig_str(self, sig: inspect.Signature, /) -> str:
        parts: list[str] = []

        for name, param in sig.parameters.items():
            annotation = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )
            parts.append(f"{name}: {type_repr(annotation)}")

        return f"{self.__name__}({', '.join(parts)})"


def runtime_overload(
    func: Callable[..., Any], /, *, options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS
) -> Multimethod:
    """Turn a function into a Multimethod, allowing for runtime overloads.

    Args:
        func (Callable[..., Any]): The function to turn into a Multimethod.
        options (EnforceOptions, optional): Type enforcement options.
            Defaults to DEFAULT_ENFORCE_OPTIONS.

    Examples:
        ```python
        >>> import ironclad as ic
        >>>
        >>> @ic.runtime_overload
        ... def describe(x: int) -> str:
        ...     return f"int: {x}"
        ...
        >>> @describe.overload
        >>> def _(x: str) -> str:
        ...     return f"str: '{x}'"
        ...
        >>> describe(32)
        'int: 32'
        >>> describe("python")
        "str: 'python'"
        >>> describe(2.4)
        InvalidOverloadError: No overload of describe() matches (float). (...)
        ```
    """
    return Multimethod(func, options=options)
