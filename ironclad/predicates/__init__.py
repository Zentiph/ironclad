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
    "all_of",
    "any_of",
    "between",
    "equals",
    "instance_of",
    "length",
    "one_of",
    "regex",
]

from .predicate import Predicate
from .predicates import (
    ALWAYS,
    NEGATIVE,
    NEVER,
    NON_EMPTY,
    NOT_NONE,
    POSITIVE,
    all_of,
    any_of,
    between,
    equals,
    instance_of,
    length,
    one_of,
    regex,
)
