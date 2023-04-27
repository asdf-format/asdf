import os

from asdf import constants, generic_io, util

from . import store
from .options import Options
from .writer import WriteBlock, write_blocks


class ReadBlocks(store.LinearStore):
    """
    {obj: block_index} : where obj is NDArrayType or other high level object
    [block_0, block_1, ...]
    """

    # def get_block_for_array(self, array):
    #     base = util.get_array_base(array)
    #     block_index = self.lookup_by_object(base)
    #     if block_index is None:
    #         return self.get_block_with_data(base)
    #     return self[block_index]

    # def get_block_with_data(self, array):
    #     base = util.get_array_base(array)
    #     for (block_index, block) in enumerate(self):
    #         if block._data is not None and not callable(block._data):
    #             if block._data is base:
    #                 if self.lookup_by_object(base) is None:
    #                     self.assign_array_to_block_index(base, block_index)
    #                 return block
    #     return None

    # def assign_read_blocks(self):
    #     for (block_index, block) in enumerate(self):
    #         if block._data is not None and not callabale(block._data):
    #             self.assign_array_to_block_index(block._data, block_index)
    #             base = util.get_array_base(block._data)

    # def assign_array_to_block_index(self, array, block_index):
    #     base = util.get_array_base(array)
    #     self.assign_object(base, block_index)

    # def assign_array_to_block(self, array, block):
    #     block_index = self.index(block)
    #     self.assign_array_to_block_index(array, block_index)
    pass


class BlockOptions(store.Store):
    """
    {array_base: options}
    read_blocks (instance of ReadBlocks)
    """

    def __init__(self, read_blocks=None):
        super().__init__()
        if read_blocks is None:
            self._read_blocks = ReadBlocks([])
        elif isinstance(read_blocks, ReadBlocks):
            self._read_blocks = read_blocks
        else:
            self._read_blocks = ReadBlocks(read_blocks)

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
            for d in self._by_id.values():
                for opt in d.values():
                    if opt.storage_type == "streamed":
                        if opt is options:
                            continue
                        raise ValueError("Can not add second streaming block")
        base = util.get_array_base(array)
        self.assign_object(base, options)

    # TODO copy to allow for changing settings on write
    # TODO make an 'update_options'


def make_external_uri(uri, index):
    if uri is None:
        uri = ""
    parts = list(util.patched_urllib_parse.urlparse(uri))
    path = parts[2]
    dirname, filename = os.path.split(path)
    filename = os.path.splitext(filename)[0] + f"{index:04d}.asdf"
    return filename
    # path = os.path.join(dirname, filename)
    # parts[2] = path
    # return util.patched_urllib_parse.urlunparse(parts)


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
    def __init__(self, read_blocks=None):
        self.options = BlockOptions(read_blocks)
        if read_blocks is None:
            self.blocks = self.options._read_blocks
        else:
            self.blocks = read_blocks
        # TODO copy options and read_blocks on start of write
        self._write_blocks = []
        self._external_write_blocks = []
        self._streamed_block = None
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

    def make_write_block(self, data, options):
        if options.storage_type == "external":
            for index, blk in enumerate(self._external_write_blocks):
                if blk._data is data:
                    # this external uri is already ready to go
                    return blk._uri
            # need to set up new external block
            index = len(self._external_write_blocks)
            blk = WriteBlock(data, options.compression, options.compression_kwargs)
            blk._uri = make_external_uri(self._write_fd.uri, index)
            self._external_write_blocks.append(blk)
            return blk._uri
        # first, look for an existing block
        for index, blk in enumerate(self._write_blocks):
            if blk._data is data:
                return index
        # if no block is found, make a new block
        self._write_blocks.append(WriteBlock(data, options.compression, options.compression_kwargs))
        # data_bytes = np.ndarray(-1, np.uint8, data.ravel(order='K').data)
        # self._write_blocks.append(WriteBlock(data_bytes, options.compression, options.compression_kwargs))
        return len(self._write_blocks) - 1

    def set_streamed_block(self, data):
        if self._streamed_block is not None and data is not self._streamed_block.data:
            raise ValueError("Can not add second streaming block")
        self._streamed_block = WriteBlock(data)

    # cludges for tests
    @property
    def internal_blocks(self):
        return self.blocks

    @property
    def _internal_blocks(self):
        return self.blocks

    def set_array_storage(self, data, storage):
        options = self.options.get_options(data)
        options.storage_type = storage
        self.options.set_options(data, options)

    def __len__(self):
        return len(self.blocks)
