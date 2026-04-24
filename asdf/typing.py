"""This module contains type aliases and protocols."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, AnyStr, Literal, Protocol

import numpy.typing as npt

from asdf.generic_io import GenericFile


# Alternate version of `Extension` for use in type-hints
# The way `Extension` works is weird enough that it can't be replaced in actual code without a lot of changes
class ExtensionLike(Protocol):
    """Object that contains an extension URI and can be wrapped by `ExtensionProxy`."""

    @property
    def extension_uri(self) -> str | None: ...


# These protocols were added to the standard library in 3.14
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
TreeKey = Any

#: Local file path or remote file URI
PathLike = str | Path
#: Readable/writable file object or the path or URI of an openable file
FileLike = PathLike | Reader | Writer | GenericFile

#: Supported modes for opening a file
FileMode = Literal["r", "w", "rw"]
#: Supported compression types
Compression = Literal["zlib", "bzp2", "lz4", "input", ""] | None
#: Supported array storage modes
ArrayStorage = Literal["internal", "external", "inline", "streamed"] | None

#: Function used to filter nodes in an ASDF tree
FilterFn = Callable[[Any], bool] | Callable[[Any, Any], bool]

NDArray = npt.NDArray
