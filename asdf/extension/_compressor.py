"""
Compressor is an interface to implement extensions to the compression
module. Extensions will typically subclass the Compressor ABC and
provide that subclass as a setuptools entry point.

Note that this interface has similar patterns to Converter.  This
interface is designed for compression and decompression of ASDF
binary array blocks, while Converter is designed for serialization
of custom Python types into the YAML tree.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


@runtime_checkable
class CompressionPlugin(Protocol):
    """A compression plugin with an associated label.

    For implementations of the actual compress/decompress methods,
    see the `Compress` and `Decompress` protocols.
    """

    @property
    @abc.abstractmethod
    def label(self) -> bytes:
        """
        Get the 4-byte label identifying this compression

        Returns
        -------
        label : bytes
            The compression label
        """
        ...


@runtime_checkable
class Compress(CompressionPlugin, Protocol):
    """A compression plugin that implements ``compress``."""

    def compress(self, data: memoryview, **kwargs) -> Iterator[bytes]:
        """
        Compress ``data``, yielding the results. The yield may be
        block-by-block, or all at once.

        Parameters
        ----------
        data : memoryview
            The data to compress. Must be contiguous and 1D, with
            the underlying ``itemsize`` preserved.
        **kwargs
            Keyword arguments to be passed to the underlying compression
            function

        Yields
        ------
        compressed : bytes-like
            A block of compressed data
        """
        raise NotImplementedError


@runtime_checkable
class Decompress(CompressionPlugin, Protocol):
    """A compression plugin that implements ``decompress``."""

    def decompress(self, data: Iterable[bytes], out: memoryview, **kwargs) -> int:
        """
        Decompress ``data``, writing the result into ``out``.

        Parameters
        ----------
        data : Iterable of bytes-like
            An Iterable of bytes-like objects containing chunks
            of compressed data.
        out : read-write bytes-like
            A contiguous, 1D output array, of equal or greater length
            than the decompressed data.
        **kwargs
            Keyword arguments to be passed to the underlying decompression
            function

        Returns
        -------
        nbytes : int
            The number of bytes written to ``out``
        """
        raise NotImplementedError


class Compressor(Compress, Decompress):
    """
    Abstract base class for plugins that compress binary data.

    Implementing classes must provide the ``labels`` property, and
    at least one of the `compress()` and `decompress()` methods.
    May also provide a constructor.
    """

    @classmethod
    def __subclasshook__(cls, class_):
        if cls is Compressor:
            return hasattr(class_, "label") and (hasattr(class_, "compress") or hasattr(class_, "decompress"))
        return NotImplemented  # pragma: no cover
