from __future__ import annotations

import sys
from datetime import timezone
from dataclasses import dataclass as _dataclass
from typing import Any, Callable, TypeVar, overload

T = TypeVar("T")

UTC = timezone.utc


@overload
def dataclass(_cls: T) -> T: ...


@overload
def dataclass(**kwargs: Any) -> Callable[[T], T]: ...


def dataclass(_cls: T | None = None, **kwargs: Any) -> Any:
    if "slots" in kwargs and sys.version_info < (3, 10):
        kwargs.pop("slots", None)
    if _cls is None:
        return _dataclass(**kwargs)
    return _dataclass(_cls, **kwargs)
