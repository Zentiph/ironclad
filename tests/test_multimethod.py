"""Tests for the Multimethod runtime overload helper."""

from typing import Any

import pytest

from ironclad.multimethod import InvalidOverloadError, Multimethod, runtime_overload
from ironclad.types import EnforceOptions


def test_runtime_overload_dispatches_to_matching_overload() -> None:
    @runtime_overload
    def describe(value: int) -> str:
        return f"int:{value}"

    @describe.overload
    def _(value: str) -> str:
        return f"str:{value}"

    assert describe(3) == "int:3"
    assert describe("hi") == "str:hi"

    with pytest.raises(InvalidOverloadError, match=r"No overload of describe\(\)"):
        describe(3.14)


def test_multimethod_prefers_more_specific_overload() -> None:
    mm = Multimethod()

    @mm.overload
    def _(_value: Any) -> str:
        return "any"

    @mm.overload
    def _(_value: int) -> str:
        return "int"

    assert mm(10) == "int"
    assert mm("x") == "any"


def test_allow_subclasses_option_is_respected() -> None:
    class Animal:
        pass

    class Dog(Animal):
        pass

    animal_dispatch = Multimethod()

    @animal_dispatch.overload
    def _(value: Animal) -> str:
        return "animal"

    assert animal_dispatch(Dog()) == "animal"

    strict_dispatch = Multimethod(options=EnforceOptions(allow_subclasses=False))

    @strict_dispatch.overload
    def _(value: Animal) -> str:
        return "animal"

    with pytest.raises(InvalidOverloadError, match=r"Dog"):
        strict_dispatch(Dog())


def test_registration_order_breaks_ties_for_equal_specificity() -> None:
    mm = Multimethod()

    @mm.overload
    def _(value: int) -> str:
        return "first"

    @mm.overload
    def _(value: int) -> str:
        return "second"

    assert mm(1) == "first"


def test_bool_is_not_treated_as_int_by_default() -> None:
    mm = Multimethod()

    @mm.overload
    def _(value: int) -> str:
        return "int"

    with pytest.raises(InvalidOverloadError, match=r"bool"):
        mm(True)  # noqa: FBT003 (boolean positional arg)
