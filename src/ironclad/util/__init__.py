"""
util
----

A package containing internal util functions for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = ["as_predicate", "matches_hint"]

from .compile import _spec_contains_int, as_predicate, matches_hint
from .perf import _fast_bind, _make_plan, _to_call
