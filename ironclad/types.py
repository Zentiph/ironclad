"""
Types for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnforceOptions:
    """A configuration of type enforcement options."""

    allow_subclasses: bool = True
    """Whether to allow subclasses to count as a valid type for a parameter."""
    check_defaults: bool = True
    """Whether to apply defaults for missing arguments."""
    strict_bools: bool = True
    """Whether to strictly disallow bools to count as integers."""


DEFAULT_ENFORCE_OPTIONS: EnforceOptions = EnforceOptions()
"""Default type enforcement options.

(allow_subclasses=True, check_defaults=True, strict_bools=True)
"""
