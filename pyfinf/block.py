# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import struct
import weakref

from astropy.extern import six

from . import constants
from . import generic_io
from . import util


class BlockManager(object):
    """
    Manages the `Block`s associated with a FINF file.
    """
    def __init__(self, finffile):
        self._finffile = weakref.ref(finffile)

        self._internal_blocks = []
        self._external_blocks = []
        self._data_to_block_mapping = {}

    def read_internal_blocks(self, fd, past_magic=False):
        """
        Read all internal blocks present in the file.

        Parameters
        ----------
        fd : GenericFile
            The file to read from.

        past_magic: bool, optional
            If `True`, the file position is immediately after the
            block magic token.  If `False` (default), the file
            position is exactly at the beginning of the block magic
            token.
        """
        while True:
            block = Block().read(fd, past_magic=past_magic)
            if block is not None:
                self.add(block)
            else:
                break
            past_magic = False

    def write_blocks(self, fd):
        """
        Write all blocks to disk.

        Parameters
        ----------
        fd : generic_io.GenericFile
            The file to write internal blocks to.  The file position
            should be after the tree.
        """
        from . import finf

        for block in self._internal_blocks:
            block.write(fd)

        for i, block in enumerate(self._external_blocks):
            subfd = generic_io.resolve_uri(fd.uri, '{0}.finf'.format(i))
            finffile = finf.FinfFile()
            finffile.blocks._internal_blocks.append(block)
            finffile.write_to(subfd)

    def add(self, block):
        """
        Add an internal block to the manager.
        """
        self._internal_blocks.append(block)
        if block._data is not None:
            self._data_to_block_mapping[id(block._data)] = block

    def __len__(self):
        return len(self._internal_blocks) + len(self._external_blocks)

    def finalize(self, ctx):
        """
        At this point, we have a complete set of blocks for the file,
        with no extras.

        Here, they are reindexed, and possibly reorganized.
        """
        # TODO: Should this reset the state (what's external and what
        # isn't) afterword?

        if ctx.get('exploded'):
            self._external_blocks += self._internal_blocks
            self._internal_blocks = []

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
            finffile = self._finffile().read_external(source)
            block = finffile.blocks._internal_blocks[0]
            if block not in self._external_blocks:
                self._external_blocks.append(block)
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

    def get_source(self, block):
        """
        Get a source identifier for a given block.

        Parameters
        ----------
        block : Block

        Returns
        -------
        source_id : str
            May be an integer for an internal block, or a URI for an
            external block.
        """
        try:
            index = self._internal_blocks.index(block)
        except ValueError:
            pass
        else:
            return index

        try:
            index = self._external_blocks.index(block)
        except ValueError:
            raise ValueError("Block not associated with FinfFile.")
        else:
            return '{0}.finf'.format(index)

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


class Block(object):
    """
    Represents a single block in a FINF file.  This is an
    implementation detail and should not be instantiated directly.
    Instead, should only be created through the `BlockManager`.
    """

    _header_fmt = b'>QQQ16s'
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
        self._uri = uri

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

    def read(self, fd, past_magic=False):
        """
        Read a Block from the given Python file-like object.

        If the file is seekable, the reading or memmapping of the
        actual data is postponed until an array requests it.  If the
        file is a stream, the data will be read into memory
        immediately.

        Parameters
        ----------
        fd : GenericFile

        past_magic: bool, optional
            If `True`, the file position is immediately after the
            block magic token.  If `False` (default), the file
            position is exactly at the beginning of the block magic
            token.
        """
        fd = generic_io.get_file(fd)

        if fd.seekable():
            offset = fd.tell()

        if not past_magic:
            buff = fd.read(len(constants.BLOCK_MAGIC))
            if len(buff) == 0:
                return None

            if buff != constants.BLOCK_MAGIC:
                raise ValueError(
                    "Bad magic number in block. "
                    "This may indicate an internal inconsistency about the "
                    "sizes of the blocks in the file.")

        buff = fd.read(2)
        header_size, = struct.unpack('>H', buff)
        if header_size < self._header_fmt_size:
            raise ValueError(
                "Header size must be > {0}".format(self._header_fmt_size))

        buff = fd.read(header_size)
        (allocated_size, used_size, checksum, encoding) = \
            struct.unpack_from(self._header_fmt, buff[:self._header_fmt_size])

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
        Write an internal block to the given Python file-like object.
        """
        with generic_io.get_file(fd, 'w') as fd:
            self._allocated = self._size
            self._offset = fd.tell()
            self._header_size = self._header_fmt_size

            fd.write(constants.BLOCK_MAGIC)
            fd.write(struct.pack(b'>H', self._header_size))
            fd.write(struct.pack(
                self._header_fmt,
                self._allocated, self._size, 0, b''))

            self._data_offset = fd.tell()

            fd.write(self._data.data)

    @property
    def data(self):
        """
        Get the data for the block, as a numpy array.
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
                # Be nice and don't move around the file position.
                curpos = self._fd.tell()
                try:
                    self._fd.seek(self._data_offset)
                    self._data = self._fd.read_into_array(self._size)
                finally:
                    self._fd.seek(curpos)

        return self._data
