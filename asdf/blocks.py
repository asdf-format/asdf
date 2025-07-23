import math
import sys
from collections.abc import Sequence
from types import MappingProxyType

from asdf.constants import BLOCK_FLAG_STREAMED

__all__ = ["BlockView", "BlockViewer"]


class BlockView:
    """
    A read-only view of an ASDF block.
    """

    def __init__(self, read_block):
        self._read_block = read_block

    @property
    def header(self):
        """
        MappingProxy: A read-only mapping of ASDF block header contents.
        """
        return MappingProxyType(self._read_block.header)

    @property
    def offset(self):
        """
        int: The offset (in bytes) of the ASDF block from the start of the file.
        """
        return self._read_block.offset

    @property
    def data_offset(self):
        """
        int: The offset (in bytes) of the ASDF block data from the start of the file.
        """
        return self._read_block.data_offset

    @property
    def loaded(self):
        """
        bool: True if the ASDF block data has been loaded (and cached).
        """
        return self._read_block._cached_data is not None

    def load(self, out=None):
        if out is not None:
            raise NotImplementedError("Reading into an array is not yet supported")
        return self._read_block.cached_data

    def _info(self):
        header = self.header
        if header["flags"] & BLOCK_FLAG_STREAMED:
            return "Stream"
        line = f"{header['allocated_size']} bytes"
        if header["allocated_size"] != header["used_size"]:
            line += f", {header['used_size']} used"
        if header["compression"] != b"\0\0\0\0":
            line += f", {header['compression'].decode('ascii')} compression"
        return line


class BlockViewer(Sequence):
    """
    A read-only sequence of `BlockView` objects.
    """

    def __init__(self, manager):
        self._manager = manager

    def __len__(self):
        return len(self._manager.blocks)

    def __getitem__(self, index):
        return BlockView(self._manager.blocks[index])

    def _info(self):
        n = len(self)
        if not n:
            return []

        # conditionally use tty bold formatting:w
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():

            def bold(s):
                return f"\x1b[1m{s}\x1b[0m"

        else:

            def bold(s):
                return s

        index_string_length = int(math.log10(n)) + 1
        lines = []
        for i, block in enumerate(self):
            index_string = str(i).rjust(index_string_length)
            prefix = bold(f"█ Block {index_string}")
            lines.append(f"{prefix}: {block._info()}")
        return lines

    def info(self):
        """
        Print a rendering of these blocks to stdout.
        """
        print("\n".join(self._info()))
