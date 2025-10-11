"""
Argument validation functions, including type and value enforcing.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import functools
import inspect
from collections.abc import Callable, Mapping, MutableSequence, Sequence
from collections.abc import Set as AbcSet
from dataclasses import dataclass
from reprlib import Repr
from types import UnionType
from typing import (
    Annotated,
    Any,
    Literal,
    ParamSpec,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from .predicates import Predicate
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, ClassInfo, EnforceOptions

__all__ = ["coerce_types", "enforce_annotations", "enforce_types", "enforce_values"]

P = ParamSpec("P")
T = TypeVar("T")

_CACHE_SIZE = 2048

_SHORT = Repr()
_SHORT.maxstring = 80
_SHORT.maxother = 80


@dataclass(frozen=True)
class _Plan:
    pos_names: tuple[str, ...]
    vararg_name: str | None
    varkw_name: str | None
    need_kwonly_bind: bool


def _bind_fallback(
    sig: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
    *,
    apply_defaults: bool,
) -> dict[str, Any]:
    bound = sig.bind(*args, **kwargs)
    if apply_defaults:
        bound.apply_defaults()
    return bound.arguments


def _map_kwargs(
    mapping: dict[str, Any],
    plan: _Plan,
    kwargs: dict[str, Any],
    /,
) -> bool:
    dup_keys = [k for k in kwargs if k in mapping]
    if dup_keys:
        return False  # need to fallback

    if plan.varkw_name is None:
        # ensure all kwargs hit known names
        unknown = [k for k in kwargs if k not in plan.pos_names]
        if unknown:
            return False  # need to fallback
        # safe to overwrite/add names params only
        for k in kwargs.keys() & set(plan.pos_names):
            mapping[k] = kwargs[k]

    else:  # plan.varkw_name is not None
        extra: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k in plan.pos_names:
                mapping[k] = v
            else:
                extra[k] = v

        if extra:
            varkw = mapping.get(plan.varkw_name)
            if not isinstance(varkw, dict):
                mapping[plan.varkw_name] = extra
            else:
                varkw.update(extra)

    return True


def _make_plan(sig: inspect.Signature) -> _Plan:
    pos, vararg, varkw, need_kwonly = [], None, None, False
    for param in sig.parameters.values():
        if param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
            pos.append(param.name)
            if param.default is not inspect.Parameter.empty:
                need_kwonly = True
        elif param.kind is inspect.Parameter.VAR_POSITIONAL:
            vararg = param.name
        elif param.kind is inspect.Parameter.KEYWORD_ONLY:
            need_kwonly = True
        elif param.kind is inspect.Parameter.VAR_KEYWORD:
            varkw = param.name
    return _Plan(tuple(pos), vararg, varkw, need_kwonly)


def _fast_bind(
    plan: _Plan,
    sig: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    apply_defaults: bool,
) -> dict[str, Any]:
    # fast path if no kw-only/defaults and kwargs only fill tail names
    if plan.need_kwonly_bind:
        return _bind_fallback(sig, args, kwargs, apply_defaults=apply_defaults)

    # map pure positionals
    mapping: dict[str, Any] = {}
    n_pos = min(len(args), len(plan.pos_names))
    if n_pos:
        mapping.update(zip(plan.pos_names[:n_pos], args[:n_pos], strict=False))

    # too many positionals without *varargs; fallback for correct error
    if len(args) > n_pos:
        if plan.vararg_name is None:
            return _bind_fallback(sig, args, kwargs, apply_defaults=apply_defaults)
        mapping[plan.vararg_name] = tuple(args[n_pos:])

    # kwargs mapping
    if kwargs and not _map_kwargs(mapping, plan, kwargs):
        return _bind_fallback(sig, args, kwargs, apply_defaults=apply_defaults)

    # optionally inject defaults (only safe if no kw-only/defaults; else bailed already)
    if apply_defaults:
        for param in sig.parameters.values():
            if (
                param.default is not inspect.Parameter.empty
                and param.name not in mapping
            ):
                mapping[param.name] = param.default

    return mapping


def _to_call_args(
    mapping: dict[str, Any], plan: _Plan, /
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    # positional params
    args_list = [mapping[name] for name in plan.pos_names]

    # *varargs
    if plan.vararg_name and plan.vararg_name in mapping:
        args_list.extend(mapping[plan.vararg_name])
    # kwargs + **varkw
    kwargs: dict[str, Any] = {}
    for name, val in mapping.items():
        if name in plan.pos_names or name in (plan.vararg_name, plan.varkw_name):
            continue
        kwargs[name] = val
    if plan.varkw_name and plan.varkw_name in mapping:
        kwargs.update(mapping[plan.varkw_name])

    return tuple(args_list), kwargs


def _spec_contains_int(spec: Any) -> bool:
    if spec is int:
        return True

    origin = get_origin(spec)
    if origin in (Union, UnionType, tuple):
        return any(_spec_contains_int(arg) for arg in get_args(spec))

    return False


def _matches_typevar(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
    if isinstance(hint, TypeVar):
        if hint.__constraints__:
            return any(_matches_hint(x, ht, opts) for ht in hint.__constraints__)
        if hint.__bound__:
            return _matches_hint(x, hint.__bound__, opts)
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
        return _matches_hint(x, base, opts)

    if origin is Literal:  # see if x is a value in the literal
        return x in set(get_args(hint))

    if origin in (Union, UnionType):
        return any(_matches_hint(x, ht, opts) for ht in get_args(hint))

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
                _matches_hint(elem, args[0], opts) for elem in x
            )

        return (
            isinstance(x, tuple)
            and len(x) == len(args)
            and all(  # make sure all items inside the tuple match the type
                _matches_hint(elem, ht, opts) for elem, ht in zip(x, args, strict=False)
            )
        )

    if origin in (list, set, frozenset, Sequence, AbcSet, MutableSequence):
        elem = (get_args(hint) or (Any,))[0]
        return isinstance(x, origin) and all(_matches_hint(e, elem, opts) for e in x)

    if origin in (dict, Mapping):
        if not isinstance(x, Mapping):
            return False

        k_hint, v_hint = get_args(hint) or (Any, Any)

        return all(
            _matches_hint(k, k_hint, opts) and _matches_hint(v, v_hint, opts)
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
        return origin is not None and _matches_hint(x, origin, opts)


@functools.lru_cache(maxsize=_CACHE_SIZE)
def _hint_pred_cached(
    hint: Any, /, *, allow_subclasses: bool, check_defaults: bool, strict_bools: bool
) -> Predicate[Any]:
    # cached wrapper around _matches_hint for hashable hints
    opts = EnforceOptions(
        allow_subclasses=allow_subclasses,
        check_defaults=check_defaults,
        strict_bools=strict_bools,
    )
    return Predicate(lambda x: _matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def _hint_pred_uncached(
    hint: Any, /, *, allow_subclasses: bool, check_defaults: bool, strict_bools: bool
) -> Predicate[Any]:
    # cached wrapper around _matches_hint for hashable hints
    opts = EnforceOptions(
        allow_subclasses=allow_subclasses,
        check_defaults=check_defaults,
        strict_bools=strict_bools,
    )
    # fallback if hint is unhashable
    return Predicate(lambda x: _matches_hint(x, hint, opts), f"'{type_repr(hint)}'")


def _matches_hint(x: Any, hint: Any, opts: EnforceOptions, /) -> bool:
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


def _as_cached_predicate(spec: Any, options: EnforceOptions) -> Predicate[Any]:
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


def enforce_types(
    options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    /,
    **types: ClassInfo,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that enforces the types of function parameters.

    Supports typing types.

    Args:
        options (EnforceOptions, optional): Type enforcement options.
            Defaults to DEFAULT_ENFORCE_OPTIONS.
        types (ClassInfo): A mapping of argument names to expected types.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        sig = inspect.signature(func)

        # validate all arguments given exist in the function signature
        for name in types:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = _make_plan(sig)

        # compile once
        validators: dict[str, Predicate[Any]] = {
            name: _as_cached_predicate(spec, options) for name, spec in types.items()
        }

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = _fast_bind(
                plan, sig, args, kwargs, apply_defaults=options.check_defaults
            )

            for name, pred in validators.items():
                val = bound[name]
                if not pred(val):
                    conditions = "("
                    if not options.allow_subclasses:
                        conditions += "no subclasses"
                    if options.strict_bools and any(
                        # only add bool info if there's an int in the types
                        _spec_contains_int(v)
                        for v in types.values()
                    ):
                        if not options.allow_subclasses:
                            conditions += ", "
                        conditions += "no bools as ints"
                    conditions += ")"

                    raise TypeError(
                        f"{func.__qualname__}(): '{name}' expected "
                        f"{pred.render_msg(val)} "
                        f"{conditions if conditions != '()' else ''}, "
                        f"got '{type_repr(type(val))}' with value {_SHORT.repr(val)}"
                    )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def enforce_annotations(
    *, check_return: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that enforces the function's type hints at runtime.

    Args:
        check_return (bool, optional): Whether to enforce the return type.
            Defaults to True.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        hints = get_type_hints(func, include_extras=True)
        param_hints = {k: v for k, v in hints.items() if k != "return"}

        wrapped = enforce_types(**param_hints)(func)
        if not check_return or "return" not in hints:
            return wrapped

        @functools.wraps(wrapped)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            out = wrapped(*args, **kwargs)

            if not _matches_hint(out, hints["return"], DEFAULT_ENFORCE_OPTIONS):
                raise TypeError(
                    f"{func.__qualname__}(): return expected "
                    f"{type_repr(hints['return'])}, got {type_repr(type(out))}"
                )

            return out

        return wrapper

    return decorator


def coerce_types(
    **coercers: Callable[[object], object],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that coerces the types of function parameters using coercer functions.

    This decorator is particularly useful for coercing string arguments into
    their proper types when using CLI/ENV arguments, web handlers, enums, and JSONs.

    Args:
        coercers (Callable[[object], object]): A mapping of argument names
            to coercer functions
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        sig = inspect.signature(func)
        plan = _make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = _fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, coerce in coercers.items():
                if name in bound:
                    bound[name] = coerce(bound[name])

            # rebuild call args and invoke
            call_args, call_kwargs = _to_call_args(bound, plan)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator


def enforce_values(
    **predicate_map: Predicate[Any],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that enforces value constraints on function parameters.

    Args:
        predicate_map (Predicate): A mapping of argument names to predicates
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        sig = inspect.signature(func)

        for name in predicate_map:
            if name not in sig.parameters:
                raise ValueError(f"Unknown parameter '{name}' in {func.__qualname__}")

        plan = _make_plan(sig)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = _fast_bind(plan, sig, args, kwargs, apply_defaults=True)

            for name, pred in predicate_map.items():
                val = bound[name]
                if not pred(val):
                    raise ValueError(
                        f"{func.__qualname__}(): '{name}' failed constraint: "
                        f"{pred.render_msg(val)}; got {_SHORT.repr(val)}"
                    )

            call_args, call_kwargs = _to_call_args(bound, plan)
            return func(*call_args, **call_kwargs)

        return wrapper

    return decorator
