"""perf.py

Performance helper functions.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

import inspect
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Union


@dataclass(frozen=True)
class _Plan:
    pos_names: Tuple[str, ...]
    vararg_name: Union[str, None]
    varkw_name: Union[str, None]
    need_kwonly_bind: bool


def make_plan(sig: inspect.Signature) -> _Plan:
    """Make a binding plan for a function signature.

    Parameters
    ----------
    sig : inspect.Signature
        The function signature

    Returns
    -------
    _Plan
        The binding plan
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


def fast_bind(  # pylint:disable=too-many-branches
    plan: _Plan,
    sig: inspect.Signature,
    args: Tuple,
    kwargs: Dict[str, Any],
    apply_defaults: bool,
) -> Dict[str, Any]:
    """Optimized argument binder that only binds what is needed.

    Parameters
    ----------
    sig : inspect.Signature
        The function's signature
    args : Tuple
        The function's args
    kwargs : Dict[str, Any]
        The function's kwargs
    apply_defaults : bool
        Whether to apply default values

    Returns
    -------
    Dict[str, Any]
        The bound arguments
    """

    # fast path if no kw-only/defaults and kwargs only fill tail names
    if plan.need_kwonly_bind:
        bound = sig.bind(*args, **kwargs)
        if apply_defaults:
            bound.apply_defaults()
        return bound.arguments

    # map pure positionals
    mapping = {}
    n = min(len(args), len(plan.pos_names))
    for i in range(n):
        mapping[plan.pos_names[i]] = args[i]

    # remaining positionals go to *varargs
    if plan.vararg_name is not None:
        mapping[plan.vararg_name] = tuple(args[n:])
    elif len(args) > n:
        # too many positionals; delegate to full bind for accurate error msg
        bound = sig.bind(*args, **kwargs)
        if apply_defaults:
            bound.apply_defaults()
        return bound.arguments

    # kwargs to names params or **varkw
    extra = {}
    for k, v in kwargs.items():
        if k in plan.pos_names:
            mapping[k] = v
        elif plan.varkw_name is not None:
            extra[k] = v
        else:
            # unexpected kw, delegate to full bind for accurate error msg
            bound = sig.bind(*args, **kwargs)
            if apply_defaults:
                bound.apply_defaults()
            return bound.arguments
    if plan.varkw_name is not None:
        mapping.setdefault(plan.varkw_name, {}).update(extra)

    # optionally inject defaults (only safe if no kw-only/defaults; else bailed already)
    if apply_defaults:
        for param in sig.parameters.values():
            if (
                param.default is not inspect.Parameter.empty
                and param.name not in mapping
            ):
                mapping[param.name] = param.default

    return mapping


def to_call(
    plan: _Plan, mapping: Dict[str, Any]
) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Convert bound arguments to function-safe args and kwargs.

    Parameters
    ----------
    plan : _Plan
        The binding plan
    mapping : Dict[str, Any]
        The argument mapping

    Returns
    -------
    Tuple[Tuple[Any, ...], Dict[str, Any]]
        The bound arguments as function-safe args and kwargs
    """

    # positional params
    args_list = [mapping[name] for name in plan.pos_names]

    # *varargs
    if plan.vararg_name and plan.vararg_name in mapping:
        args_list.extend(mapping[plan.vararg_name])
    # kwargs + **varkw
    kwargs: Dict[str, Any] = {}
    for name, val in mapping.items():
        if (
            name in plan.pos_names
            or name == plan.vararg_name
            or name == plan.varkw_name
        ):
            continue
        kwargs[name] = val
    if plan.varkw_name and plan.varkw_name in mapping:
        kwargs.update(mapping[plan.varkw_name])

    return tuple(args_list), kwargs
