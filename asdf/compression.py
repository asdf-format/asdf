# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import struct

import numpy as np


DEFAULT_BLOCK_SIZE = 1 << 22  #: Decompressed block size in bytes, 4MiB


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
    if not compression or compression == b'\0\0\0\0':
        return None

    if isinstance(compression, bytes):
        compression = compression.decode('ascii')

    compression = compression.strip('\0')
    if compression not in ('zlib', 'bzp2', 'lz4', 'input'):
        raise ValueError(
            "Supported compression types are: 'zlib', 'bzp2', 'lz4', or 'input'")

    return compression


class Lz4Compressor(object):
    def __init__(self, block_api):
        self._api = block_api

    def compress(self, data):
        output = self._api.compress(data, mode='high_compression')
        header = struct.pack('!I', len(output))
        return header + output


class Lz4Decompressor(object):
    def __init__(self, block_api):
        self._api = block_api
        self._size = 0
        self._pos = 0
        self._buffer = b''

    def decompress(self, data):
        if not self._size:
            data = self._buffer + data
            if len(data) < 4:
                self._buffer += data
                return b''
            self._size = struct.unpack('!I', data[:4])[0]
            data = data[4:]
            self._buffer = bytearray(self._size)
        if self._pos + len(data) < self._size:
            self._buffer[self._pos:self._pos + len(data)] = data
            self._pos += len(data)
            return b''
        else:
            offset = self._size - self._pos
            self._buffer[self._pos:] = data[:offset]
            data = data[offset:]
            self._size = 0
            self._pos = 0
            output = self._api.decompress(self._buffer)
            self._buffer = b''
            return output + self.decompress(data)


def _get_decoder(compression):
    if compression == 'zlib':
        try:
            import zlib
        except ImportError:
            raise ImportError(
                "Your Python does not have the zlib library, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return zlib.decompressobj()
    elif compression == 'bzp2':
        try:
            import bz2
        except ImportError:
            raise ImportError(
                "Your Python does not have the bz2 library, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return bz2.BZ2Decompressor()
    elif compression == 'lz4':
        try:
            import lz4.block
        except ImportError:
            raise ImportError(
                "lz4 library in not installed in your Python environment, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return Lz4Decompressor(lz4.block)
    else:
        raise ValueError(
            "Unknown compression type: '{0}'".format(compression))


def _get_encoder(compression):
    if compression == 'zlib':
        try:
            import zlib
        except ImportError:
            raise ImportError(
                "Your Python does not have the zlib library, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return zlib.compressobj()
    elif compression == 'bzp2':
        try:
            import bz2
        except ImportError:
            raise ImportError(
                "Your Python does not have the bz2 library, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return bz2.BZ2Compressor()
    elif compression == 'lz4':
        try:
            import lz4.block
        except ImportError:
            raise ImportError(
                "lz4 library in not installed in your Python environment, "
                "therefore the block in this ASDF file "
                "can not be compressed.")
        return Lz4Compressor(lz4.block)
    else:
        raise ValueError(
            "Unknown compression type: '{0}'".format(compression))


def to_compression_header(compression):
    """
    Converts a compression string to the four byte field in a block
    header.
    """
    if not compression:
        return b''

    if isinstance(compression, str):
        return compression.encode('ascii')

    return compression


def decompress(fd, used_size, data_size, compression):
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

    Returns
    -------
    array : numpy.array
         A flat uint8 containing the decompressed data.
    """
    buffer = np.empty((data_size,), np.uint8)

    compression = validate(compression)
    decoder = _get_decoder(compression)

    i = 0
    for block in fd.read_blocks(used_size):
        decoded = decoder.decompress(block)
        if i + len(decoded) > data_size:
            raise ValueError("Decompressed data too long")
        buffer.data[i:i+len(decoded)] = decoded
        i += len(decoded)

    if hasattr(decoder, 'flush'):
        decoded = decoder.flush()
        if i + len(decoded) > data_size:
            raise ValueError("Decompressed data too long")
        elif i + len(decoded) < data_size:
            raise ValueError("Decompressed data too short")
        buffer[i:i+len(decoded)] = decoded

    return buffer


def compress(fd, data, compression, block_size=DEFAULT_BLOCK_SIZE):
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

    block_size : int, optional
        Input data will be split into blocks of this size (in bytes) before compression.
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    # We can have numpy arrays here. While compress() will work with them,
    # it is impossible to split them into fixed size blocks without converting
    # them to bytes.
    if isinstance(data, np.ndarray):
        data = data.tobytes()

    for i in range(0, len(data), block_size):
        fd.write(encoder.compress(data[i:i+block_size]))
    if hasattr(encoder, "flush"):
        fd.write(encoder.flush())


def get_compressed_size(data, compression, block_size=DEFAULT_BLOCK_SIZE):
    """
    Returns the number of bytes required when the given data is
    compressed.

    Parameters
    ----------
    data : buffer

    compression : str
        The type of compression to use.

    block_size : int, optional
        Input data will be split into blocks of this size (in bytes) before the compression.

    Returns
    -------
    bytes : int
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    l = 0
    for i in range(0, len(data), block_size):
        l += len(encoder.compress(data[i:i+block_size]))
    if hasattr(encoder, "flush"):
        l += len(encoder.flush())

    return l
