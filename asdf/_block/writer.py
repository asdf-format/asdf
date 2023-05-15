import numpy as np

from asdf import constants

from . import io as bio


class WriteBlock:
    """
    Data and compression options needed to write and ASDF block.
    """

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
    """
    Write a list of WriteBlocks to a file

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to write to. Writing will start at the current position.

    blocks : list of WriteBlock
        List of WriteBlock instances used to get the data and options
        to write to each ASDF block.

    padding : bool or float, optional, default False
        If False, add no padding bytes between blocks. If True
        add some default amount of padding. If a float, add
        a number of padding bytes based off a ratio of the data
        size.
        See ``asdf._block.io.write_block`` ``padding`` argument for
        more details.

    streamed_block : WriteBlock, optional
        If provided (not None) include this WriteBlock as
        the final block in the file and mark it as a streamed
        block.

    write_index : bool, optional, default True
        If True, include a block index at the end of the file.
        If a streamed_block is provided (or the file is not
        seekable) no block index will be written.

    Returns
    -------
    offsets : list of int
        Byte offsets (from the start of the file) where each
        block was written (this is the start of the block magic
        bytes for each block). This list includes the offset of
        the streamed_block if it was provided.
        If the file written to is not seekable these offsets
        will all be None.

    headers : list of dict
        Headers written for each block (including the streamed_block
        if it was provided).
    """
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
