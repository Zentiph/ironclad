from typing import Any

from .types import ClassInfo

__all__: list[str]

def class_info_to_str(t: ClassInfo, /) -> str: ...
def type_repr(hint: Any, /) -> str: ...
