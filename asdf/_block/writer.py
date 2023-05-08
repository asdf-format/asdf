import numpy as np

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

    @property
    def data_bytes(self):
        data = self.data
        if data is not None:
            return np.ndarray(-1, np.uint8, data.ravel(order="K").data)
        return np.ndarray(0, np.uint8)


def write_blocks(fd, blocks, padding=False, streamed_block=None, write_index=True):
    offsets = []
    headers = []
    for blk in blocks:
        if fd.seekable():
            offset = fd.tell()
        else:
            offset = None
        offsets.append(offset)
        fd.write(constants.BLOCK_MAGIC)
        headers.append(
            bio.write_block(
                fd,
                blk.data_bytes,
                compression_kwargs=blk.compression_kwargs,
                padding=padding,
                compression=blk.compression,
            )
        )
    if streamed_block is not None:
        if fd.seekable():
            offset = fd.tell()
        else:
            offset = None
        offsets.append(offset)
        fd.write(constants.BLOCK_MAGIC)
        headers.append(bio.write_block(fd, streamed_block.data_bytes, stream=True))
    elif len(offsets) and write_index and fd.seekable():
        bio.write_block_index(fd, offsets)
    return offsets, headers
