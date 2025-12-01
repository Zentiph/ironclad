from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final
from typing import overload as typing_overload

from .types import DEFAULT_ENFORCE_OPTIONS, EnforceOptions

__all__: Final[list[str]]

class InvalidOverloadError(TypeError): ...

class Multimethod:
    @typing_overload
    def __init__(
        self,
        func: Callable[..., Any],
        /,
        *,
        options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS,
    ) -> None: ...
    @typing_overload
    def __init__(
        self, func: None = None, /, *, options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS
    ) -> None: ...
    def overload(self, func: Callable[..., Any], /) -> Multimethod: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

def runtime_overload(
    func: Callable[..., Any], /, *, options: EnforceOptions = DEFAULT_ENFORCE_OPTIONS
) -> Multimethod: ...
