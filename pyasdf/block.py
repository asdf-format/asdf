# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from collections import namedtuple
import copy
import os
import struct
import weakref

import numpy as np

from astropy.extern import six
from astropy.extern.six.moves.urllib import parse as urlparse

from . import constants
from . import generic_io
from . import stream
from . import treeutil
from . import util


class BlockManager(object):
    """
    Manages the `Block`s associated with a ASDF file.
    """
    def __init__(self, asdffile):
        self._asdffile = weakref.ref(asdffile)

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
            if block.array_storage == 'internal':
                yield block

        for block in self._blocks:
            if block.array_storage == 'streamed':
                yield block
                break

    @property
    def streamed_block(self):
        for block in self._blocks:
            if block.array_storage == 'streamed':
                return block

    @property
    def external_blocks(self):
        for block in self._blocks:
            if block.array_storage == 'external':
                yield block

    def has_blocks_with_offset(self):
        """
        Returns `True` if any of the internal blocks currently have an
        offset assigned.
        """
        for block in self.internal_blocks:
            if block.offset is not None:
                return True
        return False

    def _sort_blocks_by_offset(self):
        def sorter(x):
            if x.offset is None:
                # 64 bits
                return 0xffffffffffffffff
            else:
                return x.offset
        self._blocks.sort(key=sorter)

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

    def write_internal_blocks_serial(self, fd, pad_blocks=False):
        """
        Write all blocks to disk serially.

        Parameters
        ----------
        fd : generic_io.GenericFile
            The file to write internal blocks to.  The file position
            should be after the tree.
        """
        for block in self.internal_blocks:
            padding = util.calculate_padding(
                block.size, pad_blocks, fd.block_size)
            block.allocated = block._size + padding
            block.offset = fd.tell()
            block.write(fd)
            fd.fast_forward(padding)

    def write_internal_blocks_random_access(self, fd):
        """
        Write all blocks to disk at their specified offsets.  All
        internal blocks must have an offset assigned at this point.

        Parameters
        ----------
        fd : generic_io.GenericFile
            The file to write internal blocks to.  The file position
            should be after the tree.
        """
        self._sort_blocks_by_offset()

        iter = self.internal_blocks
        last_block = next(iter)
        # We need to explicitly clear anything between the tree
        # and the first block, otherwise there may be other block
        # markers left over which will throw off block indexing.
        # We don't need to do this between each block.
        fd.clear(last_block.offset - fd.tell())

        for block in iter:
            last_block.allocated = ((block.offset - last_block.offset) -
                                    last_block.header_size)
            fd.seek(last_block.offset)
            last_block.write(fd)
            last_block = block

        # The last block must be "allocated" all the way to the
        # end of the file, which isn't truncated when updating.
        fd.seek(0, 2)
        last_end = fd.tell()
        last_block.allocated = max(
            last_end - last_block.offset,
            last_block.size) - last_block.header_size
        fd.seek(last_block.offset)
        last_block.write(fd)

    def write_external_blocks(self, uri, pad_blocks=False):
        """
        Write all blocks to disk serially.

        Parameters
        ----------
        uri : str
            The base uri of the external blocks
        """
        from . import asdf

        for i, block in enumerate(self.external_blocks):
            if uri is None:
                raise ValueError(
                    "Can't write external blocks, since URI of main file is "
                    "unknown.")
            subfd = self.get_external_uri(uri, i)
            with asdf.AsdfFile() as asdffile:
                block = copy.copy(block)
                block.array_storage = 'internal'
                asdffile.blocks.add(block)
                block._used = True
                asdffile.write_to(subfd, pad_blocks=pad_blocks)

    def get_external_filename(self, filename, index):
        """
        Given a main filename and an index number, return a new file
        name for referencing an external block.
        """
        filename = os.path.splitext(filename)[0]
        return filename + '{0:04d}.asdf'.format(index)

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

    def remove(self, block):
        """
        Remove a block from the manager.
        """
        self._blocks.remove(block)
        if block._data is not None:
            del self._data_to_block_mapping[id(block._data)]

    def _find_used_blocks(self, tree, auto_inline):
        from .tags.core import ndarray

        if auto_inline is None:
            auto_inline = 0

        block_to_array_mapping = {}

        def visit_array(node):
            block = None
            if isinstance(node, np.ndarray):
                block = self.find_or_create_block_for_array(node)
            elif (isinstance(node, ndarray.NDArrayType) and
                not isinstance(node, stream.Stream)):
                block = node.block
            if block is not None:
                block_to_array_mapping.setdefault(block, [])
                block_to_array_mapping[block].append(node)

        treeutil.walk(tree, visit_array)

        for block in self._blocks[:]:
            arrays = block_to_array_mapping.get(block, [])
            if getattr(block, '_used', 0) == 0 and len(arrays) == 0:
                self.remove(block)
            elif len(arrays) == 1:
                if np.product(block.data.shape) < auto_inline:
                    block.array_storage = 'inline'

    def finalize(self, ctx, all_array_storage, auto_inline=None):
        """
        At this point, we have a complete set of blocks for the file,
        with no extras.

        Here, they are reindexed, and possibly reorganized.
        """
        # TODO: Should this reset the state (what's external and what
        # isn't) afterword?

        self._find_used_blocks(ctx.tree, auto_inline)

        if all_array_storage is not None:
            for block in self.blocks:
                block.array_storage = all_array_storage

        count = 0
        for block in self._blocks:
            if block.array_storage == 'streamed':
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

        Returns
        -------
        buffer : buffer
        """
        if isinstance(source, int):
            block = util.nth_item(self.internal_blocks, source)
            if block is None:
                raise ValueError("Block '{0}' not found.".format(source))

        elif isinstance(source, six.string_types):
            asdffile = self._asdffile().read_external(source)
            block = asdffile.blocks._blocks[0]
            block.array_storage = 'external'
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

        Returns
        -------
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
                if internal_block.array_storage == 'streamed':
                    return -1
                return i

        for i, external_block in enumerate(self.external_blocks):
            if block == external_block:
                if self._asdffile().uri is None:
                    raise ValueError(
                        "Can't write external blocks, since URI of main file is "
                        "unknown.")

                parts = list(urlparse.urlparse(self._asdffile().uri))
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
        if (isinstance(arr, ndarray.NDArrayType) and
            arr._block is not None):
            if arr._block in self._blocks:
                return arr._block
            else:
                arr._block = None

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
            block = Block(array_storage='streamed')
            self._blocks.append(block)
        return block

    def add_inline(self, array):
        """
        Add an inline block for ``array`` to the block set.
        """
        block = Block(array, array_storage='inline')
        self.add(block)
        return block

    def __getitem__(self, arr):
        return self.find_or_create_block_for_array(arr)


class Block(object):
    """
    Represents a single block in a ASDF file.  This is an
    implementation detail and should not be instantiated directly.
    Instead, should only be created through the `BlockManager`.
    """

    _header = util.BinaryStruct([
        ('flags', 'I'),
        ('allocated_size', 'Q'),
        ('used_size', 'Q'),
        ('checksum', 'Q'),
        ('encoding', '16s'),
    ])

    def __init__(self, data=None, uri=None, array_storage='internal'):
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
        self._array_storage = array_storage

        self._fd = None
        self._offset = None
        self._allocated = self._size
        self._encoding = None
        self._memmapped = False

    def __repr__(self):
        return '<Block {0} alloc: {1} size: {2} type: {3}>'.format(
            self._array_storage[:3], self._allocated, self._size, self._array_storage)

    def __len__(self):
        return self._size

    @property
    def offset(self):
        return self._offset
    @offset.setter
    def offset(self, offset):
        self._offset = offset

    @property
    def allocated(self):
        return self._allocated
    @allocated.setter
    def allocated(self, allocated):
        self._allocated = allocated

    @property
    def header_size(self):
        return self._header.size + constants.BLOCK_HEADER_BOILERPLATE_SIZE

    @property
    def data_offset(self):
        return self._offset + self.header_size

    @property
    def size(self):
        return self._size + self.header_size

    @property
    def array_storage(self):
        return self._array_storage

    @array_storage.setter
    def array_storage(self, typename):
        if typename not in ['internal', 'external', 'streamed', 'inline']:
            raise ValueError(
                "array_storage must be one of 'internal', 'external', "
                "'streamed' or 'inline'")
        self._array_storage = typename

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

        offset = None
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
        elif offset is not None:
            offset -= 4

        buff = fd.read(2)
        header_size, = struct.unpack(b'>H', buff)
        if header_size < self._header.size:
            raise ValueError(
                "Header size must be >= {0}".format(self._header.size))

        buff = fd.read(header_size)
        header = self._header.unpack(buff)

        # This is used by the documentation system, but nowhere else.
        self._flags = header['flags']

        if fd.seekable():
            # If the file is seekable, we can delay reading the actual
            # data until later.
            self._fd = fd
            self._header_size = header_size
            self._offset = offset
            if header['flags'] & constants.BLOCK_FLAG_STREAMED:
                # Support streaming blocks
                fd.fast_forward(-1)
                self._array_storage = 'streamed'
                self._size = self._allocated = (fd.tell() - self.data_offset) + 1
            else:
                fd.fast_forward(header['allocated_size'])
                self._allocated = header['allocated_size']
                self._size = header['used_size']
        else:
            # If the file is a stream, we need to get the data now.
            if header['flags'] & constants.BLOCK_FLAG_STREAMED:
                # Support streaming blocks
                self._array_storage = 'streamed'
                self._data = fd.read_into_array(-1)
                self._size = self._allocated = len(self._data)
            else:
                self._size = header['used_size']
                self._allocated = header['allocated_size']
                self._data = fd.read_into_array(self._size)
                fd.fast_forward(self._allocated - self._size)
            fd.close()

        return self

    def write(self, fd):
        """
        Write an internal block to the given Python file-like object.
        """
        with generic_io.get_file(fd, 'w') as fd:
            self._header_size = self._header.size

            flags = 0
            if self._array_storage == 'streamed':
                flags |= constants.BLOCK_FLAG_STREAMED

            fd.write(constants.BLOCK_MAGIC)
            fd.write(struct.pack(b'>H', self._header_size))
            fd.write(self._header.pack(
                flags=flags, allocated_size=self.allocated,
                used_size=self._size, checksum=0, encoding=b''))

            if self._data is not None:
                fd.write_array(self._data)

    @property
    def data(self):
        """
        Get the data for the block, as a numpy array.
        """
        if self._data is None:
            if self._fd.is_closed():
                raise IOError(
                    "ASDF file has already been closed. "
                    "Can not get the data.")

            if self._fd.can_memmap():
                self._data = self._fd.memmap_array(
                    self.data_offset, self._size)
                self._memmapped = True

            else:
                # Be nice and reset the file position after we're done
                curpos = self._fd.tell()
                try:
                    self._fd.seek(self.data_offset)
                    self._data = self._fd.read_into_array(self._size)
                finally:
                    self._fd.seek(curpos)

        return self._data


def calculate_updated_layout(blocks, tree_size, pad_blocks, block_size):
    """
    Calculates a block layout that will try to use as many blocks as
    possible in their original locations, though at this point the
    algorithm is fairly naive.  The result will be stored in the
    offsets of the blocks.

    Parameters
    ----------
    blocks : Blocks instance

    tree_size : int
        The amount of space to reserve for the tree at the beginning.

    Returns
    -------
    Returns `False` if no good layout can be found and one is best off
    rewriting the file serially, otherwise, returns `True`.
    """
    def unfix_block(i):
        # We can't really move memory-mapped blocks around, so at this
        # point, we just return False.  If this algorithm gets more
        # sophisticated we could carefully move memmapped blocks
        # around without clobbering other ones.
        return False

    def fix_block(block, offset):
        block.offset = offset
        fixed.append(Entry(block.offset, block.offset + block.size, block))
        fixed.sort()

    Entry = namedtuple("Entry", ['start', 'end', 'block'])

    fixed = []
    free = []
    for block in blocks._blocks:
        if block.array_storage == 'internal':
            if block.offset is not None:
                fixed.append(
                    Entry(block.offset, block.offset + block.size, block))
            else:
                free.append(block)

    if not len(fixed):
        return False

    fixed.sort()

    # Make enough room at the beginning for the tree, by popping off
    # blocks at the beginning
    while len(fixed) and fixed[0].start < tree_size:
        if not unfix_block(0):
            return False

    if not len(fixed):
        return False

    # This algorithm is pretty basic at this point -- it just looks
    # for the first open spot big enough for the free block to fit.
    while len(free):
        block = free.pop()
        last_end = tree_size
        for entry in fixed:
            if entry.start - last_end >= block.size:
                fix_block(block, last_end)
                break
            last_end = entry.end
        else:
            padding = util.calculate_padding(
                entry.block.size, pad_blocks, block_size)
            fix_block(block, last_end + padding)

    if blocks.streamed_block is not None:
        padding = util.calculate_padding(
            fixed[-1].block.size, pad_blocks, block_size)
        blocks.streamed_block.offset = fixed[-1].end + padding

    blocks._sort_blocks_by_offset()

    return True
