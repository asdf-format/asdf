"""This module contains type aliases and protocols useful for type checking."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, AnyStr, Literal, Protocol, TypeAlias

import numpy.typing as npt

from asdf.generic_io import GenericFile
from asdf.versioning import AsdfVersion

__all__ = [
    "ArrayStorage",
    "AsdfVersionLike",
    "Compression",
    "ExtensionLike",
    "FileLike",
    "FileMode",
    "FilterFn",
    "NDArray",
    "PathLike",
    "Reader",
    "TreeKey",
    "Writer",
]


# Alternate version of `Extension` for use in type-hints
# The way `Extension` works is weird enough that it can't be replaced in actual code without a lot of changes
class ExtensionLike(Protocol):
    """Object that contains an extension URI and can be wrapped by ``ExtensionProxy``."""

    @property
    def extension_uri(self) -> str | None: ...


# These protocols are backports of types that were added to the standard library in 3.14.
# Whenever we drop support for Python <3.14 we can replace these with the standard library equivalents.
class Reader(Protocol[AnyStr]):  # pyrefly: ignore[variance-mismatch]
    """Object with a ``read`` method that returns string or bytes."""

    def read(self, /) -> AnyStr: ...


class Writer(Protocol[AnyStr]):  # pyrefly: ignore[variance-mismatch]
    """Object with a ``write`` method that accepts string or bytes."""

    def write(self, data: AnyStr, /) -> None: ...


# Ideally this would be `str | int | bool`
# Unfortunately this becomes a headache since mapping keys aren't covariant
# See: https://github.com/python/typing/pull/273
# The solution suggested here: https://github.com/python/mypy/issues/6001#issuecomment-1331906818
# fails when you try to actually index the map.
# Hopefully someday we will find a way to specialize this type more.

#: Valid ASDF tree keys
TreeKey: TypeAlias = Any

#: Local file path or remote file URI
PathLike: TypeAlias = str | Path
#: Readable/writable file object or the path or URI of an openable file
FileLike: TypeAlias = PathLike | Reader | Writer | GenericFile
#: A type interpretable as a version number
AsdfVersionLike: TypeAlias = AsdfVersion | str | list[int] | tuple[int, ...]

#: Supported modes for opening a file
FileMode: TypeAlias = Literal["r", "w", "rw"]

# TODO: find a way to represent this where it will accept arbitrary strings but still suggest the set of literals
#: Supported compression types
Compression: TypeAlias = Literal["zlib", "bzp2", "lz4", "input", ""] | str | None
#: Supported array storage modes
ArrayStorage: TypeAlias = Literal["internal", "external", "inline", "streamed"] | None

#: Function used to filter nodes in an ASDF tree
FilterFn: TypeAlias = Callable[[Any], bool] | Callable[[Any, Any], bool]

#: ASDF-compatible multi-dimensional array
NDArray: TypeAlias = npt.NDArray[Any]
