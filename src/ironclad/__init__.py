"""
ironclad
--------

A lightweight toolkit for enforcing strict runtime contracts
—types, value sets, and predicates—without repetitive `if ... raise` boilerplate.

:copyright: (c) 2025-present Zentiph
:license: MIT; see LICENSE for more details.
"""

__all__ = ["enforce_types"]

__title__ = "ironclad"
__author__ = "Zentiph"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Zentiph"
# __version__ =
# TODO: add version parse from version info

from .arg_validation import enforce_types
