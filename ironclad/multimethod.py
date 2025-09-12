"""multimethod.py

File for the multimethod, an object that creates runtime overloads with type-hint matching.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from __future__ import annotations

import functools
import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
    Union,
)

from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions
from .util import as_predicate


class multimethod:  # pylint:disable=invalid-name
    """Runtime overloads with type-hint matching."""

    __slots__ = ("options", "_implementations", "__name__")

    def __init__(
        self,
        func: Union[Callable[..., Any], None] = None,
        /,
        *,
        options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    ) -> None:
        """Runtime overloads with type-hint matching.

        Arguments
        ---------
        func : Callable | None, optional
            The function to overload, by default None
        options : EnforceOptions, optional
            Type enforcement options, by default DEFAULT_ENFORCE_OPTIONS
        """

        self._implementations: List[
            Tuple[
                inspect.Signature,
                Dict[str, Callable[[Any], bool]],
                Callable[..., Any],
                Dict[str, Any],
            ]
        ] = []
        self.options = options
        self.__name__ = getattr(func, "__name__", "overloaded")
        if func is not None:
            self.overload(func)
            functools.update_wrapper(self, func)

    def overload(self, func: Callable[..., Any], /) -> multimethod:
        """Register a new function overload to this multimethod.

        Parameters
        ----------
        func : Callable
            The function to register

        Returns
        -------
        multimethod
            The updated multimethod now including the given function
        """

        sig = inspect.signature(func)
        validators: Dict[str, Callable[[Any], bool]] = {}
        norm_annotation: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            annotation = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )
            # Normalize varargs/kwargs to Tuple[...] and Mapping[str, ...]
            # if param.kind is inspect.Parameter.VAR_POSITIONAL:
            #     annotation = Tuple[annotation, ...]
            # elif param.kind is inspect.Parameter.VAR_KEYWORD:
            #     annotation = Mapping[str, annotation]

            norm_annotation[name] = annotation
            validators[name] = as_predicate(annotation, self.options)

        self._implementations.append((sig, validators, func, norm_annotation))
        return self

    def __call__(self, *args: Any, **kwargs: Any):
        matches: List[Tuple[int, Callable[..., Any]]] = []

        for sig, validators, func, norm_annotation in self._implementations:
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
            want = " | ".join(self._sig_str(sig) for sig, *_ in self._implementations)
            got = ", ".join(type_repr(type(arg)) for arg in args)
            if kwargs:
                got += (", " if got else "") + "**kwargs"

            raise TypeError(
                f"No overload of {self.__name__}() matches ({got}). Candidates: {want}"
            )

        matches.sort(key=lambda t: t[0], reverse=True)
        return matches[0][1](*args, **kwargs)

    def _sig_str(self, sig: inspect.Signature, /) -> str:
        parts: List[str] = []

        for name, param in sig.parameters.items():
            annotation = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )
            parts.append(f"{name}: {type_repr(annotation)}")

        return f"{self.__name__}({'(' + ', '.join(parts) + ')'})"


def runtime_overload(
    func: Callable[..., Any], /, *, options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS
) -> multimethod:
    # pylint:disable=line-too-long
    """Turn a function into a multimethod, allowing for runtime overloads.

    Parameters
    ----------
    func : Callable
        The function to turn into a multimethod
    options : EnforceOptions, optional
        Type enforcement options, by default DEFAULT_ENFORCE_OPTIONS

    Example
    -------
    >>> from ironclad import runtime_overload
    >>>
    >>> @runtime_overload
    ... def func(s: str) -> bool:
    ...     return True
    ...
    >>> @func.overload
    ... def _(x: int, y: int) -> bool:
    ...     return False
    ...
    >>> func("hi")
    True
    >>> func(1, 2)
    False
    >>> func(1, "hi")
    Traceback (most recent call last):
      ...
    TypeError: No overload of func() matches (int, str). Candidates: func((s: str)) | func((x: int, y: int))
    """

    return multimethod(func, options=options)
