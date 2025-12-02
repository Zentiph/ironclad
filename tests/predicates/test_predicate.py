"""Tests for the predicate class."""

import pytest

from ironclad.predicates import Predicate


def is_pos(x: int) -> bool:
    return x > 0


def test_call() -> None:
    pred = Predicate(is_pos, "is positive")

    assert pred(1) is True, "Predicate call did not return the expected value."
    assert pred(-1) is False, "Predicate call did not return the expected value."


def test_and() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: not is_pos(x), "is not positive")
    combined = pred1 & pred2

    assert combined(1) is False, "ANDed predicate did not return the expected value."
    assert combined(-1) is False, "ANDed predicate did not return the expected value."
    assert combined.render_msg() == "(is positive) and (is not positive)"


def test_or() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: x < 0, "is negative")
    combined = pred1 | pred2

    assert combined(1) is True, "ORed predicate did not return the expected value."
    assert combined(-1) is True, "ORed predicate did not return the expected value."
    assert combined(0) is False, "ORed predicate did not return the expected value."
    assert combined.render_msg() == "(is positive) or (is negative)"


def test_invert() -> None:
    pred = Predicate(is_pos, "is positive")
    inverted = ~pred

    assert inverted(1) is False, "Inverted predicate did not return the expected value."
    assert inverted(-1) is True, "Inverted predicate did not return the expected value."
    assert inverted.render_msg() == "not (is positive)"


if __name__ == "__main__":
    pytest.main()
