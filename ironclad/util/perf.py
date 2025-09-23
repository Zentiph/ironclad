"""
Performance helper functions.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import inspect
from dataclasses import dataclass
from typing import Any

__all__ = ["fast_bind", "make_plan", "to_call_args"]


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


def make_plan(sig: inspect.Signature) -> _Plan:
    """Make a plan for applying defaults to function signature arguments.

    Args:
        sig (inspect.Signature): The function signature.

    Returns:
        _Plan: The signature binding plan.
    """
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


def fast_bind(
    plan: _Plan,
    sig: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    apply_defaults: bool,
) -> dict[str, Any]:
    """Fast bind function signature arguments using a plan in order to save time.

    Args:
        plan (_Plan): The signature binding plan.
        sig (inspect.Signature): The function signature.
        args (tuple[Any, ...]): The function's arguments.
        kwargs (dict[str, Any]): The function's keyword arguments.
        apply_defaults (bool): Whether to apply all defaults.

    Returns:
        dict[str, Any]: The bound arguments.
    """
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


def to_call_args(
    mapping: dict[str, Any], plan: _Plan, /
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Convert a mapping to function call arguments with a signature binding plan.

    Args:
        mapping (dict[str, Any]): A mapping of parameter names to values.
        plan (_Plan): The signature binding plan.

    Returns:
        tuple[tuple[Any, ...], dict[str, Any]]: A tuple containing
        the varargs and varkwargs.
    """
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
