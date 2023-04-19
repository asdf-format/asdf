import copy
import os
import re
import weakref

import numpy as np
import yaml

from asdf import compression as mcompression
from asdf import constants, generic_io, treeutil, util, yamlutil
from asdf.config import get_config
from asdf.util import patched_urllib_parse

from .block import Block, UnloadedBlock


class BlockManager:
    """
    Manages the `Block`s associated with a ASDF file.
    """

    def __init__(self, asdffile, copy_arrays=False, lazy_load=True):
        self._asdffile = weakref.ref(asdffile)

        self._internal_blocks = []
        self._external_blocks = []
        self._inline_blocks = []
        self._streamed_blocks = []

        self._block_type_mapping = {
            "internal": self._internal_blocks,
            "external": self._external_blocks,
            "inline": self._inline_blocks,
            "streamed": self._streamed_blocks,
        }

        self._data_to_block_mapping = {}
        self._validate_checksums = False
        self._memmap = not copy_arrays
        self._lazy_load = lazy_load
        self._internal_blocks_mapped = False

    def __len__(self):
        """
        Return the total number of blocks being managed.

        This may not include all of the blocks in an open file, since
        their reading may have been deferred.  Call
        `finish_reading_internal_blocks` to find the positions and
        header information of all blocks in the file.
        """
        return sum(len(x) for x in self._block_type_mapping.values())

    def add(self, block, key=None):
        """
        Add an internal block to the manager.
        """
        if not self._internal_blocks_mapped:
            # If the block index is missing we need to locate the remaining
            # blocks so that we don't accidentally add our new block
            # in the middle of the list.
            self.finish_reading_internal_blocks()

        self._add(block, key=key)

    def _add(self, block, key=None):
        block_set = self._block_type_mapping.get(block.array_storage, None)
        if block_set is not None:
            if block not in block_set:
                block_set.append(block)
        else:
            msg = f"Unknown array storage type {block.array_storage}"
            raise ValueError(msg)

        if block.array_storage == "streamed" and len(self._streamed_blocks) > 1:
            msg = "Can not add second streaming block"
            raise ValueError(msg)

        if block._data is not None or key is not None:
            if key is None:
                key = id(util.get_array_base(block._data))
            self._data_to_block_mapping[key] = block

    def remove(self, block):
        """
        Remove a block from the manager.
        """
        block_set = self._block_type_mapping.get(block.array_storage, None)
        if block_set is not None:
            if block in block_set:
                block_set.remove(block)
                for key, blk in list(self._data_to_block_mapping.items()):
                    if blk is block:
                        del self._data_to_block_mapping[key]
        else:
            msg = f"Unknown array storage type {block.array_storage}"
            raise ValueError(msg)

    def set_array_storage(self, block, array_storage):
        """
        Set the array storage type of the given block.

        Parameters
        ----------
        block : Block instance

        array_storage : str
            Must be one of:

            - ``internal``: The default.  The array data will be
              stored in a binary block in the same ASDF file.

            - ``external``: Store the data in a binary block in a
              separate ASDF file.

            - ``inline``: Store the data as YAML inline in the tree.

            - ``streamed``: The special streamed inline block that
              appears at the end of the file.
        """
        if array_storage not in ["internal", "external", "streamed", "inline"]:
            msg = "array_storage must be one of 'internal', 'external', 'streamed' or 'inline'"
            raise ValueError(msg)

        if block.array_storage != array_storage:
            if block in self.blocks:
                self.remove(block)
            block._array_storage = array_storage
            self.add(block)
            if array_storage == "streamed":
                block.output_compression = None
                block.output_compression_kwargs = None

    @property
    def blocks(self):
        """
        An iterator over all blocks being managed.

        This may not include all of the blocks in an open file,
        since their reading may have been deferred.  Call
        `finish_reading_internal_blocks` to find the positions and
        header information of all blocks in the file.
        """
        for block_set in self._block_type_mapping.values():
            yield from block_set

    @property
    def internal_blocks(self):
        """
        An iterator over all internal blocks being managed.

        This may not include all of the blocks in an open file,
        since their reading may have been deferred.  Call
        `finish_reading_internal_blocks` to find the positions and
        header information of all blocks in the file.
        """
        for block_set in (self._internal_blocks, self._streamed_blocks):
            yield from block_set

    @property
    def streamed_block(self):
        """
        The streamed block (always the last internal block in a file),
        or `None` if a streamed block is not present.
        """
        self.finish_reading_internal_blocks()

        if len(self._streamed_blocks):
            return self._streamed_blocks[0]

        return None

    @property
    def external_blocks(self):
        """
        An iterator over all external blocks being managed.
        """
        yield from self._external_blocks

    @property
    def inline_blocks(self):
        """
        An iterator over all inline blocks being managed.
        """
        yield from self._inline_blocks

    @property
    def memmap(self):
        """
        The flag which indicates whether the arrays are memory mapped
        to the underlying file.
        """
        return self._memmap

    @property
    def lazy_load(self):
        """
        The flag which indicates whether the blocks are lazily read.
        """
        return self._lazy_load

    def has_blocks_with_offset(self):
        """
        Returns `True` if any of the internal blocks currently have an
        offset assigned.
        """
        return any(block.offset is not None for block in self.internal_blocks)

    def _new_block(self):
        return Block(memmap=self.memmap, lazy_load=self.lazy_load)

    def _sort_blocks_by_offset(self):
        def sorter(x):
            if x.offset is None:
                msg = "Block is missing offset"
                raise ValueError(msg)

            return x.offset

        self._internal_blocks.sort(key=sorter)

    def _read_next_internal_block(self, fd, past_magic=False):
        # This assumes the file pointer is at the beginning of the
        # block, (or beginning + 4 if past_magic is True)
        block = self._new_block().read(fd, past_magic=past_magic, validate_checksum=self._validate_checksums)
        if block is not None:
            self._add(block)

        return block

    def read_internal_blocks(self, fd, past_magic=False, validate_checksums=False):
        """
        Read internal blocks present in the file.  If the file is
        seekable, only the first block will be read, and the reading
        of all others will be lazily deferred until an the loading of
        an array requests it.

        Parameters
        ----------
        fd : GenericFile
            The file to read from.

        past_magic : bool, optional
            If `True`, the file position is immediately after the
            block magic token.  If `False` (default), the file
            position is exactly at the beginning of the block magic
            token.

        validate_checksums : bool, optional
            If `True`, validate the blocks against their checksums.

        """
        self._validate_checksums = validate_checksums

        while True:
            block = self._read_next_internal_block(fd, past_magic=past_magic)
            if block is None:
                break
            past_magic = False

            # If the file handle is seekable, we only read the first
            # block and defer reading the rest until later.
            if fd.seekable():
                break

    def finish_reading_internal_blocks(self):
        """
        Read all remaining internal blocks present in the file, if any.
        This is called before updating a file, since updating requires
        knowledge of all internal blocks in the file.
        """
        if not self._internal_blocks:
            return
        for block in self._internal_blocks:
            if isinstance(block, UnloadedBlock):
                block.load()

        last_block = self._internal_blocks[-1]

        # Read all of the remaining blocks in the file, if any
        if last_block._fd is not None and last_block._fd.seekable():
            last_block._fd.seek(last_block.end_offset)
            while True:
                last_block = self._read_next_internal_block(last_block._fd, False)
                if last_block is None:
                    break

        self._internal_blocks_mapped = True

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
            if block.output_compression:
                block.offset = fd.tell()
                block.write(fd)
            else:
                if block.input_compression:
                    block.update_size()
                padding = util.calculate_padding(block.size, pad_blocks, fd.block_size)
                block.allocated = block._size + padding
                block.offset = fd.tell()
                block.write(fd)
                fd.fast_forward(block.allocated - block._size)

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

        iter_ = self.internal_blocks
        last_block = next(iter_)
        # We need to explicitly clear anything between the tree
        # and the first block, otherwise there may be other block
        # markers left over which will throw off block indexing.
        # We don't need to do this between each block.
        fd.clear(last_block.offset - fd.tell())

        for block in iter_:
            last_block.allocated = (block.offset - last_block.offset) - last_block.header_size
            fd.seek(last_block.offset)
            last_block.write(fd)
            last_block = block

        last_block.allocated = last_block.size
        fd.seek(last_block.offset)
        last_block.write(fd)

        fd.truncate(last_block.end_offset)

    def write_external_blocks(self, uri, pad_blocks=False):
        """
        Write all blocks to disk serially.

        Parameters
        ----------
        uri : str
            The base uri of the external blocks
        """

        import asdf

        for i, block in enumerate(self.external_blocks):
            if uri is None:
                msg = "Can't write external blocks, since URI of main file is unknown."
                raise ValueError(msg)
            subfd = self.get_external_uri(uri, i)
            asdffile = asdf.AsdfFile()
            blk = copy.copy(block)
            blk._array_storage = "internal"
            asdffile._blocks.add(blk)
            blk._used = True
            # skip the new block manager here
            asdffile._write_to(subfd, pad_blocks=pad_blocks, all_array_storage="internal")

    def write_block_index(self, fd, ctx):
        """
        Write the block index.

        Parameters
        ----------
        fd : GenericFile
            The file to write to.  The file pointer should be at the
            end of the file.
        """
        if len(self._internal_blocks) and not len(self._streamed_blocks):
            fd.write(constants.INDEX_HEADER)
            fd.write(b"\n")
            offsets = [x.offset for x in self.internal_blocks]

            yaml_version = tuple(int(x) for x in ctx.version_map["YAML_VERSION"].split("."))

            yaml.dump(
                offsets,
                Dumper=yamlutil._yaml_base_dumper,
                stream=fd,
                explicit_start=True,
                explicit_end=True,
                version=yaml_version,
                allow_unicode=True,
                encoding="utf-8",
            )

    _re_index_content = re.compile(rb"^" + constants.INDEX_HEADER + rb"\r?\n%YAML.*\.\.\.\r?\n?$")
    _re_index_misc = re.compile(rb"^[\n\r\x20-\x7f]+$")

    def read_block_index(self, fd, ctx):
        """
        Read the block index.

        Parameters
        ----------
        fd : GenericFile
            The file to read from.  It must be seekable.
        """
        # This reads the block index by reading backward from the end
        # of the file.  This tries to be as conservative as possible,
        # since not reading an index isn't a deal breaker --
        # everything can still be read from the file, only slower.
        # Importantly, it must remain "transactionally clean", and not
        # create any blocks until we're sure the block index makes
        # sense.

        if not fd.seekable():
            return

        if not len(self._internal_blocks):
            return

        first_block = self._internal_blocks[0]
        first_block_end = first_block.end_offset

        fd.seek(0, generic_io.SEEK_END)
        file_size = block_end = fd.tell()
        # We want to read on filesystem block boundaries.  We use
        # "block_end - 5" here because we need to read at least 5
        # bytes in the first block.
        block_start = ((block_end - 5) // fd.block_size) * fd.block_size
        buff_size = block_end - block_start

        content = b""

        fd.seek(block_start, generic_io.SEEK_SET)
        buff = fd.read(buff_size)

        # Extra '\0' bytes are allowed after the ..., mainly to
        # workaround poor truncation support on Windows
        buff = buff.rstrip(b"\0")
        content = buff

        # We need an explicit YAML end marker, or there's no
        # block index
        for ending in (b"...", b"...\r\n", b"...\n"):
            if content.endswith(ending):
                break
        else:
            return

        # Read blocks in reverse order from the end of the file
        while True:
            # Look for the index header
            idx = content.rfind(constants.INDEX_HEADER)
            if idx != -1:
                content = content[idx:]
                index_start = block_start + idx
                break

            # If the rest of it starts to look like binary
            # values, bail...
            if not self._re_index_misc.match(buff):
                return

            if block_start <= first_block_end:
                return

            block_end = block_start
            block_start = max(block_end - fd.block_size, first_block_end)

            fd.seek(block_start, generic_io.SEEK_SET)
            buff_size = block_end - block_start
            buff = fd.read(buff_size)
            content = buff + content

        yaml_content = content[content.find(b"\n") + 1 :]

        # The following call to yaml.load is safe because we're
        # using pyyaml's SafeLoader.
        offsets = yaml.load(yaml_content, Loader=yamlutil._yaml_base_loader)  # noqa: S506

        # Make sure the indices look sane
        if not isinstance(offsets, list) or len(offsets) == 0:
            return

        last_offset = 0
        for x in offsets:
            if not isinstance(x, int) or x > file_size or x < 0 or x <= last_offset + Block._header.size:
                return
            last_offset = x

        # We always read the first block, so we can confirm that the
        # first entry in the block index matches the first block
        if offsets[0] != first_block.offset:
            return

        if len(offsets) == 1:
            # If there's only one block in the index, we've already
            # loaded the first block, so just return: we have nothing
            # left to do
            return

        # One last sanity check: Read the last block in the index and
        # make sure it makes sense.
        fd.seek(offsets[-1], generic_io.SEEK_SET)
        try:
            block = self._new_block().read(fd)
        except (ValueError, OSError):
            return

        # Now see if the end of the last block leads right into the index
        if block.end_offset != index_start:
            return

        # It seems we're good to go, so instantiate the UnloadedBlock
        # objects
        for offset in offsets[1:-1]:
            self._internal_blocks.append(UnloadedBlock(fd, offset, memmap=self.memmap, lazy_load=self.lazy_load))

        # We already read the last block in the file -- no need to read it again
        self._internal_blocks.append(block)

        # Record that all block locations have been mapped out (used to avoid
        # unnecessary calls to finish_reading_internal_blocks later).
        self._internal_blocks_mapped = True

        # Materialize the internal blocks if we are not lazy
        if not self.lazy_load:
            self.finish_reading_internal_blocks()

    def get_external_filename(self, filename, index):
        """
        Given a main filename and an index number, return a new file
        name for referencing an external block.
        """
        filename = os.path.splitext(filename)[0]
        return filename + f"{index:04d}.asdf"

    def get_external_uri(self, uri, index):
        """
        Given a main URI and an index number, return a new URI for
        saving an external block.
        """
        if uri is None:
            uri = ""
        parts = list(patched_urllib_parse.urlparse(uri))
        path = parts[2]
        dirname, filename = os.path.split(path)
        filename = self.get_external_filename(filename, index)
        path = os.path.join(dirname, filename)
        parts[2] = path
        return patched_urllib_parse.urlunparse(parts)

    def _find_used_blocks(self, tree, ctx, remove=True):
        reserved_blocks = set()

        for node in treeutil.iter_tree(tree):
            if ctx.extension_manager.handles_type(type(node)):
                converter = ctx.extension_manager.get_converter_for_type(type(node))
                sctx = ctx._create_serialization_context()
                tag = converter.select_tag(node, sctx)
                for key in converter.reserve_blocks(node, tag, sctx):
                    reserved_blocks.add(self.find_or_create_block(key))
            else:
                hook = ctx._type_index.get_hook_for_type("reserve_blocks", type(node), ctx.version_string)
                if hook is not None:
                    for block in hook(node, ctx):
                        reserved_blocks.add(block)

        if remove:
            for block in list(self.blocks):
                if getattr(block, "_used", 0) == 0 and block not in reserved_blocks:
                    self.remove(block)
            return None
        for block in list(self.blocks):
            if getattr(block, "_used", 0):
                reserved_blocks.add(block)
        return reserved_blocks

    def _handle_global_block_settings(self, block):
        cfg = get_config()
        all_array_storage = cfg.all_array_storage
        if all_array_storage:
            self.set_array_storage(block, all_array_storage)

        all_array_compression = cfg.all_array_compression
        all_array_compression_kwargs = cfg.all_array_compression_kwargs
        # Only override block compression algorithm if it wasn't explicitly set
        # by AsdfFile.set_array_compression.
        if all_array_compression != "input":
            block.output_compression = all_array_compression
            block.output_compression_kwargs = all_array_compression_kwargs

        if all_array_storage is None:
            threshold = get_config().array_inline_threshold
            if threshold is not None and block.array_storage in ["internal", "inline"]:
                if np.prod(block.data.shape) < threshold:
                    self.set_array_storage(block, "inline")
                else:
                    self.set_array_storage(block, "internal")

    def finalize(self, ctx):
        """
        At this point, we have a complete set of blocks for the file,
        with no extras.

        Here, they are reindexed, and possibly reorganized.
        """
        # TODO: Should this reset the state (what's external and what
        # isn't) afterword?

        self._find_used_blocks(ctx.tree, ctx)

        for block in list(self.blocks):
            self._handle_global_block_settings(block)

    def get_block_by_key(self, key):
        if key not in self._data_to_block_mapping:
            msg = f"Unknown block key {key}"
            raise KeyError(msg)
        return self._data_to_block_mapping[key]

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
        # If an "int", it is the index of an internal block
        if isinstance(source, int):
            if source == -1:
                if len(self._streamed_blocks):
                    return self._streamed_blocks[0]
                # If we don't have a streamed block, fall through so
                # we can read all of the blocks, ultimately arriving
                # at the last one, which, if all goes well is a
                # streamed block.

            # First, look in the blocks we've already read
            elif source >= 0:
                if source < len(self._internal_blocks):
                    return self._internal_blocks[source]
            else:
                msg = f"Invalid source id {source}"
                raise ValueError(msg)

            # If we have a streamed block or we already know we have
            # no blocks, reading any further isn't going to yield any
            # new blocks.
            if len(self._streamed_blocks) or len(self._internal_blocks) == 0:
                msg = f"Block '{source}' not found."
                raise ValueError(msg)

            # If the desired block hasn't already been read, and the
            # file is seekable, and we have at least one internal
            # block, then we can move the file pointer to the end of
            # the last known internal block, and start looking for
            # more internal blocks.  This is "deferred block loading".
            last_block = self._internal_blocks[-1]

            if last_block._fd is not None and last_block._fd.seekable():
                last_block._fd.seek(last_block.end_offset)
                while True:
                    next_block = self._read_next_internal_block(last_block._fd, False)
                    if next_block is None:
                        break
                    if len(self._internal_blocks) - 1 == source:
                        return next_block
                    last_block = next_block

            if source == -1 and last_block.array_storage == "streamed":
                return last_block

            msg = f"Block '{source}' not found."
            raise ValueError(msg)

        if isinstance(source, str):
            asdffile = self._asdffile().open_external(source)
            block = asdffile._blocks._internal_blocks[0]
            self.set_array_storage(block, "external")

        # Handle the case of inline data
        elif isinstance(source, list):
            block = Block(data=np.array(source), array_storage="inline")

        else:
            msg = f"Unknown source '{source}'"
            raise TypeError(msg)

        return block

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
                if internal_block.array_storage == "streamed":
                    return -1
                return i

        for i, external_block in enumerate(self.external_blocks):
            if block == external_block:
                if self._asdffile().uri is None:
                    msg = "Can't write external blocks, since URI of main file is unknown."
                    raise ValueError(msg)

                parts = list(patched_urllib_parse.urlparse(self._asdffile().uri))
                path = parts[2]
                filename = os.path.basename(path)
                return self.get_external_filename(filename, i)

        msg = "block not found."
        raise ValueError(msg)

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
        from asdf.tags.core import ndarray

        if isinstance(arr, ndarray.NDArrayType) and arr.block is not None and arr.block in self.blocks:
            return arr.block

        base = util.get_array_base(arr)
        block = self._data_to_block_mapping.get(id(base))
        if block is not None:
            return block

        block = Block(base)
        self.add(block)
        self._handle_global_block_settings(block)
        return block

    def find_or_create_block(self, key):
        """
        For a given hashable key, looks for an existing block. If not
        found, adds a new block to the block list. Returns the index
        in the block list to the array.

        Parameters
        ----------
        key : hashable

        Returns
        -------
        block : Block
        """
        block = self._data_to_block_mapping.get(key)
        if block is not None:
            return block

        block = Block()
        self.add(block, key=key)
        self._handle_global_block_settings(block)
        self._data_to_block_mapping[key] = block

        return block

    def get_streamed_block(self):
        """
        Get the streamed block, which is always the last one.  A
        streamed block, on writing, does not manage data of its own,
        but the user is expected to stream it to disk directly.
        """
        block = self.streamed_block
        if block is None:
            block = Block(array_storage="streamed")
            self.add(block)
        return block

    def add_inline(self, array):
        """
        Add an inline block for ``array`` to the block set.
        """
        block = Block(array, array_storage="inline")
        self.add(block)
        return block

    def get_output_compressions(self):
        """
        Get the list of unique compressions used on blocks.
        """
        return list({b.output_compression for b in self.blocks})

    def get_output_compression_extensions(self):
        """
        Infer the compression extensions used on blocks.
        Note that this is somewhat indirect and could be fooled if a new extension
        for the same compression label is loaded after the compression of the block.
        """
        ext = []
        for label in self.get_output_compressions():
            compressor = mcompression._get_compressor_from_extensions(label, return_extension=True)
            if compressor is not None:
                ext += [compressor[1]]  # second item is the extension
        return ext

    def __getitem__(self, arr):
        return self.find_or_create_block_for_array(arr)

    def close(self):
        for block in self.blocks:
            block.close()
