from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping, Sized
from typing import Any, Final, Protocol, Self, TypeAlias, TypeVar

from ..types import ClassInfo
from .predicate import Predicate

__all__: Final[list[str]]

class _Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...
    def __le__(self, other: Self, /) -> bool: ...
    def __gt__(self, other: Self, /) -> bool: ...
    def __ge__(self, other: Self, /) -> bool: ...

C = TypeVar("C", bound=_Comparable)
T = TypeVar("T")
K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

AnyRealNumber: TypeAlias = int | float

ALWAYS: Final[Predicate[Any]]
NEVER: Final[Predicate[Any]]

def equals(value: T) -> Predicate[T]: ...
def between(low: C, high: C, /, *, inclusive: bool = True) -> Predicate[C]: ...
def instance_of(t: ClassInfo) -> Predicate[object]: ...

NOT_NONE: Final[Predicate[Any]]
POSITIVE: Final[Predicate[AnyRealNumber]]
NEGATIVE: Predicate[AnyRealNumber]

def all_of(*predicates: Predicate[T]) -> Predicate[T]: ...
def any_of(*predicates: Predicate[T]) -> Predicate[T]: ...
def one_of(
    values: Iterable[T],  # pylint:disable=redefined-outer-name
    /,
) -> Predicate[T]: ...
def length(size: int, /) -> Predicate[Sized]: ...
def length_between(
    low: int, high: int, /, *, inclusive: bool = True
) -> Predicate[Sized]: ...

NON_EMPTY: Final[Predicate[Sized]]

def keys(inner: Predicate[K]) -> Predicate[Mapping[K, Any]]: ...
def values(inner: Predicate[V]) -> Predicate[Mapping[Hashable, V]]: ...
def regex(pattern: str, flags: int = 0) -> Predicate[str]: ...
