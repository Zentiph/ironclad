"""
Tools for creating predicates for logic or validation.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = [
    "ALWAYS",
    "NEVER",
    "NON_EMPTY",
    "Predicate",
    "as_predicate",
    "between",
    "equals",
    "instance_of",
    "items",
    "keys",
    "matches_hint",
    "one_of",
    "regex",
    "spec_contains_int",
    "values",
]

from .compile import as_predicate, matches_hint, spec_contains_int
from .predicate import Predicate
from .predicates import (
    ALWAYS,
    NEVER,
    NON_EMPTY,
    between,
    equals,
    instance_of,
    items,
    keys,
    one_of,
    regex,
    values,
)
