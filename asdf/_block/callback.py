"""
A `DataCallback` class is implemented here to allow
for reassignment of the index of an ASDF block corresponding
to a callback.

This is needed so that extension code can generate a callback
during deserialization of an ASDF file that will continue
to be valid even after an `AsdfFile.update` which might
reorder blocks.

To allow for 'low-level' block access needed for ndarray
`DataCallback` can be called with an optional ``_attr``
argument to cache data, access the block header and other
operations that we generally do not want to expose to
extension code.
"""

import weakref


class DataCallback:
    """
    A callable object used to read data from an ASDF block
    read from an ASDF file.
    """

    def __init__(self, index, read_blocks):
        self._reassign(index, read_blocks)

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

    def _reassign(self, index, read_blocks):
        self._index = index
        self._read_blocks_ref = weakref.ref(read_blocks)
