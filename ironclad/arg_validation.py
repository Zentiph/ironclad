"""
Argument validation functions, including type and value enforcing.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from reprlib import Repr
from typing import (
    Any,
    ParamSpec,
    TypeVar,
    get_type_hints,
)

from ._utils import as_predicate, matches_hint, spec_contains_int
from .predicates import Predicate
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, ClassInfo, EnforceOptions

__all__ = ["coerce_types", "enforce_annotations", "enforce_types", "enforce_values"]

P = ParamSpec("P")
T = TypeVar("T")

Coercer = Callable[[Any], Any]


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
            name: as_predicate(spec, options) for name, spec in types.items()
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
                        spec_contains_int(v)
                        for v in types.values()
                    ):
                        if not options.allow_subclasses:
                            conditions += ", "
                        conditions += "no bools as ints"
                    conditions += ")"

                    # TODO show generic typed types for 'got' section
                    #      like list[int] or tuple[int, str]
                    #      (right now it just shows list)
                    raise TypeError(
                        f"{func.__qualname__}(): '{name}' expected "
                        f"{pred.render_msg(val)}"
                        f"{' ' + conditions if conditions != '()' else ''}, "
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

            if not matches_hint(out, hints["return"], DEFAULT_ENFORCE_OPTIONS):
                raise TypeError(
                    f"{func.__qualname__}(): return expected "
                    f"{type_repr(hints['return'])}, got {type_repr(type(out))}"
                )

            return out

        return wrapper

    return decorator


def coerce_types(
    **coercers: Coercer,
) -> Callable[[Callable[P, T]], Callable[..., T]]:
    """Decorator that coerces the types of function parameters using coercer functions.

    This decorator is particularly useful for coercing string arguments into
    their proper types when using CLI/ENV arguments, web handlers, enums, and JSONs.

    Args:
        coercers (Coercer): A mapping of argument names
            to coercer functions
    """

    def decorator(func: Callable[P, T]) -> Callable[..., T]:
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
