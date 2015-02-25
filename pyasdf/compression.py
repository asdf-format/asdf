# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import zlib

import numpy as np

from astropy.extern import six
from astropy.extern.six.moves import xrange


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

    if compression != 'zlib':
        raise ValueError("Supported compression types are: 'zlib'")

    return compression


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
         The compression type used.  Currently, only ``zlib`` is
         supported.

    Returns
    -------
    array : numpy.array
         A flat uint8 containing the decompressed data.
    """
    buffer = np.empty((data_size,), np.uint8)

    compression = validate(compression)

    decoder = zlib.decompressobj()

    i = 0
    for block in fd.read_blocks(used_size):
        decoded = decoder.decompress(block)
        if i + len(decoded) > data_size:
            raise ValueError("Decompressed data too long")
        buffer.data[i:i+len(decoded)] = decoded
        i += len(decoded)

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
        The type of compression to use.  Currently, only ``zlib`` is
        supported.

    block_size : int, optional
        The size of blocks (in raw data) to process at a time.
    """
    compression = validate(compression)

    encoder = zlib.compressobj()

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
        The type of compression to use.  Currently, only ``zlib`` is
        supported.

    Returns
    -------
    bytes : int
    """
    compression = validate(compression)

    encoder = zlib.compressobj()

    l = 0
    for i in range(0, len(data), block_size):
        l += len(encoder.compress(data[i:i+block_size]))
    l += len(encoder.flush())

    return l
