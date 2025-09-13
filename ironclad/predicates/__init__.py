"""
Tools for creating predicates for logic or validation.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = [
    "Predicate",
    "as_predicate",
    "between",
    "each",
    "items",
    "keys",
    "matches_hint",
    "non_empty",
    "one_of",
    "regex",
    "spec_contains_int",
    "values",
]

from .compile import as_predicate, matches_hint, spec_contains_int
from .predicate import Predicate
from .predicates import between, each, items, keys, non_empty, one_of, regex, values
