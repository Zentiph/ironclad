"""
Compiled predicates for value/type checks.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from collections.abc import Mapping, MutableSequence, Sequence
from collections.abc import Set as AbcSet
from functools import lru_cache
from types import UnionType
from typing import Annotated, Any, Literal, TypeVar, Union, get_args, get_origin

from ..repr import type_repr
from ..types import EnforceOptions
from .predicate import Predicate

__all__ = ["as_predicate", "matches_hint", "spec_contains_int"]

_CACHE_SIZE = 2048


def _matches_typevar(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
    if isinstance(hint, TypeVar):
        if hint.__constraints__:
            return any(matches_hint(x, ht, opts) for ht in hint.__constraints__)
        if hint.__bound__:
            return matches_hint(x, hint.__bound__, opts)
        return True

    return False


def _matches_typing_hint(
    x: Any, hint: Any, origin: Any, opts: EnforceOptions, /
) -> bool:
    if origin is type:  # see if x is a subclass of the type inside type[T]
        (t,) = get_args(hint) or (object,)
        return isinstance(x, type) and (t is object or issubclass(x, t))

    if origin is Annotated:  # check if the base type matches
        base, *_ = get_args(hint)
        return matches_hint(x, base, opts)

    if origin is Literal:  # see if x is a value in the literal
        return x in set(get_args(hint))

    if origin in (Union, UnionType):
        return any(matches_hint(x, ht, opts) for ht in get_args(hint))

    return _matches_typevar(x, hint, opts)


def _matches_collection_hint(
    x: Any, hint: Any, origin: Any, opts: EnforceOptions, /
) -> bool:
    if origin is tuple:
        args: tuple[Any, ...] = get_args(hint)

        if len(args) == 2 and args[1] is ...:  # any size tuple (tuple[T, ...])
            return isinstance(
                x, tuple
            ) and all(  # make sure all items inside the tuple match the type
                matches_hint(elem, args[0], opts) for elem in x
            )

        return (
            isinstance(x, tuple)
            and len(x) == len(args)
            and all(  # make sure all items inside the tuple match the type
                matches_hint(elem, ht, opts) for elem, ht in zip(x, args, strict=False)
            )
        )

    if origin in (list, set, frozenset, Sequence, AbcSet, MutableSequence):
        elem = (get_args(hint) or (Any,))[0]
        return isinstance(x, origin) and all(matches_hint(e, elem, opts) for e in x)

    if origin in (dict, Mapping):
        if not isinstance(x, Mapping):
            return False

        k_hint, v_hint = get_args(hint) or (Any, Any)

        return all(
            matches_hint(k, k_hint, opts) and matches_hint(v, v_hint, opts)
            for k, v in x.items()
        )

    return False


def _matches_normal(x: Any, hint: Any, origin: Any, opts: EnforceOptions, /) -> bool:
    try:  # normal classes/ABCs, @runtime_checkable Protocols
        if isinstance(hint, type):
            if not opts.allow_subclasses:
                return type(x) is hint  # pylint:disable=unidiomatic-typecheck
            # separate case for restriction on bools as ints
            if opts.strict_bools and hint is int:
                return type(x) is int  # pylint:disable=unidiomatic-typecheck

        return isinstance(x, hint)
    except TypeError:
        # fallback for typing objects on older Python versions
        return origin is not None and matches_hint(x, origin, opts)


@lru_cache(maxsize=_CACHE_SIZE)
def _hint_pred_cached(
    hint: Any, /, *, allow_subclasses: bool, check_defaults: bool, strict_bools: bool
) -> Predicate[Any]:
    # cached wrapper around matches_hint for hashable hints
    opts = EnforceOptions(
        allow_subclasses=allow_subclasses,
        check_defaults=check_defaults,
        strict_bools=strict_bools,
    )
    return Predicate(lambda x: matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def _hint_pred_uncached(
    hint: Any, /, *, allow_subclasses: bool, check_defaults: bool, strict_bools: bool
) -> Predicate[Any]:
    # cached wrapper around matches_hint for hashable hints
    opts = EnforceOptions(
        allow_subclasses=allow_subclasses,
        check_defaults=check_defaults,
        strict_bools=strict_bools,
    )
    # fallback if hint is unhashable
    return Predicate(lambda x: matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def matches_hint(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
    """Check if a variable matches its type hint.

    Args:
        x (Any): The variable to check.
        hint (Any): The type hint.
        opts (EnforceOptions): The type enforcement options.

    Returns:
        bool: Whether the variable matches the type hint.
    """
    if hint is Any:  # can be anything
        return True

    if hint is None or hint is type(None):  # hint is None, so x must be
        return x is None

    origin = get_origin(hint)

    if _matches_collection_hint(x, hint, origin, opts):
        return True

    if _matches_typing_hint(x, hint, origin, opts):
        return True

    return _matches_normal(x, hint, origin, opts)


def spec_contains_int(spec: Any) -> bool:
    """Check if a type spec contains an integer somewhere inside.

    Args:
        spec (Any): The type spec.

    Returns:
        bool: Whether the type spec contains an int.
    """
    if spec is int:
        return True

    origin = get_origin(spec)
    if origin in (Union, UnionType, tuple):
        return any(spec_contains_int(arg) for arg in get_args(spec))

    return False


def as_predicate(spec: Any, options: EnforceOptions) -> Predicate[Any]:
    """Turn a typing spec or an existing Predicate into a Predicate with caching.

    Caching will not work if a type hint is not cachable.

    Args:
        spec (Any): The typing spec or Predicate to convert.
        options (EnforceOptions): The type enforcement options.

    Returns:
        Predicate[Any]: The cached predicate.
    """
    if isinstance(spec, Predicate):
        return spec
    try:
        # try to hash
        return _hint_pred_cached(
            spec,
            allow_subclasses=options.allow_subclasses,
            check_defaults=options.check_defaults,
            strict_bools=options.strict_bools,
        )
    except TypeError:
        # unhashable, don't cache
        return _hint_pred_uncached(
            spec,
            allow_subclasses=options.allow_subclasses,
            check_defaults=options.check_defaults,
            strict_bools=options.strict_bools,
        )
