# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import copy
import os
import struct
import weakref

from astropy.extern import six
from astropy.extern.six.moves.urllib import parse as urlparse

from . import constants
from . import generic_io
from . import util


class BlockManager(object):
    """
    Manages the `Block`s associated with a FINF file.
    """
    def __init__(self, finffile):
        self._finffile = weakref.ref(finffile)

        self._blocks = []
        self._data_to_block_mapping = {}

    def __len__(self):
        """
        Return the total number of blocks being managed.
        """
        return len(self._blocks)

    @property
    def blocks(self):
        for block in self._blocks:
            yield block

    @property
    def internal_blocks(self):
        for block in self._blocks:
            if block.block_type == 'internal':
                yield block

        for block in self._blocks:
            if block.block_type == 'streamed':
                yield block
                break

    @property
    def streamed_block(self):
        for block in self._blocks:
            if block.block_type == 'streamed':
                return block

    @property
    def external_blocks(self):
        for block in self._blocks:
            if block.block_type == 'external':
                yield block

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

        for block in self.internal_blocks:
            block.write(fd)

        for i, block in enumerate(self.external_blocks):
            if fd.uri is None:
                raise ValueError(
                    "Can't write external blocks, since URI of main file is "
                    "unknown.")
            subfd = self.get_external_uri(fd.uri, i)
            finffile = finf.FinfFile()
            block = copy.copy(block)
            block.block_type = 'internal'
            finffile.blocks.add(block)
            finffile.write_to(subfd)

    def get_external_filename(self, filename, index):
        """
        Given a main filename and an index number, return a new file
        name for referencing an external block.
        """
        filename = os.path.splitext(filename)[0]
        return filename + '{0:04d}.finf'.format(index)

    def get_external_uri(self, uri, index):
        """
        Given a main URI and an index number, return a new URI for
        saving an external block.
        """
        if uri is None:
            uri = ''
        parts = list(urlparse.urlparse(uri))
        path = parts[2]
        dirname, filename = os.path.split(path)
        filename = self.get_external_filename(filename, index)
        path = os.path.join(dirname, filename)
        parts[2] = path
        return urlparse.urlunparse(parts)

    def add(self, block):
        """
        Add an internal block to the manager.
        """
        self._blocks.append(block)
        if block._data is not None:
            self._data_to_block_mapping[id(block._data)] = block

    def finalize(self, ctx):
        """
        At this point, we have a complete set of blocks for the file,
        with no extras.

        Here, they are reindexed, and possibly reorganized.
        """
        # TODO: Should this reset the state (what's external and what
        # isn't) afterword?

        if ctx.get('exploded'):
            for block in self.internal_blocks:
                block.block_type = 'external'

        count = 0
        for block in self._blocks:
            if block.block_type == 'streamed':
                count += 1
        if count > 1:
            raise ValueError(
                "Found {0} streamed blocks, but there must be only one.".format(count))

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
            block = util.nth_item(self.internal_blocks, source)
            if block is None:
                raise ValueError("Block '{0}' not found.".format(source))

        elif isinstance(source, six.string_types):
            finffile = self._finffile().read_external(source)
            block = finffile.blocks._blocks[0]
            block.block_type = 'external'
            if block not in self._blocks:
                self._blocks.append(block)

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
        for i, internal_block in enumerate(self.internal_blocks):
            if block == internal_block:
                if internal_block.block_type == 'streamed':
                    return -1
                return i

        for i, external_block in enumerate(self.external_blocks):
            if block == external_block:
                if self._finffile().uri is None:
                    raise ValueError(
                        "Can't write external blocks, since URI of main file is "
                        "unknown.")

                parts = list(urlparse.urlparse(self._finffile().uri))
                path = parts[2]
                filename = os.path.basename(path)
                return self.get_external_filename(filename, i)

        raise ValueError("block not found.")

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
        from .tags.core import ndarray
        if isinstance(arr, ndarray.NDArrayType):
            if arr._block is not None:
                if arr._block not in self._blocks:
                    self._blocks.append(arr._block)
                return arr._block

        base = util.get_array_base(arr)
        block = self._data_to_block_mapping.get(id(base))
        if block is not None:
            return block
        block = Block(base)
        self.add(block)
        return block

    def get_streamed_block(self):
        """
        Get the streamed block, which is always the last one.  A
        streamed block, on writing, does not manage data of its own,
        but the user is expected to stream it to disk directly.
        """
        block = self.streamed_block
        if block is None:
            block = Block(block_type='streamed')
            self._blocks.append(block)
        return block

    def add_inline(self, array):
        """
        Add an inline block for ``array`` to the block set.
        """
        block = Block(array, block_type='inline')
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

    _header_fmt = b'>IQQQ16s'
    _header_fmt_size = struct.calcsize(_header_fmt)

    def __init__(self, data=None, uri=None, block_type='internal'):
        if data is not None:
            self._data = data
            if six.PY2:
                self._size = len(data.data)
            elif six.PY3:
                self._size = data.data.nbytes
        else:
            self._data = None
            self._size = 0
        self._uri = uri
        self._block_type = block_type

        self._fd = None
        self._header_size = None
        self._offset = None
        self._data_offset = None
        self._allocated = 0
        self._encoding = None
        self._memmapped = False

    def __repr__(self):
        return '<Block {0} alloc: {1} size: {2} encoding: {3}>'.format(
            self._block_type[:3], self._allocated, self._size, self._encoding)

    def __len__(self):
        return self._size

    @property
    def block_type(self):
        return self._block_type

    @block_type.setter
    def block_type(self, typename):
        if typename not in ['internal', 'external', 'streamed', 'inline']:
            raise ValueError(
                "block_type must be one of 'internal', 'external', 'streamed' or 'inline'")
        self._block_type = typename

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
            if len(buff) < 4:
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
        (flags, allocated_size, used_size, checksum, encoding) = \
            struct.unpack_from(self._header_fmt, buff[:self._header_fmt_size])

        # Support streaming blocks
        if fd.seekable():
            # If the file is seekable, we can delay reading the actual
            # data until later.
            self._fd = fd
            self._header_size = header_size
            self._offset = offset
            self._data_offset = fd.tell()
            self._encoding = encoding
            if flags & constants.BLOCK_FLAG_STREAMED:
                fd.fast_forward(-1)
                self._block_type = 'streamed'
                self._size = self._allocated = (fd.tell() - self._data_offset) + 1
            else:
                fd.fast_forward(allocated_size)
                self._allocated = allocated_size
                self._size = used_size
        else:
            # If the file is a stream, we need to get the data now.
            if flags & constants.BLOCK_FLAG_STREAMED:
                self._block_type = 'streamed'
                self._data = fd.read_into_array(-1)
                self._size = self._allocated = len(self._data)
            else:
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

            flags = 0
            if self._block_type == 'streamed':
                flags |= constants.BLOCK_FLAG_STREAMED

            fd.write(constants.BLOCK_MAGIC)
            fd.write(struct.pack(b'>H', self._header_size))
            fd.write(struct.pack(
                self._header_fmt, flags,
                self._allocated, self._size, 0, b''))

            self._data_offset = fd.tell()

            if self._data is not None:
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
