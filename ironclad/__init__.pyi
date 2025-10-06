from __future__ import annotations

from typing import Literal, NamedTuple, TypeAlias

__all__: list[str]

__title__: str
__author__: str
__license__: str
__copyright__: str
__version__: str

_ReleaseLevel: TypeAlias = Literal["alpha", "beta", "candidate", "final"]

class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: _ReleaseLevel

version_info: _VersionInfo
