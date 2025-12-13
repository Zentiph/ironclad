"""Tests for argument validation decorators."""

# DISABLE TYPE CHECKING ERRORS FOR MISSING
# ANNOTATIONS FOR THIS FILE
# mypy: disable-error-code=no-untyped-def
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

import pytest

from ironclad.arg_validation import (
    coerce_types,
    enforce_annotations,
    enforce_types,
    enforce_values,
)
from ironclad.predicates import Predicate
from ironclad.types import EnforceOptions


def test_enforce_types_accepts_valid_and_rejects_invalid() -> None:
    @enforce_types(x=int, y=str)
    def func(x, y="ok"):
        return f"{x}-{y}"

    assert func(1, "go") == "1-go"
    assert func(2) == "2-ok"

    with pytest.raises(TypeError, match=r"'x' expected 'int'"):
        func("bad", "ok")

    with pytest.raises(TypeError, match=r"no bools as ints"):
        func(True, "ok")  # noqa: FBT003 (boolean positional arg)


def test_enforce_types_disallows_subclasses_when_configured() -> None:
    opts = EnforceOptions(allow_subclasses=False)

    @enforce_types(opts, x=int)
    def func(x):
        return x

    assert func(3) == 3

    with pytest.raises(TypeError, match=r"no subclasses"):
        func(True)  # noqa: FBT003 (boolean positional arg)


def test_enforce_types_unknown_param_raises() -> None:
    with pytest.raises(ValueError, match="Unknown parameter 'z'"):

        @enforce_types(z=int)
        def _(x):
            return x


def test_enforce_annotations_enforces_parameters_and_return() -> None:
    @enforce_annotations()
    def add(x: int, y: int) -> int:
        return x + y

    assert add(1, 2) == 3

    @enforce_annotations()
    def bad_return(x: int) -> str:
        return x  # type: ignore[return-value]

    with pytest.raises(TypeError, match=r"return expected .*str"):
        bad_return(5)


def test_enforce_annotations_can_skip_return_check() -> None:
    @enforce_annotations(check_return=False)
    def echo(x: int) -> str:
        return x  # type: ignore[return-value]

    assert echo(7) == 7  # type: ignore[comparison-overlap]


def test_coerce_types_coerces_args_kwargs_and_defaults() -> None:
    @coerce_types(x=int, y=int)
    def func(x, y=3, *, z=4, **extra):
        return x, y, z, extra

    assert func("1", "2", z="5", note="hi") == (1, 2, "5", {"note": "hi"})
    # y default should still be coerced
    assert func("3") == (3, 3, 4, {})


def test_coerce_types_works_with_kwonly_and_varargs() -> None:
    @coerce_types(x=int)
    def func(x, *args, **kwargs):
        return x, args, kwargs

    assert func("2", "extra", key="val") == (2, ("extra",), {"key": "val"})
    assert func(x="4") == (4, (), {})


def test_enforce_values_passes_and_fails_with_predicates() -> None:
    positive = Predicate[int](lambda x: x > 0, "positive", "expected positive")

    @enforce_values(x=positive)
    def func(x):
        return x

    assert func(10) == 10

    with pytest.raises(
        ValueError, match=r"'x' failed constraint: expected positive; got 0"
    ):
        func(0)


def test_enforce_values_unknown_param_raises() -> None:
    with pytest.raises(ValueError, match="Unknown parameter 'y'"):

        @enforce_values(y=Predicate(lambda x: True, "dummy"))
        def _(x):
            return x
