from typing import overload


@overload
def func(s: str) -> bool:
    return True


@overload
def func(x: int, y: int) -> bool:
    return False
