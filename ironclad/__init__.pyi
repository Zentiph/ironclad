from typing import Final, Literal, NamedTuple, TypeAlias

__all__: Final[list[str]]

__title__: Final[str]
__author__: Final[str]
__license__: Final[str]
__copyright__: Final[str]
__version__: Final[str]

from . import predicates as predicates
from . import type_repr as type_repr
from .arg_validation import (
    coerce_types as coerce_types,
)
from .arg_validation import (
    enforce_annotations as enforce_annotations,
)
from .arg_validation import (
    enforce_types as enforce_types,
)
from .arg_validation import (
    enforce_values as enforce_values,
)
from .multimethod import Multimethod as Multimethod
from .multimethod import runtime_overload as runtime_overload
from .types import DEFAULT_ENFORCE_OPTIONS as DEFAULT_ENFORCE_OPTIONS
from .types import ClassInfo as ClassInfo
from .types import EnforceOptions as EnforceOptions

_ReleaseLevel: TypeAlias = Literal["alpha", "beta", "candidate", "final"]

class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: _ReleaseLevel

version_info: _VersionInfo
