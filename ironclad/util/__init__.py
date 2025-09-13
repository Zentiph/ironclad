"""
A package containing internal util functions for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = [
    "as_predicate",
    "fast_bind",
    "make_plan",
    "matches_hint",
    "spec_contains_int",
    "to_call_args",
]

from .compile import as_predicate, matches_hint, spec_contains_int
from .perf import fast_bind, make_plan, to_call_args
