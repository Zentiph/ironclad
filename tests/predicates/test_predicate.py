"""Tests for the predicate class."""

from collections.abc import Sized

import pytest

from ironclad.predicates import Predicate


def is_pos(x: int) -> bool:
    return x > 0


def longer_than_three(collection: Sized) -> bool:
    return len(collection) > 3


def test_call() -> None:
    pred = Predicate(is_pos, "is positive")
    assert pred(1) is True, "Predicate call did not return the expected value."
    assert pred(-1) is False, "Predicate call did not return the expected value."


def test_getters() -> None:
    pred1 = Predicate(is_pos, "is positive")
    assert pred1.func == is_pos
    assert pred1.name == "is positive"
    assert pred1.msg == "is positive"  # takes name if None

    pred2 = Predicate(
        longer_than_three, "longer than 3", "sized object had 3 or less items"
    )
    assert pred2.func == longer_than_three
    assert pred2.name == "longer than 3"
    assert pred2.msg == "sized object had 3 or less items"


def test_message_rendering() -> None:
    pred1 = Predicate(is_pos, "is positive", "expected positive number, got {x}")
    assert pred1.render_msg(-2) == "expected positive number, got -2"

    pred2 = Predicate(
        longer_than_three,
        "longer than 3",
        lambda x: "expected collection with length > 3, got length "
        f"{len(x) if x is not None else 'None'}",
    )
    assert pred2.render_msg([]) == "expected collection with length > 3, got length 0"

    # TODO: add tests for context and tree rendering once error messages are improved


def test_explaining_and_validating() -> None:
    pred = Predicate(is_pos, "is positive", "expected positive number, got {x}")
    assert pred.explain(1) is None
    assert pred.explain(-1) == "expected positive number, got -1"
    assert pred.validate(1) == 1
    with pytest.raises(ValueError):
        pred.validate(-1)


def test_with_changers() -> None:
    pred = Predicate(is_pos, "is positive")
    assert pred.with_name("abc").name == "abc"
    assert pred.with_msg("xyz").msg == "xyz"


def test_and() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: not is_pos(x), "is not positive")

    combined = pred1 & pred2
    assert combined(1) is False
    assert combined(-1) is False
    assert combined.render_msg() == "(is positive) and (is not positive)"


def test_or() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: x < 0, "is negative")

    combined = pred1 | pred2
    assert combined(1) is True
    assert combined(-1) is True
    assert combined(0) is False
    assert combined.render_msg() == "(is positive) or (is negative)"


def test_invert() -> None:
    pred = Predicate(is_pos, "is positive")

    inverted = ~pred
    assert inverted(1) is False
    assert inverted(-1) is True
    assert inverted.render_msg() == "not (is positive)"


def test_xor() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: x < 0, "is negative")

    combined = pred1 ^ pred2
    assert combined(1) is True
    assert combined(-1) is True
    assert combined(0) is False


def test_implies() -> None:
    pred1 = Predicate(is_pos, "is positive")
    pred2 = Predicate[int](lambda x: x > 3, "greater than 3")

    combined = pred1.implies(pred2)
    assert combined(4) is True
    assert combined(1) is False
    assert combined(-1) is True


if __name__ == "__main__":
    pytest.main()
