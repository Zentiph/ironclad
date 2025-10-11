from typing import Literal, NamedTuple, TypeAlias

__all__: list[str] = [
    "DEFAULT_ENFORCE_OPTIONS",
    "ClassInfo",
    "EnforceOptions",
    "Multimethod",
    "class_info_to_str",
    "coerce_types",
    "enforce_annotations",
    "enforce_types",
    "enforce_values",
    "predicates",
    "runtime_overload",
    "type_repr",
    "version_info",
]

__title__: str
__author__: str
__license__: str
__copyright__: str
__version__: str

from . import predicates
from .arg_validation import (
    coerce_types,
    enforce_annotations,
    enforce_types,
    enforce_values,
)
from .multimethod import Multimethod, runtime_overload
from .repr import class_info_to_str, type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, ClassInfo, EnforceOptions

_ReleaseLevel: TypeAlias = Literal["alpha", "beta", "candidate", "final"]

class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: _ReleaseLevel

version_info: _VersionInfo
