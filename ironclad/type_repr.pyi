from typing import Any, Final

from .types import ClassInfo

__all__: Final[list[str]]

def class_info_to_str(t: ClassInfo, /) -> str: ...
def type_repr(hint: Any, /) -> str: ...
