# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

import six


def validate(compression):
    """
    Validate the compression string.

    Parameters
    ----------
    compression : str or None

    Returns
    -------
    compression : str or None
        In canonical form.

    Raises
    ------
    ValueError
    """
    if not compression:
        return None

    if compression == b'\0\0\0\0':
        return None

    if isinstance(compression, bytes):
        compression = compression.decode('ascii')

    if compression not in ('zlib', 'bzp2'):
        raise ValueError(
            "Supported compression types are: 'zlib' and 'bzp2'")

    return compression


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
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return zlib.compressobj()
    elif compression == 'bzp2':
        try:
            import bz2
        except ImportError:
            raise ImportError(
                "Your Python does not have the bz2 library, "
                "therefore the compressed block in this ASDF file "
                "can not be decompressed.")
        return bz2.BZ2Compressor()
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

    if isinstance(compression, six.text_type):
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


def compress(fd, data, compression, block_size=1 << 16):
    """
    Compress array data and write to a file.

    Parameters
    ----------
    fd : generic_io.GenericIO object
        The file to write to.

    data : buffer
        The buffer of uncompressed data

    compression : str
        The type of compression to use.

    block_size : int, optional
        The size of blocks (in raw data) to process at a time.
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    for i in range(0, len(data), block_size):
        fd.write(encoder.compress(data[i:i+block_size]))
    fd.write(encoder.flush())


def get_compressed_size(data, compression, block_size=1 << 16):
    """
    Returns the number of bytes required when the given data is
    compressed.

    Parameters
    ----------
    data : buffer

    compression : str
        The type of compression to use.

    Returns
    -------
    bytes : int
    """
    compression = validate(compression)
    encoder = _get_encoder(compression)

    l = 0
    for i in range(0, len(data), block_size):
        l += len(encoder.compress(data[i:i+block_size]))
    l += len(encoder.flush())

    return l
