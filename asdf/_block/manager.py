import contextlib
import copy
import os
import weakref

from asdf import config, constants, generic_io, util

from . import store
from .callback import DataCallback
from .options import Options
from .writer import WriteBlock, write_blocks


class ReadBlocks(store.LinearStore):
    """
    {obj: block_index} : where obj is NDArrayType or other high level object
    [block_0, block_1, ...]
    """

    def set_blocks(self, blocks):
        self._items = blocks
        # TODO should this invalidate the associations?

    def append_block(self, block):
        self._items.append(block)


class BlockOptions(store.Store):
    """
    {array_base: options}
    read_blocks (instance of ReadBlocks)
    """

    def __init__(self, read_blocks=None):
        super().__init__()
        self._read_blocks = read_blocks

    def get_options(self, array):
        base = util.get_array_base(array)
        options = self.lookup_by_object(base)
        if options is None:
            # look up by block with matching _data
            for block in self._read_blocks:
                if block._cached_data is base or block._data is base:
                    # init options
                    if block.header["flags"] & constants.BLOCK_FLAG_STREAMED:
                        storage_type = "streamed"
                    else:
                        storage_type = "internal"
                    options = Options(storage_type, block.header["compression"])
                    # set options
                    self.set_options(base, options)
                    break
        if options is None:
            options = Options()
            self.set_options(base, options)
        return options

    def set_options(self, array, options):
        if options.storage_type == "streamed":
            for oid, by_key in self._by_id.items():
                for key, opt in by_key.items():
                    if not key.is_valid():
                        continue
                    if opt.storage_type == "streamed":
                        if opt is options:
                            continue
                        raise ValueError("Can not add second streaming block")
        base = util.get_array_base(array)
        self.assign_object(base, options)

    def get_output_compressions(self):
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
                if not key.is_valid():
                    continue
                if opts.compression:
                    compressions.add(opts.compression)
        return compressions


def make_external_uri(uri, index):
    if uri is None:
        uri = ""
    parts = list(util.patched_urllib_parse.urlparse(uri))
    path = parts[2]
    dirname, filename = os.path.split(path)
    filename = os.path.splitext(filename)[0] + f"{index:04d}.asdf"
    return filename


def resolve_external_uri(uri, relative):
    if uri is None:
        uri = ""
    parts = list(util.patched_urllib_parse.urlparse(uri))
    path = parts[2]
    dirname, filename = os.path.split(path)
    path = os.path.join(dirname, relative)
    parts[2] = path
    return util.patched_urllib_parse.urlunparse(parts)


class Manager:
    def __init__(self, read_blocks=None, uri=None):
        if read_blocks is None:
            read_blocks = ReadBlocks([])
        self.options = BlockOptions(read_blocks)
        self.blocks = read_blocks
        self._data_callbacks = store.Store()
        self._write_blocks = store.LinearStore()
        self._external_write_blocks = []
        self._streamed_block = None
        self._streamed_obj = None
        self._write_fd = None
        self._uri = uri

    def _clear_write(self):
        self._write_blocks = store.LinearStore()
        self._external_write_blocks = []
        self._streamed_block = None
        self._streamed_obj = None
        self._write_fd = None

    def _write_external_blocks(self):
        from asdf import AsdfFile

        if not len(self._external_write_blocks):
            return

        if self._write_fd.uri is None:
            raise ValueError("Can't write external blocks, since URI of main file is unknown.")

        for blk in self._external_write_blocks:
            uri = resolve_external_uri(self._write_fd.uri, blk._uri)
            af = AsdfFile()
            with generic_io.get_file(uri, mode="w") as f:
                af.write_to(f, include_block_index=False)
                write_blocks(f, [blk])

    def make_write_block(self, data, options, obj):
        # if we're not actually writing just return a junk index
        # if self._write_fd is None:
        #    return constants.MAX_BLOCKS + 1
        if options.storage_type == "external":
            for index, blk in enumerate(self._external_write_blocks):
                if blk._data is data:
                    # this external uri is already ready to go
                    return blk._uri
            # need to set up new external block
            index = len(self._external_write_blocks)
            blk = WriteBlock(data, options.compression, options.compression_kwargs)
            base_uri = self._uri or self._write_fd.uri
            blk._uri = make_external_uri(base_uri, index)
            self._external_write_blocks.append(blk)
            return blk._uri
        # first, look for an existing block
        for index, blk in enumerate(self._write_blocks):
            if blk._data is data:
                self._write_blocks.assign_object(obj, blk)
                return index
        # if no block is found, make a new block
        blk = WriteBlock(data, options.compression, options.compression_kwargs)
        self._write_blocks._items.append(blk)
        self._write_blocks.assign_object(obj, blk)
        return len(self._write_blocks) - 1

    def set_streamed_block(self, data, obj):
        if self._streamed_block is not None and data is not self._streamed_block.data:
            raise ValueError("Can not add second streaming block")
        self._streamed_block = WriteBlock(data)
        self._streamed_obj = weakref.ref(obj)

    def _get_data_callback(self, index):
        return DataCallback(index, self.blocks)

    def _set_array_storage(self, data, storage):
        options = self.options.get_options(data)
        options.storage_type = storage
        self.options.set_options(data, options)

    def _get_array_storage(self, data):
        return self.options.get_options(data).storage_type

    def _set_array_compression(self, arr, compression, **compression_kwargs):
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
        previous_options = copy.deepcopy(self.options)
        yield
        self.options = previous_options
        self.options._read_blocks = self.blocks

    @contextlib.contextmanager
    def write_context(self, fd, copy_options=True):
        self._clear_write()
        self._write_fd = fd
        if copy_options:
            with self.options_context():
                yield
        else:
            yield
        self._clear_write()

    def write(self, fd, pad_blocks, include_block_index):
        if self._write_fd is None or fd is not self._write_fd:
            msg = "Write called outside of valid write_context"
            raise OSError(msg)
        if len(self._write_blocks) or self._streamed_block:
            write_blocks(
                fd,
                self._write_blocks,
                pad_blocks,
                streamed_block=self._streamed_block,
                write_index=include_block_index,
            )
        if len(self._external_write_blocks):
            self._write_external_blocks()
