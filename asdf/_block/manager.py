import collections
import contextlib
import copy

from asdf import config, constants, generic_io, util

from . import external, reader, store, writer
from . import io as bio
from .callback import DataCallback
from .key import Key as BlockKey
from .options import Options


class ReadBlocks(collections.UserList):
    # workaround inability to weakref a list
    pass


class OptionsStore(store.Store):
    """
    A Store of Options that can be accessed by Key
    (see ``asdf._block.store.Store``).
    """

    def __init__(self, read_blocks=None):
        super().__init__()
        self._read_blocks = read_blocks

    def has_options(self, array):
        """
        Check of Options have been defined for this array
        without falling back to generating Options from
        a ReadBlock.

        Parameters
        ----------
        array : ndarray
            The base of this array (see `asdf.util.get_array_base`) will
            be used to lookup any Options in the Store.

        Returns
        -------
        has_options : bool
            True if Options were previously defined for this array.
        """
        base = util.get_array_base(array)
        return self.lookup_by_object(base) is not None

    def get_options_from_block(self, array):
        """
        Get Options for some array using only settings read from a
        corresponding ReadBlock (one that shares the same base array).
        Any Options defined using previous calls to set_options will
        be ignored (use ``get_options`` if you would like these previously
        set options to be considered).

        Parameters
        ----------
        array : ndarray
            The base of this array (see `asdf.util.get_array_base`) will
            be used to lookup a corresponding ReadBlock.

        Returns
        -------
        options : Options or None
            Options initialized from settings read from a ReadBlock
            or None if no corresponding block was found.
        """
        base = util.get_array_base(array)
        # look up by block with matching _data
        for block in self._read_blocks:
            if block._cached_data is base or block._data is base:
                # init options
                if block.header["flags"] & constants.BLOCK_FLAG_STREAMED:
                    storage_type = "streamed"
                else:
                    storage_type = "internal"
                options = Options(storage_type, block.header["compression"])
                return options
        return None

    def get_options(self, array):
        """
        Get Options for some array using either previously defined
        options (as set by ``set_options``) or settings read from a
        corresponding ReadBlock (one that shares the same base array).

        Note that if no options are found in the Store and options
        are found from a ReadBlock the resulting Options will be added
        to the Store.

        Parameters
        ----------
        array : ndarray
            The base of this array (see `asdf.util.get_array_base`) will
            be used to lookup any Options in the Store.

        Returns
        -------
        options : Options or None
            Options read from the Store or ReadBlocks or None if
            no options were found.
        """
        base = util.get_array_base(array)
        options = self.lookup_by_object(base)
        if options is None:
            options = self.get_options_from_block(base)
            if options is not None:
                self.set_options(base, options)
        if options is None:
            options = Options()
            self.set_options(base, options)
        return options

    def set_options(self, array, options):
        """
        Set Options for an array.

        Parameters
        ----------
        array : ndarray
            The base of this array (see `asdf.util.get_array_base`) will
            be used to add options to the Store.

        options : Options
            The Options to add to the Store for this array.

        Raises
        ------
        ValueError
            If more than one block is set as a streamed block.
        """
        if options.storage_type == "streamed":
            for oid, by_key in self._by_id.items():
                for key, opt in by_key.items():
                    if not key._is_valid():
                        continue
                    if opt.storage_type == "streamed":
                        if opt is options:
                            continue
                        msg = "Can not add second streaming block"
                        raise ValueError(msg)
        base = util.get_array_base(array)
        self.assign_object(base, options)

    def get_output_compressions(self):
        """
        Get all output compression types used for this Store of
        Options.

        Returns
        -------
        compressions : list of bytes
            List of 4 byte compression labels used for this OptionsStore.
        """
        compressions = set()
        cfg = config.get_config()
        if cfg.all_array_compression == "input":
            for blk in self._read_blocks:
                if blk.header["compression"]:
                    compressions.add(blk.header["compression"])
        else:
            compressions.add(cfg.all_array_compression)
        for _, by_key in self._by_id.items():
            for key, opts in by_key.items():
                if not key._is_valid():
                    continue
                if opts.compression:
                    compressions.add(opts.compression)
        return compressions


class Manager:
    """
    Manager for reading, writing and storing options for ASDF blocks.
    """

    def __init__(self, read_blocks=None, uri=None, lazy_load=False, memmap=False, validate_checksums=False):
        if read_blocks is None:
            read_blocks = ReadBlocks([])
        self.options = OptionsStore(read_blocks)

        self._blocks = read_blocks
        self._external_block_cache = external.ExternalBlockCache()
        self._data_callbacks = store.Store()

        self._write_blocks = store.LinearStore()
        self._external_write_blocks = []
        self._streamed_write_block = None
        self._streamed_obj_keys = set()
        self._write_fd = None

        self._uri = uri

        # general block settings
        self._lazy_load = lazy_load
        self._memmap = memmap
        self._validate_checksums = validate_checksums

    @property
    def blocks(self):
        """
        Get any ReadBlocks that were read from an ASDF file

        Returns
        -------
        read_blocks : list of ReadBlock
            List of ReadBlock instances created during a call to read
            or update.
        """
        return self._blocks

    @blocks.setter
    def blocks(self, new_blocks):
        if not isinstance(new_blocks, ReadBlocks):
            new_blocks = ReadBlocks(new_blocks)
        self._blocks = new_blocks
        # we propagate these blocks to options so that
        # options lookups can fallback to the new read blocks
        self.options._read_blocks = new_blocks

    def read(self, fd, after_magic=False):
        """
        Read blocks from an ASDF file and update the manager read_blocks.

        Parameters
        ----------
        fd : file or generic_io.GenericIO
            File to read from. Reading starts at the current file position.

        after_magic : bool, optional, default False
            If True, the file pointer is past the block magic bytes of the
            first block.
        """
        self.blocks = reader.read_blocks(
            fd, self._memmap, self._lazy_load, self._validate_checksums, after_magic=after_magic
        )

    def _load_external(self, uri):
        value = self._external_block_cache.load(self._uri, uri)
        if value is external.UseInternal:
            return self.blocks[0].data
        return value

    def _clear_write(self):
        self._write_blocks = store.LinearStore()
        self._external_write_blocks = []
        self._streamed_write_block = None
        self._streamed_obj_keys = set()
        self._write_fd = None

    def _write_external_blocks(self):
        from asdf import AsdfFile

        if self._write_fd is None or self._write_fd.uri is None:
            msg = "Can't write external blocks, since URI of main file is unknown."
            raise ValueError(msg)

        for blk in self._external_write_blocks:
            uri = generic_io.resolve_uri(self._write_fd.uri, blk._uri)
            af = AsdfFile()
            with generic_io.get_file(uri, mode="w") as f:
                af.write_to(f, include_block_index=False)
                writer.write_blocks(f, [blk])

    def make_write_block(self, data, options, obj):
        """
        Make a WriteBlock with data and options and
        associate it with an object (obj).

        Parameters
        ----------
        data : npdarray or callable
            Data to be written to an ASDF block. Can be provided as
            a callable function that when evaluated will return the
            data.
        options : Options
            Options instance used to define the ASDF block compression
            and storage type.
        obj : object
            An object in the ASDF tree that will be associated
            with the new WriteBlock so that `AsdfFile.update` can
            map newly created blocks to blocks read from the original
            file.

        Returns
        -------
        block_source : int or str
            The relative uri (str) if an external block was created
            or the index of the block (int) for an internal block.

        Raises
        ------
        ValueError
            If a external block was created without a URI for the main
            file.
        """
        if options.storage_type == "external":
            for index, blk in enumerate(self._external_write_blocks):
                if blk._data is data:
                    # this external uri is already ready to go
                    return blk._uri
            # need to set up new external block
            index = len(self._external_write_blocks)
            blk = writer.WriteBlock(data, options.compression, options.compression_kwargs)
            if self._write_fd is not None:
                base_uri = self._write_fd.uri or self._uri
            else:
                base_uri = self._uri
            if base_uri is None:
                msg = "Can't write external blocks, since URI of main file is unknown."
                raise ValueError(msg)
            blk._uri = external.uri_for_index(base_uri, index)
            self._external_write_blocks.append(blk)
            return blk._uri
        # first, look for an existing block
        for index, blk in enumerate(self._write_blocks):
            if blk._data is data:
                self._write_blocks.assign_object(obj, blk)
                return index
        # if no block is found, make a new block
        blk = writer.WriteBlock(data, options.compression, options.compression_kwargs)
        self._write_blocks._items.append(blk)
        self._write_blocks.assign_object(obj, blk)
        return len(self._write_blocks) - 1

    def set_streamed_write_block(self, data, obj):
        """
        Create a WriteBlock that will be written as an ASDF
        streamed block.

        Parameters
        ----------
        data : ndarray or callable
            Data to be written to an ASDF block. Can be provided as
            a callable function that when evaluated will return the
            data.
        obj : object
            An object in the ASDF tree that will be associated
            with the new WriteBlock so that `AsdfFile.update` can
            map newly created blocks to blocks read from the original
            file.
        """
        if self._streamed_write_block is not None and data is not self._streamed_write_block.data:
            msg = "Can not add second streaming block"
            raise ValueError(msg)
        if self._streamed_write_block is None:
            self._streamed_write_block = writer.WriteBlock(data)
        self._streamed_obj_keys.add(BlockKey(obj))

    def _get_data_callback(self, index):
        return DataCallback(index, self.blocks)

    def _set_array_storage(self, data, storage):
        options = self.options.get_options(data)
        options.storage_type = storage
        self.options.set_options(data, options)

    def _get_array_storage(self, data):
        return self.options.get_options(data).storage_type

    def _set_array_compression(self, arr, compression, **compression_kwargs):
        # if this is input compression but we already have defined options
        # we need to re-lookup the options based off the block
        if compression == "input" and self.options.has_options(arr):
            from_block_options = self.options.get_options_from_block(arr)
            if from_block_options is not None:
                compression = from_block_options.compression
        options = self.options.get_options(arr)
        options.compression = compression
        options.compression_kwargs = compression_kwargs

    def _get_array_compression(self, arr):
        return self.options.get_options(arr).compression

    def _get_array_compression_kwargs(self, arr):
        return self.options.get_options(arr).compression_kwargs

    def get_output_compressions(self):
        return self.options.get_output_compressions()

    @contextlib.contextmanager
    def options_context(self):
        """
        Context manager that copies block options on
        entrance and restores the options when exited.
        """
        previous_options = copy.deepcopy(self.options)
        yield
        self.options = previous_options
        self.options._read_blocks = self.blocks

    @contextlib.contextmanager
    def write_context(self, fd, copy_options=True):
        """
        Context manager that copies block options on
        entrance and restores the options when exited.

        Parameters
        ----------
        fd : file or generic_io.GenericIO
            File to be written to. This is required on
            entrance to this context so that any external
            blocks can resolve relative uris.

        copy_options : bool, optional, default True
            Copy options on entrance and restore them on
            exit (See `options_context`).
        """
        self._clear_write()
        self._write_fd = fd
        if copy_options:
            with self.options_context():
                yield
        else:
            yield
        self._clear_write()

    def write(self, pad_blocks, include_block_index):
        """
        Write blocks that were set up during the current
        `write_context`.

        Parameters
        ----------
        pad_blocks : bool, None or float
            If False, add no padding bytes between blocks. If True
            add some default amount of padding. If a float, add
            a number of padding bytes based off a ratio of the data
            size.

        include_block_index : bool
            If True, include a block index at the end of the file.
            If a streamed_block is provided (or the file is not
            seekable) no block index will be written.

        Raises
        ------
        OSError
            If called outside a `write_context`.
        """
        if self._write_fd is None:
            msg = "write called outside of valid write_context"
            raise OSError(msg)
        if len(self._write_blocks) or self._streamed_write_block:
            writer.write_blocks(
                self._write_fd,
                self._write_blocks,
                pad_blocks,
                streamed_block=self._streamed_write_block,
                write_index=include_block_index,
            )
        if len(self._external_write_blocks):
            self._write_external_blocks()

    def update(self, new_tree_size, pad_blocks, include_block_index):
        """
        Perform an update-in-place of ASDF blocks set up during
        a `write_context`.

        Parameters
        ----------
        new_tree_size : int
            Size (in bytes) of the serialized ASDF tree (and any
            header bytes) that will be written at the start of the
            file being updated.

        pad_blocks : bool, None or float
            If False, add no padding bytes between blocks. If True
            add some default amount of padding. If a float, add
            a number of padding bytes based off a ratio of the data
            size.

        include_block_index : bool
            If True, include a block index at the end of the file.
            If a streamed_block is provided (or the file is not
            seekable) no block index will be written.


        Raises
        ------
        OSError
            If called outside a `write_context`.
        """
        if self._write_fd is None:
            msg = "update called outside of valid write_context"
            raise OSError(msg)
        # find where to start writing blocks (either end of new tree or end of last 'free' block)
        last_block = None
        for blk in self.blocks[::-1]:
            if not blk.memmap and (blk._cached_data is not None or not callable(blk._data)):
                continue
            last_block = blk
            break
        if last_block is None:
            new_block_start = new_tree_size
        else:
            new_block_start = max(
                last_block.data_offset + last_block.header["allocated_size"],
                new_tree_size,
            )

        if len(self._external_write_blocks):
            self._write_external_blocks()

        # do we have any blocks to write?
        if len(self._write_blocks) or self._streamed_write_block:
            self._write_fd.seek(new_block_start)
            offsets, headers = writer.write_blocks(
                self._write_fd,
                self._write_blocks,
                pad_blocks,
                streamed_block=self._streamed_write_block,
                write_index=False,  # don't write an index as we will modify the offsets
            )
            new_block_end = self._write_fd.tell()

            # move blocks to start in increments of block_size
            n_bytes = new_block_end - new_block_start
            src, dst = new_block_start, new_tree_size
            block_size = self._write_fd.block_size
            while n_bytes > 0:
                self._write_fd.seek(src)
                bs = self._write_fd.read(min(n_bytes, block_size))
                self._write_fd.seek(dst)
                self._write_fd.write(bs)
                n = len(bs)
                n_bytes -= n
                src += n
                dst += n

            # update offset to point at correct locations
            offsets = [o - (new_block_start - new_tree_size) for o in offsets]

            # write index if no streamed block
            if include_block_index and self._streamed_write_block is None:
                bio.write_block_index(self._write_fd, offsets)

            # map new blocks to old blocks
            new_read_blocks = ReadBlocks()
            for i, (offset, header) in enumerate(zip(offsets, headers)):
                # find all objects that assigned themselves to
                # the write block (wblk) at index i
                if i == len(self._write_blocks):  # this is a streamed block
                    obj_keys = self._streamed_obj_keys
                    wblk = self._streamed_write_block
                else:
                    wblk = self._write_blocks[i]
                    # find object associated with wblk
                    obj_keys = set()
                    for oid, by_key in self._write_blocks._by_id.items():
                        for key, index in by_key.items():
                            if self._write_blocks[index] is wblk:
                                obj_keys.add(key)

                # we have to be lazy here as any current memmap is invalid
                new_read_block = reader.ReadBlock(offset + 4, self._write_fd, self._memmap, True, False, header=header)
                new_read_blocks.append(new_read_block)
                new_index = len(new_read_blocks) - 1

                # update all callbacks
                for obj_key in obj_keys:
                    obj = obj_key._ref()
                    if obj is None:
                        # this object no longer exists so don't both assigning it
                        continue

                    # update data callbacks to point to new block
                    cb = self._data_callbacks.lookup_by_object(obj)
                    if cb is not None:
                        cb._reassign(new_index, new_read_blocks)

            # update read blocks to reflect new state
            self.blocks = new_read_blocks
