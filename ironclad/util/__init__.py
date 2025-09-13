"""
A package containing internal util functions for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = [
    "fast_bind",
    "make_plan",
    "to_call_args",
]

from .perf import fast_bind, make_plan, to_call_args
