"""
_util
-----

A package containing internal util functions for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = ["as_predicate", "matches_hint", "fast_bind", "make_plan", "to_call"]

from .compile import as_predicate, matches_hint
from .perf import fast_bind, make_plan, to_call
