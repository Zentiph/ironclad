"""
ironclad
--------

A lightweight toolkit for enforcing strict runtime contracts
—types, value sets, and predicates—without repetitive `if ... raise` boilerplate.

:authors: Zentiph
:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE.md for more details.
"""

__all__ = [
    "predicates",
    "coerce_types",
    "enforce_annotations",
    "enforce_types",
    "enforce_values",
    "type_repr",
    "DEFAULT_ENFORCE_OPTIONS",
    "EnforceOptions",
]

__title__ = "ironclad"
__author__ = "Zentiph"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Zentiph"
# __version__ =
# TODO: add version parse from version info

from . import predicates
from .arg_validation import (
    coerce_types,
    enforce_annotations,
    enforce_types,
    enforce_values,
)
from .repr import type_repr
from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions
