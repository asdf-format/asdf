# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import struct

from astropy.extern import six

from . import constants
from . import generic_io
from . import util
from . import versioning


class BlockManager(object):
    """
    Manages the `Block`s associated with a FINF file.
    """
    def __init__(self, finffile):
        # TODO: weakref?  This is cyclical
        self._finffile = finffile

        self._internal_blocks = []
        self._external_blocks = []
        self._external_blocks_by_uri = {}
        self._data_to_block_mapping = {}

    def read_internal_blocks(self, fd):
        """
        Read all internal blocks present in the file.

        Parameters
        ----------
        fd : GenericFile
            The file position must be exactly at the beginning of the
            first block header.
        """
        while True:
            block = Block().read(fd)
            if block is not None:
                self.add(block)
            else:
                break

    def add(self, block):
        """
        Add a block to the manager.
        """
        if block._external:
            self._external_blocks.append(block)
            self._external_blocks_by_uri[block._uri] = block
        else:
            block._index = len(self._internal_blocks)
            self._internal_blocks.append(block)
        if block._data is not None:
            self._data_to_block_mapping[id(block._data)] = block

    def __len__(self):
        return len(self._internal_blocks) + len(self._external_blocks)

    def __iter__(self):
        for x in self._internal_blocks:
            yield x
        for x in self._external_blocks:
            yield x

    def finalize(self, ctx):
        """
        At this point, we have a complete set of blocks for the file,
        with no extras.

        Here, they are reindexed, and possibly reorganized.
        """
        if ctx.get('exploded'):
            for block in self._internal_blocks:
                self._external_blocks.append(block)
                block._external = True
            self._internal_blocks = []

        for i, block in enumerate(self._internal_blocks):
            block._index = i
        for i, block in enumerate(self._external_blocks):
            block._index = i

    def get_block(self, source):
        """
        Given a "source identifier", return a block.

        Parameters
        ----------
        source : any
            If an integer, refers to the index of an internal block.
            If a string, is a uri to an external block.

        Return
        ------
        buffer : buffer
        """
        if isinstance(source, int):
            if source < 0 or source >= len(self._internal_blocks):
                raise ValueError("Block '{0}' not found.".format(source))
            block = self._internal_blocks[source]

        elif isinstance(source, six.string_types):
            if self._finffile.uri is not None:
                full_uri = generic_io.resolve_uri(self._finffile.uri, source)
            else:
                full_uri = None
            block = self._external_blocks_by_uri.get(full_uri)
            if block is None:
                block = Block(uri=full_uri)
                self.add(block)

        else:
            raise TypeError("Unknown source '{0}'".format(source))

        return block

    def get_data(self, source):
        """
        Given a "source identifier", return a buffer containing data.

        Parameters
        ----------
        source : any
            If an integer, refers to the index of an internal block.
            If a string, is a uri to an external block.

        Return
        ------
        buffer : buffer
        """
        block = self.get_block(source)

        data = block.data
        self._data_to_block_mapping[id(data)] = block

        return data.data

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
        block : Block
        """
        base = util.get_array_base(arr)
        block = self._data_to_block_mapping.get(id(base))
        if block is not None:
            return block
        block = Block(base)
        self.add(block)
        return block

    def __getitem__(self, arr):
        return self.find_or_create_block_for_array(arr)


class Block(versioning.VersionedMixin):
    """
    Represents a single block in a FINF file.  This is an
    implementation detail and should not be instantiated directly.
    Instead, should only be created through the `BlockManager`.
    """

    _header_fmt = b'>BBBQQQ16s'
    _header_fmt_size = struct.calcsize(_header_fmt)

    def __init__(self, data=None, uri=None):
        if data is not None:
            self._data = data
            if six.PY2:
                self._size = len(data.data)
            elif six.PY3:
                self._size = data.data.nbytes
        else:
            self._data = None
            self._size = None
        self._external = uri is not None
        self._uri = uri

        self._fd = None
        self._header_size = None
        self._offset = None
        self._data_offset = None
        self._allocated = None
        self._encoding = None
        self._memmapped = False
        self._index = None

    def __repr__(self):
        return '<Block alloc: {0} size: {1} encoding: {2}>'.format(
            self._allocated, self._size, self._encoding)

    @property
    def external(self):
        return self._external

    @property
    def source(self):
        if self._external:
            return "{0}.bff".format(self._index)
        else:
            return self._index

    def read(self, fd):
        """
        Read a Block from the given Python file-like object.  The file
        position should be at the beginning of the block header (at
        the block magic token).

        If the file is seekable, the reading or memmapping of the
        actual data is postponed until an array requests it.  If the
        file is a stream, we have to read it right now.
        """
        fd = generic_io.get_file(fd)

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
        if header_size < self._header_fmt_size:
            raise ValueError(
                "Header size must be > {0}".format(self._header_fmt_size))

        buff = fd.read(header_size)
        (major, minor, micro, allocated_size, used_size, checksum, encoding) = \
            struct.unpack_from(self._header_fmt, buff[:self._header_fmt_size])

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
            fd.close()

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
        if self.external:
            fd = generic_io.resolve_uri(fd.uri, self.source)

        with generic_io.get_file(fd, 'w') as fd:
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
        The data for the block, as a numpy array.
        """
        if self._data is None:
            if self._uri is not None:
                self.read(self._uri)
            elif self._fd is None:
                raise ValueError(
                    "Can not load data because source tree has no URI.")

            if self._fd is not None:
                if self._fd.is_closed():
                    raise IOError(
                        "FINF file has already been closed. "
                        "Can not get the data.")

                if self._fd.can_memmap():
                    self._data = self._fd.memmap_array(
                        self._data_offset, self._size)
                    self._memmapped = True

                else:
                    # Be nice and don't move around the file position.
                    curpos = self._fd.tell()
                    try:
                        self._fd.seek(self._data_offset)
                        self._data = self._fd.read_into_array(self._size)
                    finally:
                        self._fd.seek(curpos)

        return self._data
