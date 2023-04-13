from asdf import constants

from . import io as bio


class WriteBlock:
    def __init__(self, data, compression=None, compression_kwargs=None):
        self._data = data
        self.compression = compression
        self.compression_kwargs = compression_kwargs

    @property
    def data(self):
        if callable(self._data):
            return self._data()
        return self._data


def write_blocks(fd, blocks, padding=False, streamed_block=None, write_index=True):
    offsets = []
    headers = []
    for blk in blocks:
        offsets.append(fd.tell())
        fd.write(constants.BLOCK_MAGIC)
        headers.append(
            bio.write_block(
                fd,
                blk.data,
                compression_kwargs=blk.compression_kwargs,
                padding=padding,
                compression=blk.compression,
            )
        )
    if streamed_block is not None:
        offsets.append(fd.tell())
        fd.write(constants.BLOCK_MAGIC)
        headers.append(bio.write_block(fd, streamed_block.data, stream=True))
    elif len(blocks) and write_index:
        bio.write_block_index(fd, offsets)
    return offsets, headers
