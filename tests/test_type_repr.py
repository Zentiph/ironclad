"""Test type representation functions."""

from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypeVar

from ironclad.type_repr import class_info_to_str, type_repr


class Custom:
    """Non-builtin class for repr tests."""


T = TypeVar("T")
Constrained = TypeVar("Constrained", int, str)
Bounded = TypeVar("Bounded", bound=Custom)


def test_type_repr_handles_builtin_any_none_and_custom() -> None:
    assert type_repr(int) == "int"
    assert type_repr(None) == "None"
    assert type_repr(Any) == "Any"
    assert type_repr(Custom) == "test_repr.Custom"


def test_type_repr_handles_literal_annotated_and_type() -> None:
    assert type_repr(Literal[1, "a"]) == "1 or 'a'"
    assert type_repr(Annotated[int, "note"]) == "int"
    assert type_repr(type[Custom]) == "type[test_repr.Custom]"


def test_type_repr_flattens_and_dedupes_unions() -> None:
    assert type_repr(int | str | int) == "int or str"
    assert type_repr(int | None) == "int or None"


def test_type_repr_collections_and_sequences() -> None:
    assert type_repr(tuple[int, ...]) == "tuple[int, ...]"
    assert type_repr(tuple[int, str]) == "tuple[int, str]"
    assert type_repr(list[Custom]) == "list[test_repr.Custom]"
    assert type_repr(dict[str, int]) == "dict[str, int]"
    assert type_repr(Sequence[int]) == "Sequence[int]"


def test_type_repr_type_vars_constraints_and_bounds() -> None:
    assert type_repr(T) == "T"
    assert type_repr(Constrained) == "int or str"
    assert type_repr(Bounded) == "test_repr.Custom"


def test_class_info_to_str_accepts_union_and_tuple_shapes() -> None:
    assert class_info_to_str(int) == "int"
    assert class_info_to_str(int | str | int) == "int | str"
    assert class_info_to_str((int, (str, Custom))) == "int | str | Custom"
