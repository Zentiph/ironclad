"""compile.py

Compiled predicates for value/type checks.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

# from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Annotated, Any, Literal, Tuple, TypeVar, Union, get_args, get_origin

from ..predicates import Predicate
from ..repr import type_repr
from ..types import EnforceOptions

# TODO: make type repr better
#       1. tuples show (<class ...>, class<...>), use better repr
#       2. typing objects just show the name, so Union[int, float] -> Union, use better repr
#       3. better show settings to describe why failed (e.g. if no subclasses, say expected no subclasses, etc)


CACHE_SIZE = 2048


# pylint:disable=too-many-branches,too-many-return-statements
def matches_hint(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
    """Check if a variable matches its type hint.

    Parameters
    ----------
    x : Any
        The variable to check
    hint : Any
        The type hint
    opts : EnforceOptions
        Any type enforcement options

    Returns
    -------
    bool
        Whether the variable matches the type hint
    """

    if hint is Any:  # can be anything
        return True

    if hint is None or hint is type(None):  # hint is None, so x must be
        return x is None

    origin = get_origin(hint)

    if origin is Annotated:  # check if the base type matches
        base, *_ = get_args(hint)
        return matches_hint(x, base, opts)

    if origin is Literal:  # see if x is a value in the literal
        return x in set(get_args(hint))

    if origin is type:  # see if x is a subclass of the type inside type[T]
        (t,) = get_args(hint) or (object,)
        return isinstance(x, type) and (t is object or issubclass(x, t))

    if origin is tuple:
        args = get_args(hint)
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
                matches_hint(elem, ht, opts) for elem, ht in zip(x, args)
            )
        )

    if origin in (list, set, frozenset, Sequence):
        elem = (get_args(hint) or (Any,))[0]
        pytype = (
            list
            if origin is list
            else (
                set if origin is set else frozenset if origin is frozenset else Sequence
            )
        )
        return isinstance(x, pytype) and all(matches_hint(e, elem, opts) for e in x)

    if origin in (dict, Mapping):
        k_hint, v_hint = get_args(hint) or (Any, Any)
        return isinstance(x, Mapping) and all(
            matches_hint(k, k_hint, opts) and matches_hint(v, v_hint, opts)
            for k, v in x.items()
        )

    if origin is Union:
        return any(matches_hint(x, ht, opts) for ht in get_args(hint))

    if isinstance(hint, TypeVar):
        if hint.__constraints__:
            return any(matches_hint(x, ht, opts) for ht in hint.__constraints__)
        if hint.__bound__:
            return matches_hint(x, hint.__bound__, opts)
        return True

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


def _opts_key(opts: EnforceOptions, /) -> Tuple[bool, bool, bool]:
    # keep hashable for caching
    return (opts.allow_subclasses, opts.check_defaults, opts.strict_bools)


@lru_cache(maxsize=CACHE_SIZE)
def _hint_pred_cached(hint: Any, opts_key: Tuple[bool, bool, bool], /) -> Predicate:
    # cached wrapper around matches_hint for hashable hints
    opts = EnforceOptions(*opts_key)
    return Predicate(lambda x: matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def _hint_pred_uncached(hint: Any, opts: EnforceOptions, /) -> Predicate:
    # fallback if hint is unhashable
    return Predicate(lambda x: matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def as_predicate(spec: Any, options: EnforceOptions) -> Predicate:
    """Turn a typing spec or an existing Predicate into a Predicate with caching.
    Caching will not work if a type hint is not cachable.

    Parameters
    ----------
    spec : Any
        Typing spec or Predicate
    options : EnforceOptions
        The options for type enforcement

    Returns
    -------
    Predicate
        Cached predicate
    """

    if isinstance(spec, Predicate):
        return spec
    try:
        # try to hash
        return _hint_pred_cached(spec, _opts_key(options))
    except TypeError:
        # unhashable, don't cache
        return _hint_pred_uncached(spec, options)
