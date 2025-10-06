"""
ironclad is a lightweight toolkit for enforcing strict runtime contracts.

ironclad enforces types, value sets, predicates, and more
without repetitive `if ... raise` boilerplate.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details.
"""

from __future__ import annotations

from typing import Literal, NamedTuple, TypeAlias

__all__ = [
    "DEFAULT_ENFORCE_OPTIONS",
    "ClassInfo",
    "EnforceOptions",
    "Multimethod",
    "class_info_to_str",
    "coerce_types",
    "enforce_annotations",
    "enforce_types",
    "enforce_values",
    "matches_hint",
    "predicates",
    "runtime_overload",
    "type_repr",
    "version_info",
]


__title__ = "ironclad"
__author__ = "Zentiph"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Zentiph"
__version__ = "0.1.0a"

__path__ = __import__("pkgutil").extend_path(__path__, __name__)


from . import predicates
from .arg_validation import (
    coerce_types,
    enforce_annotations,
    enforce_types,
    enforce_values,
)
from .multimethod import Multimethod, runtime_overload
from .predicates import matches_hint
from .repr import class_info_to_str, type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, ClassInfo, EnforceOptions

_ReleaseLevel: TypeAlias = Literal["alpha", "beta", "candidate", "final"]


class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: _ReleaseLevel


def _parse_version(v: str) -> _VersionInfo:
    m = __import__("re").match(
        r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<mic>\d+)(?:(?P<lvl>a|b|rc))?$",
        v,
    )
    if not m:
        # fallback if someone sets a non-PEP440 string
        return _VersionInfo(0, 0, 0, "alpha")

    lvl_map: dict[str | None, _ReleaseLevel] = {
        None: "final",
        "a": "alpha",
        "b": "beta",
        "rc": "candidate",
    }
    lvl = m.group("lvl")
    return _VersionInfo(
        int(m.group("maj")),
        int(m.group("min")),
        int(m.group("mic")),
        lvl_map[lvl],
    )


version_info = _parse_version(__version__)

del _parse_version
