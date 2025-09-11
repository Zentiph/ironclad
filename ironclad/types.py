"""types.py

Types for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from dataclasses import dataclass
from typing import Literal, NamedTuple, TypeAlias


@dataclass(frozen=True)
class EnforceOptions:
    """A configuration of options for the enforce_types decorator."""

    allow_subclasses: bool = True
    """Whether to allow subclasses to count as a valid type for a parameter."""
    check_defaults: bool = True
    """Whether to apply defaults for missing arguments."""
    strict_bools: bool = True
    """Whether to strictly disallow bools to count as integers."""


DEFAULT_ENFORCE_OPTIONS: EnforceOptions = EnforceOptions()


_ReleaseLevel: TypeAlias = Literal["alpha", "beta", "candidate", "final"]


class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: _ReleaseLevel
