from collections.abc import Callable
from typing import Any, Final, ParamSpec, TypeVar

from .predicates import Predicate
from .types import DEFAULT_ENFORCE_OPTIONS, ClassInfo, EnforceOptions

P = ParamSpec("P")
T = TypeVar("T")

Coercer = Callable[[Any], Any]

__all__: Final[list[str]]

def enforce_types(
    options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    /,
    **types: ClassInfo,
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...
def enforce_annotations(
    *, check_return: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...
def coerce_types(
    **coercers: Coercer,
) -> Callable[[Callable[P, T]], Callable[..., T]]: ...
def enforce_values(
    **predicate_map: Predicate[Any],
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...
