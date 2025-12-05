"""Tests for the predicate class."""

from collections.abc import Iterable, Sized

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


def test_explain() -> None:
    pred = Predicate(is_pos, "is positive", "expected positive number, got {x}")
    assert pred.explain(1) is None
    assert pred.explain(-1) == "expected positive number, got -1"


def test_validate() -> None:
    pred = Predicate(is_pos, "is positive", "expected positive number, got {x}")
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


def test_clone() -> None:
    pred = Predicate(is_pos, "is positive")

    clone = pred.clone()
    assert clone.name == pred.name
    assert clone.msg == pred.msg
    assert clone.func == pred.func
    # ensuring that the context is copied
    assert clone.render_with_context(0) == clone.render_with_context(0)


def test_lift() -> None:
    pred = Predicate(is_pos, "is positive")

    def check_all_positive(xs: Iterable[int]) -> bool:
        return all(pred.func(x) for x in xs)

    lifted = pred.lift(
        check_all_positive,
        "all positive",
        "expected positive element",
    )
    assert lifted([1, 1]) is True
    assert lifted([0, 1]) is False
    # check the output message is longer (due to increased context chain)
    assert len(lifted.render_with_context()) > len(pred.render_with_context())


def test_on() -> None:
    class Data:
        def __init__(self, data: int) -> None:
            self.data = data

    data1 = Data(3)
    data2 = Data(-1)
    pred = Predicate(is_pos, "is positive")

    on_data: Predicate[Data] = pred.on(lambda o: o.data)
    assert on_data(data1) is True
    assert on_data(data2) is False


def test_quantify() -> None:
    pred = Predicate(is_pos, "is positive")

    def only_one(xs: Iterable[bool]) -> bool:
        found = False
        for x in xs:
            if x and found:
                return False
            if x and not found:
                found = True
        return found

    quantified = pred.quantify(only_one, "only one", prefix="only one element: ")
    assert quantified([10, -1, -1]) is True
    assert quantified([-1, -1, -1]) is False
    assert quantified([10, -1, 10]) is False


def test_all() -> None:
    pred = Predicate(is_pos, "is positive")

    quantified = pred.all()
    assert quantified([1, 2, 3]) is True
    assert quantified([0, 1, 2]) is False
    assert quantified([-1, 0, 1]) is False
    assert quantified([-2, -1, 0]) is False


def test_any() -> None:
    pred = Predicate(is_pos, "is positive")

    quantified = pred.any()
    assert quantified([1, 2, 3]) is True
    assert quantified([0, 1, 2]) is True
    assert quantified([-1, 0, 1]) is True
    assert quantified([-2, -1, 0]) is False


def test_at_least() -> None:
    pred = Predicate(is_pos, "is positive")

    at_least_two = pred.at_least(2)
    assert at_least_two([1, 2, 3]) is True
    assert at_least_two([0, 1, 2]) is True
    assert at_least_two([-1, 0, 1]) is False
    assert at_least_two([-2, -1, 0]) is False

    at_least_one = pred.at_least(1)
    assert at_least_one([1, 2, 3]) is True
    assert at_least_one([0, 1, 2]) is True
    assert at_least_one([-1, 0, 1]) is True
    assert at_least_one([-2, -1, 0]) is False

    at_least_zero = pred.at_least(0)
    assert at_least_zero([1, 2, 3]) is True
    assert at_least_zero([0, 1, 2]) is True
    assert at_least_zero([-1, 0, 1]) is True
    assert at_least_zero([-2, -1, 0]) is True

    with pytest.raises(ValueError):
        pred.at_least(-10)

    # unreachable n, always False
    at_least_five = pred.at_least(5)
    assert at_least_five([1, 1, 1]) is False


def test_at_most() -> None:
    pred = Predicate(is_pos, "is positive")

    at_most_two = pred.at_most(2)
    assert at_most_two([1, 2, 3]) is False
    assert at_most_two([0, 1, 2]) is True
    assert at_most_two([-1, 0, 1]) is True
    assert at_most_two([-2, -1, 0]) is True

    at_most_one = pred.at_most(1)
    assert at_most_one([1, 2, 3]) is False
    assert at_most_one([0, 1, 2]) is False
    assert at_most_one([-1, 0, 1]) is True
    assert at_most_one([-2, -1, 0]) is True

    at_most_zero = pred.at_most(0)
    assert at_most_zero([1, 2, 3]) is False
    assert at_most_zero([0, 1, 2]) is False
    assert at_most_zero([-1, 0, 1]) is False
    assert at_most_zero([-2, -1, 0]) is True

    with pytest.raises(ValueError):
        pred.at_most(-10)

    # unreachable n, always True
    at_most_five = pred.at_most(5)
    assert at_most_five([1, 1, 1]) is True


def test_exactly() -> None:
    pred = Predicate(is_pos, "is positive")

    exactly_two = pred.exactly(2)
    assert exactly_two([0, 0, 1, 1]) is True
    assert exactly_two([0, 0, 0, 1]) is False
    assert exactly_two([1, 1, 1, 1]) is False

    exactly_zero = pred.exactly(0)
    assert exactly_zero([0, 0, 0, 0]) is True
    assert exactly_zero([0, 0, 0, 1]) is False
    assert exactly_zero([0, 0, 1, 1]) is False
    assert exactly_zero([0, 1, 1, 1]) is False
    assert exactly_zero([1, 1, 1, 1]) is False

    with pytest.raises(ValueError):
        pred.exactly(-10)


def test_bool() -> None:
    pred = Predicate(is_pos, "is positive")

    with pytest.raises(TypeError):
        bool(pred)


if __name__ == "__main__":
    pytest.main()
