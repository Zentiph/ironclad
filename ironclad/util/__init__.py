"""
util
----

A package containing internal util functions for ironclad.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = ["as_predicate", "matches_hint"]

from .compile import (
    _spec_contains_int as _spec_contains_int,
    as_predicate,
    matches_hint,
)
from .perf import (
    _fast_bind as _fast_bind,
    _make_plan as _make_plan,
    _to_call as _to_call,
)
