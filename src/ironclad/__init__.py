"""
ironclad
--------

A lightweight toolkit for enforcing strict runtime contracts
—types, value sets, and predicates—without repetitive `if ... raise` boilerplate.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details.
"""

__all__ = [
    "predicates",
    "coerce_types",
    "enforce_annotations",
    "enforce_types",
    "enforce_values",
    "multimethod",
    "runtime_overload",
    "type_repr",
    "DEFAULT_ENFORCE_OPTIONS",
    "EnforceOptions",
    "version_info",
    "as_predicate",
    "matches_hint",
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
from .multimethod import multimethod, runtime_overload
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions, _ReleaseLevel, _VersionInfo
from .util import as_predicate, matches_hint


def _parse_version(v: str) -> _VersionInfo:
    import re  # pylint:disable=import-outside-toplevel
    from typing import Dict, Union  # pylint:disable=import-outside-toplevel

    m = re.match(
        r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<micro>\d+)(?:(?P<pre>a|b|rc))?$",
        v,
    )
    if not m:
        # fallback if someone sets a non-PEP440 string
        return _VersionInfo(0, 0, 0, "alpha")

    pre_map: Dict[Union[str, None], _ReleaseLevel] = {
        None: "final",
        "a": "alpha",
        "b": "beta",
        "rc": "candidate",
    }
    pre = m.group("pre")
    return _VersionInfo(
        int(m.group("maj")),
        int(m.group("min")),
        int(m.group("micro")),
        pre_map[pre],
    )


version_info: _VersionInfo = _parse_version(__version__)

del _parse_version, _ReleaseLevel, _VersionInfo
