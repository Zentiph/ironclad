"""Tests for the predicates module (not the Predicate class)."""

import pytest

from ironclad import predicates

ASSORTED_DATA = (1, 3.4, "hi", [1, 2], {"a": 1})


def test_always_and_never() -> None:
    for d in ASSORTED_DATA:
        assert predicates.ALWAYS(d) is True
        assert predicates.NEVER(d) is False


def test_equals() -> None:
    for d1 in ASSORTED_DATA:
        pred = predicates.equals(d1)
        for d2 in ASSORTED_DATA:
            assert pred(d2) is True if d1 == d2 else pred(d2) is False


def test_between() -> None:
    pred1 = predicates.between(1, 100, inclusive=True)
    assert pred1(23) is True
    assert pred1(48) is True
    assert pred1(1) is True
    assert pred1(100) is True
    assert pred1(0) is False
    assert pred1(101) is False

    pred2 = predicates.between(1, 100, inclusive=False)
    assert pred2(23) is True
    assert pred2(48) is True
    assert pred2(1) is False
    assert pred2(100) is False
    assert pred1(0) is False
    assert pred1(101) is False


def test_instance_of() -> None:
    pred1 = predicates.instance_of(int)
    assert pred1(1) is True
    assert pred1(-3) is True
    assert pred1(2.4) is False
    assert pred1("1") is False

    pred2 = predicates.instance_of((int, float))
    assert pred2(1) is True
    assert pred2(-3) is True
    assert pred2(2.4) is True
    assert pred2("1") is False


def test_not_none() -> None:
    assert predicates.NOT_NONE(1) is True
    assert predicates.NOT_NONE(2.3) is True
    assert predicates.NOT_NONE("hi") is True
    assert predicates.NOT_NONE([1, 2]) is True
    assert predicates.NOT_NONE(()) is True
    assert predicates.NOT_NONE([None]) is True
    assert predicates.NOT_NONE(None) is False


def test_positive() -> None:
    assert predicates.POSITIVE(1) is True
    assert predicates.POSITIVE(2.3) is True
    assert predicates.POSITIVE(float("inf")) is True
    assert predicates.POSITIVE(-0.001) is False
    assert predicates.POSITIVE(-10) is False
    assert predicates.POSITIVE(float("-inf")) is False
    assert predicates.POSITIVE(0) is False


if __name__ == "__main__":
    pytest.main()
