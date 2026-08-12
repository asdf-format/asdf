"""This module contains type aliases and protocols useful for type checking."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, TypeAlias, overload

import numpy as np
import numpy.typing as npt
from typing_extensions import Reader, TypeVar, Writer

from asdf.generic_io import GenericFile
from asdf.tags.core import NDArrayType
from asdf.util import _NOT_SET_TYPE
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
    "NotSetType",
    "PathLike",
    "Reader",
    "TreeKey",
    "Writer",
]


# Ideally this would be `str | int | bool`
# Unfortunately this becomes a headache since mapping keys aren't covariant
# See: https://github.com/python/typing/pull/273
# The solution suggested here: https://github.com/python/mypy/issues/6001#issuecomment-1331906818
# fails when you try to actually index the map.
# Hopefully someday we will find a way to specialize this type more.

#: Valid ASDF tree keys
TreeKey: TypeAlias = Any
#: A YAML node that can be passed to or returned from an ASDF converter
YamlNode: TypeAlias = Mapping[TreeKey, Any] | Sequence[Any] | str

#: Local file path or remote file URI
PathLike: TypeAlias = str | Path
#: Readable/writable file object or the path or URI of an openable file
FileLike: TypeAlias = PathLike | Reader | Writer | GenericFile
#: A type interpretable as a version number
AsdfVersionLike: TypeAlias = AsdfVersion | str

#: Supported modes for opening a file
FileMode: TypeAlias = Literal["r", "w", "rw"]

# TODO: find a way to represent this where it will accept arbitrary strings but still suggest the set of literals
#: Supported compression types
Compression: TypeAlias = Literal["zlib", "bzp2", "lz4", "input", ""] | str | bytes | None
#: Supported array storage modes
ArrayStorage: TypeAlias = Literal["internal", "external", "inline", "streamed"] | None

#: Function used to filter nodes in an ASDF tree
FilterFn: TypeAlias = Callable[[Any], bool] | Callable[[Any, Any], bool]

#: ASDF-compatible multi-dimensional array
NDArray: TypeAlias = npt.NDArray[Any] | NDArrayType

#: A 1-D byte numpy array used to read and write block data
ByteArray1D: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint8]]

NotSetType = Literal[_NOT_SET_TYPE.NOT_SET]

_Array_co = TypeVar("_Array_co", default=NDArray, covariant=True)


class ArrayCallback(Protocol[_Array_co]):
    """A callback that returns a numpy array"""

    def __call__(self) -> _Array_co: ...


#: A callback that returns a `ByteArray1D`
BlockDataCallback = ArrayCallback[ByteArray1D]


class BlockAttrCallback(ArrayCallback[ByteArray1D], Protocol):
    """A data callback that provides access to low-level block attributes."""

    @overload
    def __call__(self) -> ByteArray1D: ...
    @overload
    def __call__(self, _attr: str) -> Any: ...

    def __call__(self, _attr: str | None = None) -> ByteArray1D | Any: ...
