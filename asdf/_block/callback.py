import weakref


class DataCallback:
    def __init__(self, index, read_blocks):
        self.reassign(index, read_blocks)

    def __call__(self, _attr=None):
        read_blocks = self._read_blocks_ref()
        if read_blocks is None:
            msg = "Attempt to read block data from missing block"
            raise OSError(msg)
        if _attr is None:
            return read_blocks[self._index].data
        else:
            # _attr allows NDArrayType to have low level block access for things
            # like reading the header and cached_data
            return getattr(read_blocks[self._index], _attr)

    def reassign(self, index, read_blocks):
        self._index = index
        self._read_blocks_ref = weakref.ref(read_blocks)
