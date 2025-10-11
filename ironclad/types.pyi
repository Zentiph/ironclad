from types import UnionType
from typing import Final, TypeAlias

__all__: list[str] = ["DEFAULT_ENFORCE_OPTIONS", "ClassInfo", "EnforceOptions"]

class EnforceOptions:
    def __init__(
        self, *, allow_subclasses: bool, check_defaults: bool, strict_bools: bool
    ) -> None: ...

    allow_subclasses: bool
    check_defaults: bool
    strict_bools: bool

DEFAULT_ENFORCE_OPTIONS: Final[EnforceOptions] = ...
ClassInfo: TypeAlias = type | UnionType | tuple["ClassInfo", ...]
