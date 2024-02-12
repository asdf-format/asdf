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
    """
    A list of ReadBlock instances.

    A simple list can't be used as other code will need
    to generate a weakref to instances of this class
    (and it is not possible to generate a weakref to a list).
    """

    pass


class WriteBlocks(collections.abc.Sequence):
    """
    A collection of ``WriteBlock`` instances that can be accessed by:
        - numerical index (see ``collections.abc.Sequence``)
        - the object or objects in the tree that created or
          are associated with this block
        - the block data
    Access by object and data is via a Store which generates
    Keys to allow use of non-hashable objects (and to not hold
    a reference to the block data).
    """

    def __init__(self, blocks=None):
        if blocks is None:
            blocks = []
        self._blocks = blocks

        # both stores contain values that are indices of
        # WriteBlock instances in _blocks
        self._data_store = store.Store()
        self._object_store = store.Store()

    def __getitem__(self, index):
        return self._blocks.__getitem__(index)

    def __len__(self):
        return self._blocks.__len__()

    def index_for_data(self, data):
        return self._data_store.lookup_by_object(data)

    def assign_object_to_index(self, obj, index):
        self._object_store.assign_object(obj, index)

    def object_keys_for_index(self, index):
        yield from self._object_store.keys_for_value(index)

    def append_block(self, blk, obj):
        """
        Append a ``WriteBlock`` instance to this collection
        assign an object, obj, to the block and return
        the index of the block within the collection.
        """
        index = len(self._blocks)
        self._blocks.append(blk)

        # assign the block data to this block to allow
        # fast lookup of blocks based on data
        self._data_store.assign_object(blk._data, index)

        # assign the object that created/uses this block
        self._object_store.assign_object(obj, index)
        return index


class OptionsStore(store.Store):
    """
    A ``Store`` of ``Options`` that can be accessed by the base
    array that corresponds to a block. A ``Store`` is used
    to avoid holding references to the array data
    (see ``asdf._block.store.Store``).

    When ``Options`` are not found within the ``Store``, the
    ``OptionsStore`` will look for any available matching
    ``ReadBlock`` to determine default Options.
    """

    def __init__(self, read_blocks):
        super().__init__()
        # ReadBlocks are needed to look up default options
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
    ``Manager`` for reading, writing and storing options for ASDF blocks.

    This class does the heavy lifting of allowing ``asdf.AsdfFile`` instances
    to control ASDF blocks. It is responsible for reading and writing blocks
    primarily to maintain some consistency with the previous BlockManager.

    Block ``Options`` control the compression and type of storage for an
    ASDF block (see `asdf.AsdfFile.set_array_storage`,
    `asdf.AsdfFile.set_array_compression`
    `asdf.AsdfFile.set_array_compression` for relevant usage and information).
    These ``Options`` instances are stored and retrieved using the base
    of the array containing the data for an ASDF block. This allows arrays
    that share the same base array (ie views of the same array) to use
    the same ASDF block.

    Reading blocks occurs through use of ``Manager.read`` which will
    create ``ReadBlock`` instances for each read ASDF block. These ``ReadBlock``
    will be used as the source for default ``Options`` for each block
    and ASDF block data can be read using ``DataCallback`` instances.
    These callbacks are used (instead of just accessing blocks by index)
    to allow block reorganization during ``update``.(Note that reading
    of external blocks is special as these are not stored within the
    block section of the ASDF file. These must be explicitly loaded
    using ``Manager._load_external``).

    Writing ASDF blocks occurs through use of ``Manager.write`` which will
    take any queued ``WriteBlocks`` (created via ``Manager.make_write_block``
    and ``Manager.set_streamed_write_block``) and write them out to a file.
    This writing must occur within a ``Manager.write_context`` to allow the
    ``Manager`` to reset any ``Options`` changes that occur during write
    and to clean up the write queue.

    Update-in-place occurs through use of ``Manager.update`` which, like
    ``Manager.write`` must occur within a ``Manager.write_context``. Following
    a ``Manager.update`` the ``ReadBlock`` instances will be replaced with
    the newly written ASDF blocks and any ``DataCallbacks`` will be updated
    to reference the appropriate new ``ReadBlock``.
    """

    def __init__(self, read_blocks=None, uri=None, lazy_load=False, memmap=False, validate_checksums=False):
        if read_blocks is None:
            read_blocks = ReadBlocks([])
        self.options = OptionsStore(read_blocks)

        self._blocks = read_blocks
        self._external_block_cache = external.ExternalBlockCache()
        self._data_callbacks = store.Store()

        self._write_blocks = WriteBlocks()
        self._external_write_blocks = []
        self._streamed_write_block = None
        self._streamed_obj_keys = set()
        self._write_fd = None

        # store the uri of the ASDF file here so that the Manager can
        # resolve and load external blocks without requiring a reference
        # to the AsdfFile instance
        self._uri = uri

        # general block settings
        self._lazy_load = lazy_load
        self._memmap = memmap
        self._validate_checksums = validate_checksums

    def close(self):
        self._external_block_cache.clear()
        self._clear_write()
        for blk in self.blocks:
            blk.close()
        self.options = OptionsStore(self.blocks)

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
        value = self._external_block_cache.load(self._uri, uri, self._memmap, self._validate_checksums)
        if value is external.UseInternal:
            return self.blocks[0].data
        return value

    def _clear_write(self):
        self._write_blocks = WriteBlocks()
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
        options : Options or None
            Options instance used to define the ASDF block compression
            and storage type. If None, a new Options instance will
            be created.
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
        if options is None:
            options = Options()
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
            blk._uri = external.relative_uri_for_index(base_uri, index)
            self._external_write_blocks.append(blk)
            return blk._uri
        # first, look for an existing block
        index = self._write_blocks.index_for_data(data)
        if index is not None:
            self._write_blocks.assign_object_to_index(obj, index)
            return index
        # if no block is found, make a new block
        blk = writer.WriteBlock(data, options.compression, options.compression_kwargs)
        index = self._write_blocks.append_block(blk, obj)
        return index

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

    def _set_array_save_base(self, data, save_base):
        options = self.options.get_options(data)
        options.save_base = save_base
        self.options.set_options(data, options)

    def _get_array_save_base(self, data):
        return self.options.get_options(data).save_base

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
                # find all objects that assigned themselves to the write block at index i
                if i == len(self._write_blocks):  # this is a streamed block
                    obj_keys = self._streamed_obj_keys
                else:
                    # find object associated with this write block
                    obj_keys = set(self._write_blocks.object_keys_for_index(i))

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
