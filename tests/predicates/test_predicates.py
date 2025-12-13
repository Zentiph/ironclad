"""Tests for the predicates module (not the Predicate class)."""

from collections.abc import Iterable, Mapping
from typing import Any

import pytest

from ironclad import predicates
from ironclad.predicates import predicates as predicates_impl

ASSORTED_DATA: tuple[Any, ...] = (1, 3.4, "hi", [1, 2], {"a": 1})


def _assert_truth_table(
    pred: predicates.Predicate[Any], truthy: Iterable[Any], falsy: Iterable[Any]
) -> None:
    for value in truthy:
        assert pred(value) is True, f"Expected {value!r} to satisfy {pred.name}"
    for value in falsy:
        assert pred(value) is False, f"Expected {value!r} to fail {pred.name}"


def test_always_and_never() -> None:
    for d in ASSORTED_DATA:
        assert predicates.ALWAYS(d) is True
        assert predicates.NEVER(d) is False


def test_equals() -> None:
    for target in ASSORTED_DATA:
        pred = predicates.equals(target)
        truthy = (target,)
        falsy = tuple(v for v in ASSORTED_DATA if v is not target and v != target)
        _assert_truth_table(pred, truthy, falsy)
        assert pred.render_msg("ignored") == f"expected == {target!r}"


def test_between() -> None:
    inclusive = predicates.between(1, 100, inclusive=True)
    _assert_truth_table(inclusive, truthy=(1, 23, 48, 100), falsy=(0, 101))
    assert inclusive.render_msg().startswith("expected 1 <= x <= 100")

    exclusive = predicates.between(1, 100, inclusive=False)
    _assert_truth_table(exclusive, truthy=(23, 48), falsy=(0, 1, 100, 101))


def test_instance_of() -> None:
    ints_only = predicates.instance_of(int)
    _assert_truth_table(ints_only, truthy=(1, -3, True), falsy=(2.4, "1"))

    number_like = predicates.instance_of((int, float))
    _assert_truth_table(number_like, truthy=(1, -3, 2.4), falsy=("1", object()))


def test_not_none() -> None:
    _assert_truth_table(
        predicates.NOT_NONE,
        truthy=(1, 2.3, "hi", [1, 2], (), [None]),
        falsy=(None,),
    )


def test_positive_and_negative() -> None:
    _assert_truth_table(
        predicates.POSITIVE,
        truthy=(1, 2.3, float("inf")),
        falsy=(-0.001, -10, float("-inf"), 0),
    )
    _assert_truth_table(
        predicates.NEGATIVE,
        truthy=(-0.001, -10, float("-inf")),
        falsy=(1, 2.3, float("inf"), 0),
    )


def test_non_empty() -> None:
    _assert_truth_table(
        predicates.NON_EMPTY,
        truthy=([1], (1,), "a", {"k": "v"}),
        falsy=([], (), "", {}),
    )


def test_all_of_and_any_of() -> None:
    positive = predicates.Predicate[int](lambda x: x > 0, "is positive")
    even = predicates.Predicate[int](lambda x: x % 2 == 0, "divisible by 2")
    divisible_by_three = predicates.Predicate[int](
        lambda x: x % 3 == 0, "divisible by 3"
    )

    all_combined = predicates.all_of(positive, even, divisible_by_three)
    _assert_truth_table(all_combined, truthy=(6,), falsy=(-6, 8, 3, -1))

    any_combined = predicates.any_of(positive, even, divisible_by_three)
    _assert_truth_table(any_combined, truthy=(6, -6, 8, 3), falsy=(-1,))

    with pytest.raises(ValueError):
        predicates.all_of()
    with pytest.raises(ValueError):
        predicates.any_of()


def test_one_of() -> None:
    pred = predicates.one_of(ASSORTED_DATA)
    _assert_truth_table(
        pred,
        truthy=ASSORTED_DATA,
        falsy=(-1, 2.1, "bye", [3, 4], {"b": 2}),
    )
    assert pred.render_msg("ignored") == f"expected one of {ASSORTED_DATA!r}"


def test_length() -> None:
    length_three = predicates.length(3)
    _assert_truth_table(
        length_three,
        truthy=([1, 2, 3], (1, 2, 3)),
        falsy=([1], [], (1, 2, 3, 4)),
    )

    length_one = predicates.length(1)
    _assert_truth_table(
        length_one,
        truthy=([1],),
        falsy=([1, 2, 3], (1, 2, 3), [], (1, 2, 3, 4)),
    )

    length_zero = predicates.length(0)
    _assert_truth_table(
        length_zero,
        truthy=([],),
        falsy=([1], [1, 2, 3], (1, 2, 3), (1, 2, 3, 4)),
    )

    neg_length = predicates.length(-2)
    _assert_truth_table(
        neg_length,
        truthy=(),
        falsy=([1, 2, 3], (1, 2, 3), [1], [], (1, 2, 3, 4)),
    )


def test_length_between() -> None:
    inclusive = predicates.length_between(2, 5, inclusive=True)
    _assert_truth_table(
        inclusive,
        truthy=([1, 2], [1, 2, 3, 4], [1, 2, 3, 4, 5]),
        falsy=([1], [], [1, 2, 3, 4, 5, 6]),
    )

    exclusive = predicates.length_between(2, 5, inclusive=False)
    _assert_truth_table(
        exclusive,
        truthy=([1, 2, 3, 4], [1, 2, 3]),
        falsy=([1, 2], [1, 2, 3, 4, 5]),
    )


def test_keys_and_values() -> None:
    even_key = predicates.Predicate[int](lambda k: k % 2 == 0, "even key")
    positive_value = predicates.Predicate[int](lambda v: v > 0, "positive value")

    keys_pred = predicates_impl.keys(even_key)
    values_pred = predicates_impl.values(positive_value)

    good_map: Mapping[int, int] = {2: 1, 4: 2}
    bad_key_map: Mapping[int, int] = {1: 1, 2: 2}
    bad_value_map: Mapping[int, int] = {2: -1, 4: 2}

    _assert_truth_table(keys_pred, truthy=(good_map,), falsy=(bad_key_map,))
    _assert_truth_table(values_pred, truthy=(good_map,), falsy=(bad_value_map,))


def test_regex() -> None:
    pred = predicates.regex(r"[a-z]+")
    _assert_truth_table(pred, truthy=("abc", "xyz"), falsy=("abc1", "123", "ABC", ""))
