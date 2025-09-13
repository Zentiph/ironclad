"""
Representation tools for types and other Python features.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import types
from collections.abc import Iterable, Mapping, Sequence
from typing import (
    Annotated,
    Any,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

_UNION_TYPES = (Union, getattr(types, "UnionType", Union))  # pylint:disable=consider-alternative-union-syntax


def _name_of_type(tp: type) -> str:
    if tp is type(None):
        return "None"
    # prefer short names for builtins or main objects
    if getattr(tp, "__module__", "") in {"builtins", "__main__"}:
        return tp.__name__
    return tp.__module__ + "." + tp.__qualname__


def _literal_value_repr(val: Any) -> str:
    return repr(val)


def _join_or(parts: Iterable[Any]) -> str:
    seen = set()
    out = []
    for part in parts:
        if part not in seen:
            out.append(part)
            seen.add(part)
    return " or ".join(out)


def _normalize_none(s: str) -> str:
    # turn NoneType into None when something produces that label
    return "None" if s == "NoneType" else s


def _flatten_union(union: Any) -> list[Any]:
    stack = [union]
    out = []

    while stack:
        current = stack.pop()
        if get_origin(current) in _UNION_TYPES:
            stack.extend(get_args(current))
        else:
            out.append(current)

    out.reverse()  # preserve original left to right order
    return out


def _normal_type_repr(hint: Any, /) -> str:
    # regular classes/types
    if isinstance(hint, type):
        return _name_of_type(hint)

    # python tuple of types
    if isinstance(hint, tuple):
        return _join_or(type_repr(h) for h in hint)

    # NewType support
    if callable(hint) and getattr(hint, "__supertype__", None) is not None:
        return getattr(hint, "__name__", str(hint))

    return ""


def _typing_type_repr(hint: Any, origin: Any, /) -> str:
    # Annotated[T, ...] -> T
    if origin is Annotated:
        base, *_ = get_args(hint)
        return type_repr(base)

    # Literal[X, Y, ...] -> "X or Y or ..."
    if origin is Literal:
        vals = (_literal_value_repr(val) for val in get_args(hint))
        return _join_or(vals)

    # if Union[X, Y] / X | Y
    if origin in _UNION_TYPES:
        parts = _flatten_union(hint)
        return _join_or(_normalize_none(type_repr(p)) for p in parts)

    # if Type[T]
    if origin is type:
        (inner,) = get_args(hint) or (Any,)
        return f"type[{type_repr(inner)}]"

    return ""  # empty string to represent this didn't work


def _collection_type_repr(hint: Any, origin: Any, /) -> str:
    # if tuples: could be Tuple[T, ...] or Tuple[T1, T2, ...]
    if origin is tuple:
        args = get_args(hint)
        if len(args) == 2 and args[1] is Ellipsis:
            return f"tuple[{type_repr(args[0])}, ...]"
        return "tuple[" + ", ".join(type_repr(ele) for ele in args) + "]"

    # built-in generics and ABCs
    if origin in (list, set, frozenset):
        (ele,) = get_args(hint) or (Any,)
        name = {list: "list", set: "set", frozenset: "frozenset"}[origin]
        return f"{name}[{type_repr(ele)}]"

    if origin in (dict, Mapping):
        k, v = get_args(hint) or (Any, Any)
        name = {dict: "dict", Mapping: "Mapping"}[origin]
        return f"{name}[{type_repr(k)}, {type_repr(v)}]"

    if origin in (Sequence, Iterable):
        (ele,) = get_args(hint) or (Any,)
        name = origin.__name__
        return f"{name}[{type_repr(ele)}]"

    return ""


def _special_repr(hint: Any, /) -> str:
    # special cases
    if hint is Any:
        return "Any"
    if hint is None or hint is type(None):
        return "None"

    # TypeVar: show constraints or bound, otherwise the name
    if isinstance(hint, TypeVar):
        if hint.__constraints__:
            return _join_or(type_repr(con) for con in hint.__constraints__)
        if hint.__bound__:
            return type_repr(hint.__bound__)
        return hint.__name__

    return ""


def _fallback_repr(hint: Any, /) -> str:
    # fallback: bare typing objects
    if getattr(hint, "__module__", "") == "typing":
        args = get_args(hint)
        base = getattr(hint, "_name", None)
        if base is None:
            # last resort, normalize str
            return str(hint).replace("typing.", "")
        if args:
            return f"{base}[{', '.join(type_repr(arg) for arg in args)}]"
        return str(base)

    return ""


def type_repr(hint: Any, /) -> str:
    """Return a pretty, user-facing string for a type hint.

    Args:
        hint (Any): The type hint to represent.

    Returns:
        str: A repr of the hint given.
    """
    normal_repr = _normal_type_repr(hint)
    if normal_repr:
        return normal_repr

    # typing constructs
    origin = get_origin(hint)

    typing_type_result = _typing_type_repr(hint, origin)
    if typing_type_result:
        return typing_type_result

    collection_type_result = _collection_type_repr(hint, origin)
    if collection_type_result:
        return collection_type_result

    special_result = _special_repr(hint)
    if special_result:
        return special_result

    fallback_result = _fallback_repr(hint)
    if fallback_result:
        return fallback_result

    # final fallback
    return getattr(hint, "__name__", str(hint))
