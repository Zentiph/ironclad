"""
Tools for creating predicates for logic or validation.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details
"""

__all__ = [
    "ALWAYS",
    "NEGATIVE",
    "NEVER",
    "NON_EMPTY",
    "NOT_NONE",
    "POSITIVE",
    "Predicate",
    "as_predicate",
    "between",
    "equals",
    "instance_of",
    "items",
    "keys",
    "length",
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
    NEGATIVE,
    NEVER,
    NON_EMPTY,
    NOT_NONE,
    POSITIVE,
    between,
    equals,
    instance_of,
    items,
    keys,
    length,
    one_of,
    regex,
    values,
)
