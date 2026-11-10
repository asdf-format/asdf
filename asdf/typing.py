"""This module contains type aliases and protocols useful for type checking."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from io import IOBase
from pathlib import Path
from typing import Any, Literal, Protocol, TypeAlias, overload

import numpy as np
import numpy.typing as npt
from typing_extensions import TypeVar

from asdf.generic_io import GenericFile
from asdf.tags.core import NDArrayType
from asdf.versioning import AsdfVersion

__all__ = [
    "ArrayCallback",
    "ArrayStorage",
    "AsdfVersionLike",
    "BlockAttrCallback",
    "BlockDataCallback",
    "ByteArray1D",
    "Compression",
    "FileLike",
    "FileMode",
    "FilterFn",
    "NDArray",
    "PathLike",
    "TreeKey",
]


# Ideally this would be `str | int | bool`
# Unfortunately this becomes a headache since mapping keys aren't covariant
# See: https://github.com/python/typing/pull/273
# The solution suggested here: https://github.com/python/mypy/issues/6001#issuecomment-1331906818
# fails when you try to actually index the map.
# Hopefully someday we will find a way to specialize this type more.

TreeKey: TypeAlias = Any
"""Valid ASDF tree keys"""
YamlNode: TypeAlias = Mapping[TreeKey, Any] | Sequence[Any] | str
"""A YAML node that can be passed to or returned from an ASDF converter"""

PathLike: TypeAlias = str | Path
"""Local file path or remote file URI"""
FileLike: TypeAlias = PathLike | IOBase | GenericFile
"""Readable/writable file object or the path or URI of an openable file"""
AsdfVersionLike: TypeAlias = AsdfVersion | str
"""A type interpretable as a version number"""

FileMode: TypeAlias = Literal["r", "w", "rw"]
"""Supported modes for opening a file"""

# TODO: find a way to represent this where it will accept arbitrary strings but still suggest the set of literals
Compression: TypeAlias = Literal["zlib", "bzp2", "lz4", "input", ""] | str | bytes | None
"""Supported compression types"""
ArrayStorage: TypeAlias = Literal["internal", "external", "inline", "streamed"] | None
"""Supported array storage modes"""

FilterFn: TypeAlias = Callable[[Any], bool] | Callable[[Any, Any], bool]
"""Function used to filter nodes in an ASDF tree"""

NDArray: TypeAlias = npt.NDArray[Any] | NDArrayType
"""ASDF-compatible multi-dimensional array"""

ByteArray1D: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint8]]
"""A 1-D byte numpy array used to read and write block data"""

_Array_co = TypeVar("_Array_co", default=NDArray, covariant=True)


class ArrayCallback(Protocol[_Array_co]):
    """A callback that returns a numpy array"""

    def __call__(self) -> _Array_co: ...


BlockDataCallback = ArrayCallback[ByteArray1D]
"""A callback that returns a `ByteArray1D`"""


class BlockAttrCallback(ArrayCallback[ByteArray1D], Protocol):
    """A data callback that provides access to low-level block attributes."""

    @overload
    def __call__(self) -> ByteArray1D: ...
    @overload
    def __call__(self, _attr: str) -> Any: ...

    def __call__(self, _attr: str | None = None) -> ByteArray1D | Any: ...
