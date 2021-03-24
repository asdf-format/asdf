"""
Compressor is an interface to implement extensions to the compression
module. Extensions will typically subclass the Compressor ABC and
provide that subclass as a setuptools entry point.

Note that this interface has similar patterns to Converter.  This
interface is designed for compression and decompression of ASDF
binary array blocks, while Converter is designed for serialization
of custom Python types into the YAML tree.
"""

import abc

class Compressor(abc.ABC):
    """
    Abstract base class for plugins that compress binary data.

    Implementing classes must provide the `labels` property, and
    at least one of the `compress()` and `decompress()` methods.
    May also provide a constructor.
    """
    @classmethod
    def __subclasshook__(cls, C):
        if cls is Compressor:
            return ( hasattr(C, "label") and
                    (hasattr(C, "compress") or
                     hasattr(C, "decompress")) )
        return NotImplemented # pragma: no cover


    @abc.abstractproperty
    def label(self):
        """
        Get the 4-byte label identifying this compression

        Returns
        -------
        label : bytes
            The compression label
        """
        pass # pragma: no cover


    def compress(self, data, **kwargs):
        """
        Compress `data`, yielding the results.  The yield may be
        block-by-block, or all at once.

        Parameters
        ----------
        data : bytes-like
            The data to compress. Must be contiguous and 1D, with
            the underlying `itemsize` preserved.
        **kwargs
            Keyword arguments to be passed to the underlying compression
            function

        Yields
        ------
        compressed : bytes-like
            A block of compressed data
        """
        raise NotImplementedError


    def decompress(self, data, out, **kwargs):
        """
        Decompress `data`, writing the result into `out`.

        Parameters
        ----------
        data : bytes-like
            The data to decompress. Must be contiguous and 1D.
        out : read-write bytes-like
            A contiguous, 1D output array, of equal or greater length
            than the decompressed data.
        **kwargs
            Keyword arguments to be passed to the underlying decompression
            function

        Returns
        -------
        nbytes : int
            The number of bytes written to `out`
        """
        raise NotImplementedError
