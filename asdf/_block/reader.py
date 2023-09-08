import warnings
import weakref

from asdf import constants
from asdf.exceptions import AsdfBlockIndexWarning, AsdfWarning

from . import io as bio
from .exceptions import BlockIndexError


class ReadBlock:
    """
    Represents an ASDF block read from a file.
    """

    def __init__(self, offset, fd, memmap, lazy_load, validate_checksum, header=None, data_offset=None, data=None):
        self.offset = offset  # after block magic bytes
        self._fd = weakref.ref(fd)
        self._header = header
        self.data_offset = data_offset
        self._data = data
        self._cached_data = None
        self.memmap = memmap
        self.lazy_load = lazy_load
        self.validate_checksum = validate_checksum
        if not lazy_load:
            self.load()

    def close(self):
        self._cached_data = None

    @property
    def loaded(self):
        return self._data is not None

    def load(self):
        """
        Load the block data (if it is not already loaded).

        Raises
        ------
        OSError
            If attempting to load from a closed file.
        """
        if self.loaded:
            return
        fd = self._fd()
        if fd is None or fd.is_closed():
            msg = "Attempt to load block from closed file"
            raise OSError(msg)
        position = fd.tell()
        _, self._header, self.data_offset, self._data = bio.read_block(
            fd, offset=self.offset, memmap=self.memmap, lazy_load=self.lazy_load
        )
        fd.seek(position)

    @property
    def data(self):
        """
        Read, parse and return data for an ASDF block.

        Returns
        -------
        data : ndarray
            A one-dimensional ndarray of dypte uint8 read from an ASDF block

        Raises
        ------
        ValueError
            If the header checksum does not match the checksum of the data
            and validate_checksums was set to True.
        """
        if not self.loaded:
            self.load()
        if callable(self._data):
            data = self._data()
        else:
            data = self._data
        if self.validate_checksum:
            checksum = bio.calculate_block_checksum(data)
            if not self._header["flags"] & constants.BLOCK_FLAG_STREAMED and checksum != self._header["checksum"]:
                msg = f"Block at {self.offset} does not match given checksum"
                raise ValueError(msg)
            # only validate data the first time it's read
            self.validate_checksum = False
        return data

    @property
    def cached_data(self):
        """
        Return cached data for an ASDF block.

        The first time this is called it may read data from the file
        (if lazy loaded). Subsequent calls will return the same
        ndarray.
        """
        if self._cached_data is None:
            self._cached_data = self.data
        return self._cached_data

    @property
    def header(self):
        """
        Get the block header. For a lazy loaded block the first time
        this is called the header will be read from the file and
        cached.

        Returns
        -------
        header : dict
            Dictionary containing the read ASDF header.
        """
        if not self.loaded:
            self.load()
        return self._header


def _read_blocks_serially(fd, memmap=False, lazy_load=False, validate_checksums=False, after_magic=False):
    """
    Read blocks serially from a file without looking for a block index.

    For parameter and return value descriptions see `read_blocks`.
    """
    blocks = []
    buff = b""
    magic_len = len(constants.BLOCK_MAGIC)
    while True:
        # the expectation is that this will begin PRIOR to the block magic
        # read 4 bytes
        if not after_magic:
            buff += fd.read(magic_len - len(buff))
            if len(buff) == 0:
                # we are done, there are no more blocks and no index
                break
            elif len(buff) < magic_len:
                # we have less than magic_len bytes, this is likely an error
                # in the input file/bytes
                if all([b == 0 for b in buff]):
                    # if these are all 0, assume this was a 'truncated' file
                    # so don't issue a warning
                    break
                # if these are non-0 bytes issue a warning that the file
                # is likely corrupt
                msg = f"Read invalid bytes {buff!r} after blocks, your file might be corrupt"
                warnings.warn(msg, AsdfWarning)
                break

        if buff == constants.INDEX_HEADER[:magic_len]:
            # we hit the block index, which is not useful here
            break

        if after_magic or buff == constants.BLOCK_MAGIC:
            # this is another block
            offset, header, data_offset, data = bio.read_block(fd, memmap=memmap, lazy_load=lazy_load)
            blocks.append(
                ReadBlock(
                    offset, fd, memmap, lazy_load, validate_checksums, header=header, data_offset=data_offset, data=data
                )
            )
            if blocks[-1].header["flags"] & constants.BLOCK_FLAG_STREAMED:
                # a file can only have 1 streamed block and it must be at the end so we
                # can stop looking for more blocks
                break
            buff = b""
            after_magic = False
        else:
            if len(blocks) or buff[0] != 0:
                # if this is not the first block or we haven't found any
                # blocks and the first byte is non-zero
                msg = f"Invalid bytes while reading blocks {buff}"
                raise OSError(msg)
            # this is the first block, allow empty bytes before block
            buff = buff.strip(b"\0")
    return blocks


def read_blocks(fd, memmap=False, lazy_load=False, validate_checksums=False, after_magic=False):
    """
    Read a sequence of ASDF blocks from a file.

    If the file is seekable (and lazy_load is False) an attempt will
    made to find, read and parse a block index. If this fails, the
    blocks will be read serially. If parsing the block index
    succeeds, the first first and last blocks will be read (to
    confirm that those portions of the index are correct). All
    other blocks will not be read until they are accessed.

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to read. Reading will start at the current position.

    memmap : bool, optional, default False
        If true, memory map block data.

    lazy_load : bool, optional, default False
        If true, block data will be a callable that when executed
        will return the block data. See the ``lazy_load`` argument
        to ``asdf._block.io.read_block`` for more details.

    validate_checksums : bool, optional, default False
        When reading blocks compute the block data checksum and
        compare it to the checksum read from the block header.
        Note that this comparison will occur when the data is
        accessed if ``lazy_load`` was set to True.

    after_magic : bool, optional, default False
        If True don't expect block magic bytes for the first block
        read from the file.

    Returns
    -------

    read_blocks : list of ReadBlock
        A list of ReadBlock instances.

    Raises
    ------
    OSError
        Invalid bytes encountered while reading blocks.

    ValueError
        A read block has an invalid checksum.
    """
    if not lazy_load or not fd.seekable():
        # load all blocks serially
        return _read_blocks_serially(fd, memmap, lazy_load, validate_checksums, after_magic)

    # try to find block index
    starting_offset = fd.tell()
    index_offset = bio.find_block_index(fd, starting_offset)
    if index_offset is None:
        # if failed, load all blocks serially
        fd.seek(starting_offset)
        return _read_blocks_serially(fd, memmap, lazy_load, validate_checksums, after_magic)

    # setup empty blocks
    try:
        block_index = bio.read_block_index(fd, index_offset)
    except BlockIndexError as e:
        # failed to read block index, fall back to serial reading
        msg = f"Failed to read block index, falling back to serial reading: {e!s}"
        warnings.warn(msg, AsdfBlockIndexWarning)
        fd.seek(starting_offset)
        return _read_blocks_serially(fd, memmap, lazy_load, validate_checksums, after_magic)
    # skip magic for each block
    magic_len = len(constants.BLOCK_MAGIC)
    blocks = [ReadBlock(offset + magic_len, fd, memmap, lazy_load, validate_checksums) for offset in block_index]
    try:
        # load first and last blocks to check if the index looks correct
        for index in (0, -1):
            fd.seek(block_index[index])
            buff = fd.read(magic_len)
            if buff != constants.BLOCK_MAGIC:
                msg = "Invalid block magic"
                raise OSError(msg)
            blocks[index].load()
    except (OSError, ValueError) as e:
        msg = f"Invalid block index contents for block {index}, falling back to serial reading: {e!s}"
        warnings.warn(msg, AsdfBlockIndexWarning)
        fd.seek(starting_offset)
        return _read_blocks_serially(fd, memmap, lazy_load, after_magic)
    return blocks
