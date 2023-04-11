import bz2
import struct
import warnings
import zlib

import numpy as np

from .config import get_config
from .exceptions import AsdfWarning


def validate(compression):
    """
    Validate the compression string.

    Parameters
    ----------
    compression : str, bytes or None

    Returns
    -------
    compression : str or None
        In canonical form.

    Raises
    ------
    ValueError
    """
    if not compression or compression == b"\0\0\0\0":
        return None

    if isinstance(compression, bytes):
        compression = compression.decode("ascii")

    compression = compression.strip("\0")

    builtin_labels = ["zlib", "bzp2", "lz4", "input"]
    ext_labels = _get_all_compression_extension_labels()
    all_labels = ext_labels + builtin_labels

    # An extension is allowed to override a builtin compression or another extension,
    # but let's warn the user of this.
    # TODO: is this the desired behavior?
    for i, label in enumerate(all_labels):
        if label in all_labels[i + 1 :]:
            warnings.warn(f'Found more than one compressor for "{label}"', AsdfWarning)

    if compression not in all_labels:
        msg = f"Supported compression types are: {all_labels}, not '{compression}'"
        raise ValueError(msg)

    return compression


class Lz4Compressor:
    def __init__(self):
        try:
            import lz4.block
        except ImportError as err:
            msg = (
                "lz4 library in not installed in your Python environment, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed."
            )
            raise ImportError(msg) from err

        self._api = lz4.block

    def compress(self, data, **kwargs):
        kwargs["mode"] = kwargs.get("mode", "default")
        compression_block_size = kwargs.pop("compression_block_size", 1 << 22)

        nelem = compression_block_size // data.itemsize
        for i in range(0, len(data), nelem):
            _output = self._api.compress(data[i : i + nelem], **kwargs)
            header = struct.pack("!I", len(_output))
            yield header + _output

    def decompress(self, blocks, out, **kwargs):
        _size = 0
        _pos = 0
        _partial_len = b""
        _buffer = None
        bytesout = 0

        for block in blocks:
            cast = "c"
            blk = memoryview(block).cast(cast)  # don't copy on slice

            while len(blk):
                if not _size:
                    # Don't know the (compressed) length of this block yet
                    if len(_partial_len) + len(blk) < 4:
                        _partial_len += blk
                        break  # we've exhausted the block
                    if _partial_len:
                        # If we started to fill a len key, finish filling it
                        remaining = 4 - len(_partial_len)
                        if remaining:
                            _partial_len += blk[:remaining]
                            blk = blk[remaining:]
                        _size = struct.unpack("!I", _partial_len)[0]
                        _partial_len = b""
                    else:
                        # Otherwise just read the len key directly
                        _size = struct.unpack("!I", blk[:4])[0]
                        blk = blk[4:]

                if len(blk) < _size or _buffer is not None:
                    # If we have a partial block, or we're already filling a buffer, use the buffer
                    if _buffer is None:
                        _buffer = np.empty(
                            _size,
                            dtype=np.byte,
                        )  # use numpy instead of bytearray so we can avoid zero initialization
                        _pos = 0
                    newbytes = min(_size - _pos, len(blk))  # don't fill past the buffer len!
                    _buffer[_pos : _pos + newbytes] = np.frombuffer(blk[:newbytes], dtype=np.byte)
                    _pos += newbytes
                    blk = blk[newbytes:]

                    if _pos == _size:
                        _out = self._api.decompress(_buffer, return_bytearray=True, **kwargs)
                        out[bytesout : bytesout + len(_out)] = _out
                        bytesout += len(_out)
                        _buffer = None
                        _size = 0
                else:
                    # We have at least one full block
                    _out = self._api.decompress(memoryview(blk[:_size]), return_bytearray=True, **kwargs)
                    out[bytesout : bytesout + len(_out)] = _out
                    bytesout += len(_out)
                    blk = blk[_size:]
                    _size = 0

        return bytesout


class ZlibCompressor:
    def compress(self, data, **kwargs):
        comp = zlib.compress(data, **kwargs)
        yield comp

    def decompress(self, blocks, out, **kwargs):
        decompressor = zlib.decompressobj(**kwargs)

        i = 0
        for block in blocks:
            decomp = decompressor.decompress(block)
            out[i : i + len(decomp)] = decomp
            i += len(decomp)
        return i


class Bzp2Compressor:
    def compress(self, data, **kwargs):
        comp = bz2.compress(data, **kwargs)
        yield comp

    def decompress(self, blocks, out, **kwargs):
        decompressor = bz2.BZ2Decompressor(**kwargs)

        i = 0
        for block in blocks:
            decomp = decompressor.decompress(block)
            out[i : i + len(decomp)] = decomp
            i += len(decomp)
        return i


def _get_compressor_from_extensions(compression, return_extension=False):
    """
    Look at the loaded ASDF extensions and return the first one (if any)
    that can handle this type of compression.
    `return_extension` can be used to return corresponding extension for bookkeeping purposes.
    Returns None if no match found.
    """
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    extensions = get_config().extensions

    for ext in extensions:
        for comp in ext.compressors:
            if compression == comp.label.decode("ascii"):
                if return_extension:
                    return comp, ext

                return comp

    return None


def _get_all_compression_extension_labels():
    """
    Get the list of compression labels supported via extensions
    """
    # TODO: in ASDF 3, this will be done by the ExtensionManager
    labels = []
    extensions = get_config().extensions
    for ext in extensions:
        for comp in ext.compressors:
            labels += [comp.label.decode("ascii")]
    return labels


def _get_compressor(label):
    ext_comp = _get_compressor_from_extensions(label)

    if ext_comp is not None:
        # Use an extension before builtins
        comp = ext_comp
    elif label == "zlib":
        comp = ZlibCompressor()
    elif label == "bzp2":
        comp = Bzp2Compressor()
    elif label == "lz4":
        comp = Lz4Compressor()
    else:
        msg = f"Unknown compression type: '{label}'"
        raise ValueError(msg)

    return comp


def to_compression_header(compression):
    """
    Converts a compression string to the four byte field in a block
    header.
    """
    if not compression:
        return b"\0\0\0\0"

    if isinstance(compression, str):
        return compression.encode("ascii")

    return compression


def decompress(fd, used_size, data_size, compression, config=None):
    """
    Decompress binary data in a file

    Parameters
    ----------
    fd : generic_io.GenericIO object
        The file to read the compressed data from.

    used_size : int
        The size of the compressed data

    data_size : int
        The size of the uncompressed data

    compression : str
        The compression type used.

    config : dict or None, optional
        Any kwarg parameters to pass to the underlying decompression
        function

    Returns
    -------
    array : numpy.array
         A flat uint8 containing the decompressed data.
    """
    buffer = np.empty((data_size,), np.uint8)

    compression = validate(compression)
    decoder = _get_compressor(compression)
    if config is None:
        config = {}

    blocks = fd.read_blocks(used_size)  # data is a generator
    len_decoded = decoder.decompress(blocks, out=buffer.data, **config)

    if len_decoded != data_size:
        msg = "Decompressed data wrong size"
        raise ValueError(msg)

    return buffer


def compress(fd, data, compression, config=None):
    """
    Compress array data and write to a file.

    Parameters
    ----------
    fd : generic_io.GenericIO object
        The file to write to.

    data : buffer
        The buffer of uncompressed data.

    compression : str
        The type of compression to use.

    config : dict or None, optional
        Any kwarg parameters to pass to the underlying compression
        function
    """
    compression = validate(compression)
    encoder = _get_compressor(compression)
    if config is None:
        config = {}

    # Get a contiguous, 1D memoryview of the underlying data, preserving data.itemsize
    # - contiguous: because we may not want to assume that all compressors can handle arbitrary strides
    # - 1D: so that len(data) works, not just data.nbytes
    # - itemsize: should preserve data.itemsize for compressors that want to use the record size
    # - memoryview: don't incur the expense of a memcpy, such as with tobytes()
    data = memoryview(data)
    if not data.contiguous:
        data = memoryview(data.tobytes())  # make a contiguous copy
    data = memoryview(np.frombuffer(data, dtype=data.format))  # get a 1D array that preserves byteorder
    if not data.contiguous:
        # the data will be contiguous by construction, but better safe than sorry!
        raise ValueError(data.contiguous)

    compressed = encoder.compress(data, **config)
    # Write block by block
    for comp in compressed:
        fd.write(comp)


def get_compressed_size(data, compression, config=None):
    """
    Returns the number of bytes required when the given data is
    compressed.

    Parameters
    ----------
    See `compress()`.

    Returns
    -------
    nbytes : int
        The size of the compressed data

    """

    class _ByteCountingFile:
        def __init__(self):
            self.count = 0

        def write(self, data):
            self.count += len(data)

    bcf = _ByteCountingFile()
    compress(bcf, data, compression, config=config)

    return bcf.count
