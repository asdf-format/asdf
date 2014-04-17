# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import struct

from astropy.extern import six

from . import constants
from . import util
from . import versioning


class BlockList(list):
    """
    Manages a list of `Block`s in a FINF file.
    """
    def find_or_create_block_for_array(self, arr):
        """
        For a given array, looks for an existing block containing its
        underlying data.  If not found, adds a new block to the block
        list.  Returns the index in the block list to the array.

        Parameters
        ----------
        arr : numpy.ndarray

        Returns
        -------
        pair : tuple
            - Block
            - index in block list
        """
        base = util.get_array_base(arr)
        for i, block in enumerate(self):
            if block._data is base:
                return block, i
        block = Block(base)
        self.append(block)
        return block, len(self) - 1


class Block(versioning.VersionedMixin):
    """
    Represents a single block in a FINF file.
    """

    _header_fmt = b'>BBBQQQ16s'
    _header_fmt_size = struct.calcsize(_header_fmt)

    def __init__(self, data=None):
        if data is not None:
            self._data = data
            if six.PY2:
                self._size = len(data.data)
            elif six.PY3:
                self._size = data.data.nbytes
        else:
            self._data = None
            self._size = None

        self._fd = None
        self._header_size = None
        self._offset = None
        self._data_offset = None
        self._allocated = None
        self._encoding = None
        self._memmapped = False

    def __repr__(self):
        return '<Block alloc: {0} size: {1} encoding: {2}>'.format(
            self._allocated, self._size, self._encoding)

    @classmethod
    def read(cls, fd):
        """
        Read a Block from the given Python file-like object.  The file
        position should be at the beginning of the block header (at
        the block magic token).

        If the file is seekable, the reading or memmapping of the
        actual data is postponed until an array requests it.  If the
        file is a stream, we have to read it right now.
        """
        if fd.seekable():
            offset = fd.tell()

        buff = fd.read(len(constants.BLOCK_MAGIC))
        if len(buff) == 0:
            return None

        if buff != constants.BLOCK_MAGIC:
            raise ValueError(
                "Bad magic number in block. "
                "This may indicate an internal inconsistency about the sizes "
                "of the blocks in the file.")

        buff = fd.read(2)
        header_size, = struct.unpack('>H', buff)
        if header_size < cls._header_fmt_size:
            raise ValueError(
                "Header size must be > {0}".format(cls._header_fmt_size))

        buff = fd.read(header_size)
        (major, minor, micro, allocated_size, used_size, checksum, encoding) = \
            struct.unpack_from(cls._header_fmt, buff[:cls._header_fmt_size])

        self = cls()
        self.version = (major, minor, micro)

        if fd.seekable():
            # If the file is seekable, we can delay reading the actual
            # data until later.
            self._fd = fd
            self._header_size = header_size
            self._offset = offset
            self._data_offset = fd.tell()
            self._allocated = allocated_size
            self._size = used_size
            self._encoding = encoding
            fd.fast_forward(allocated_size)
        else:
            # If the file is a stream, we need to get the data now.
            self._size = used_size
            self._allocated = allocated_size
            self._data = fd.read_into_array(used_size)
            fd.fast_forward(allocated_size - used_size)

        return self

    def update(self):
        """
        Update a block in-place on disk.
        """
        raise NotImplementedError()

    def write(self, fd):
        """
        Write a block to the given Python file-like object.

        If the block is already memmapped from the given file object,
        the file position is moved to the end of the block and nothing
        more.
        """
        if self._memmapped and self._fd == fd:
            fd.seek(10 + self._header_size + self._allocated, 1)
            return

        self._allocated = self._size
        self._offset = fd.tell()
        self._header_size = self._header_fmt_size

        version = self.version
        fd.write(constants.BLOCK_MAGIC)
        fd.write(struct.pack(b'>H', self._header_size))
        fd.write(struct.pack(
            self._header_fmt,
            version[0], version[1], version[2],
            self._allocated, self._size, 0, b''))

        self._data_offset = fd.tell()

        fd.write(self._data.data)

    @property
    def data(self):
        """
        The data for the block, as a Python buffer object.
        """
        if self._data is None:
            if self._fd.is_closed():
                raise IOError(
                    "FINF file has already been closed. "
                    "Can not get the data.")

            if self._fd.can_memmap():
                self._data = self._fd.memmap_array(
                    self._data_offset, self._size)
                self._memmapped = True

            else:
                # Be nice and restore the file position.
                curpos = self._fd.tell()
                try:
                    self._fd.seek(self._data_offset)
                    self._data = self._fd.read_into_array(self._size)
                finally:
                    self._fd.seek(curpos)

        return self._data.data
