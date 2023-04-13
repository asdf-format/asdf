import weakref

from asdf import constants

from . import io as bio


class ReadBlock:
    def __init__(self, offset, fd, memmap, lazy_load, header=None, data_offset=None, data=None):
        self.offset = offset
        self._fd = weakref.ref(fd)
        self.header = header
        self.data_offset = data_offset
        self._data = data
        # TODO alternative to passing these down?
        self.memmap = memmap
        self.lazy_load = lazy_load
        if not lazy_load:
            self.load()

    @property
    def loaded(self):
        return self._data is not None

    def load(self):
        if self.loaded:
            return
        fd = self._fd()
        if fd is None or fd.is_closed():
            raise OSError("Attempt to load block from closed file")
        _, self.header, self.data_offset, self._data = bio.read_block(
            fd, offset=self.offset, memmap=self.memmap, lazy_load=self.lazy_load
        )

    @property
    def data(self):
        if not self.loaded:
            self.load()
        if callable(self._data):
            return self._data()
        return self._data

    def reset(self, fd, offset):
        self._fd = weakref.ref(fd)
        self.offset = offset
        self.header = None
        self.data_offset = None
        self._data = None
        if not self.lazy_load:
            self.load()


def read_blocks_serially(fd, memmap=False, lazy_load=False):
    blocks = []
    buff = b""
    while True:
        # the expectation is that this will begin PRIOR to the block magic
        # read 4 bytes
        buff += fd.read(4 - len(buff))
        if len(buff) < 4:
            # we are done, there are no more blocks and no index
            # TODO error? we shouldn't have extra bytes, the old code allows this
            break

        if buff == constants.INDEX_HEADER[:4]:
            # we hit the block index, which is not useful here
            break

        if buff == constants.BLOCK_MAGIC:
            # this is another block
            offset, header, data_offset, data = bio.read_block(fd, memmap=memmap, lazy_load=lazy_load)
            blocks.append(ReadBlock(offset, fd, memmap, lazy_load, header=header, data_offset=data_offset, data=data))
            if blocks[-1].header["flags"] & constants.BLOCK_FLAG_STREAMED:
                # a file can only have 1 streamed block and it must be at the end so we
                # can stop looking for more blocks
                break
            buff = b""
        else:
            if len(blocks) or buff[0] != 0:
                # if this is not the first block or we haven't found any
                # blocks and the first byte is non-zero
                msg = f"Invalid bytes while reading blocks {buff}"
                raise OSError(msg)
            # this is the first block, allow empty bytes before block
            buff = buff.strip(b"\0")
    return blocks


def read_blocks(fd, memmap=False, lazy_load=False):
    if not lazy_load or not fd.seekable():
        # load all blocks serially
        return read_blocks_serially(fd, memmap, lazy_load)

    # try to find block index
    starting_offset = fd.tell()
    index_offset = bio.find_block_index(fd, starting_offset)
    if index_offset is None:
        # if failed, load all blocks serially
        fd.seek(starting_offset)
        return read_blocks_serially(fd, memmap, lazy_load)

    # setup empty blocks
    block_index = bio.read_block_index(fd, index_offset)
    # skip magic for each block
    blocks = [ReadBlock(offset + 4, fd, memmap, lazy_load) for offset in block_index]
    try:
        # load first and last blocks to check if the index looks correct
        for index in (0, -1):
            fd.seek(block_index[index])
            buff = fd.read(4)
            if buff != constants.BLOCK_MAGIC:
                raise OSError("Invalid block magic")
            blocks[index].load()
    except (OSError, ValueError):
        fd.seek(starting_offset)
        return read_blocks_serially(fd, memmap, lazy_load)
    return blocks
