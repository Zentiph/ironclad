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
    "DEFAULT_ENFORCE_OPTIONS",
    "EnforceOptions",
    "enforce_types",
    "enforce_values",
]

__title__ = "ironclad"
__author__ = "Zentiph"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Zentiph"
# __version__ =
# TODO: add version parse from version info

from . import predicates
from .arg_validation import (
    DEFAULT_ENFORCE_OPTIONS,
    EnforceOptions,
    enforce_types,
    enforce_values,
)
