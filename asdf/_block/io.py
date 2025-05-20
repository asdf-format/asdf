"""
Low-level functions for reading and writing ASDF blocks
and other block related file contents (like the block index).
"""

import hashlib
import io
import os
import struct
import weakref

import yaml

from asdf import _compression as mcompression
from asdf import constants, util
from asdf.versioning import _yaml_base_loader as BaseLoader

from .exceptions import BlockIndexError

BLOCK_HEADER = util._BinaryStruct(
    [
        ("flags", "I"),
        ("compression", "4s"),
        ("allocated_size", "Q"),
        ("used_size", "Q"),
        ("data_size", "Q"),
        ("checksum", "16s"),
    ],
)


def calculate_block_checksum(data):
    if data.ndim > 1:
        data = data.ravel(order="K")
    # The following line is safe because we're only using
    # the MD5 as a checksum.
    m = hashlib.new("md5", usedforsecurity=False)
    m.update(data)
    return m.digest()


def validate_block_header(header):
    """
    Check that they key value pairs in header contain consistent
    information about the ASDF block ``compression``, ``flags``,
    ``used_size`` and ``data_size`` (otherwise raise an exception).

    Parameters
    ----------
    header : dict
        ASDF block header information.

    Raises
    ------
    ValueError
        If the key value pairs in header contain inconsistent information
    """
    compression = mcompression.validate(header["compression"])
    if header["flags"] & constants.BLOCK_FLAG_STREAMED:
        if compression is not None:
            msg = "Compression set on a streamed block."
            raise ValueError(msg)
    else:
        if compression is None and header["used_size"] != header["data_size"]:
            msg = "used_size and data_size must be equal when no compression is used."
            raise ValueError(msg)
    return header


def read_block_header(fd, offset=None):
    """
    Read an ASDF block header

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to read.

    offset : int, optional
        Offset within the file where the start of the ASDF block
        header is located. If provided, the file will be seeked prior
        to reading.

    Returns
    -------
    header : dict
        Dictionary containing the read ASDF header as parsed by the
        `BLOCK_HEADER` `asdf.util._BinaryStruct`.

    Raises
    ------
    ValueError
        If the read header is inconsistent (see `validate_block_header`).
    """
    if offset is not None:
        fd.seek(offset)

    # read the header size
    buff = fd.read(2)
    header_size = struct.unpack(b">H", buff)[0]
    if header_size < BLOCK_HEADER.size:
        msg = f"Header size must be >= {BLOCK_HEADER.size}"
        raise ValueError(msg)

    header = BLOCK_HEADER.unpack(fd.read(header_size))
    return validate_block_header(header)


def read_block_data(fd, header, offset=None, memmap=False):
    """
    Read (or memory map) data for an ASDF block.

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to read.

    header : dict
        ASDF block header dictionary (as read from `read_block_header`).

    offset : int, optional
        Offset within the file where the start of the ASDF block data
        is located. If provided, the file will be seeked prior to reading.

    memmap : bool, optional, default False
        Memory map the block data using `generic_io.GenericIO.memmap_array`.
        A compressed block will never be memmapped and if the file ``fd``
        does not support memmapping the data will not be memmapped (and
        no error will be raised).

    Returns
    -------
    data : ndarray or memmap
        A one-dimensional ndarray of dtype uint8
    """

    if fd.seekable():
        if offset is not None:
            fd.seek(offset)
        else:
            offset = fd.tell()

    if header["flags"] & constants.BLOCK_FLAG_STREAMED:
        used_size = -1
    else:
        used_size = header["used_size"]

    # if no compression, just read data
    compression = mcompression.validate(header["compression"])
    if compression:
        # compressed data will not be memmapped
        data = mcompression.decompress(fd, used_size, header["data_size"], compression)
        fd.fast_forward(header["allocated_size"] - header["used_size"])
    else:
        if memmap and fd.can_memmap():
            data = fd.memmap_array(offset, used_size)
            ff_bytes = header["allocated_size"]
        else:
            data = fd.read_into_array(used_size)
            ff_bytes = header["allocated_size"] - header["used_size"]
        if (header["flags"] & constants.BLOCK_FLAG_STREAMED) and fd.seekable():
            fd.seek(0, os.SEEK_END)
        else:
            fd.fast_forward(ff_bytes)
    return data


def read_block(fd, offset=None, memmap=False, lazy_load=False):
    """
    Read a block (header and data) from an ASDF file.

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to read.

    offset : int, optional
        Offset within the file where the start of the ASDF block header
        is located. If provided, the file will be seeked prior to reading.
        Note this is the start of the block header not the start of the
        block magic.

    memmap : bool, optional, default False
        Memory map the block data see `read_block_data` for more
        details.

    lazy_load : bool, optional, default False
        Return a callable that when called will read the block data. This
        option is ignored for a non-seekable file.

    Returns
    -------
    offset : int
        The offset within the file where the block was read (equal to offset
        argument if it was provided).

    header : dict
        ASDF block header as read with `read_block_header`.

    data_offset : int
        The offset within the file where the block data begins.

    data : ndarray, memmap or callable
        ASDF block data (one-dimensional ndarray of dtype uint8). If lazy_load
        (and the file is seekable) data will be a callable that when executed
        will seek the file and read the block data.
    """
    # expects the fd or offset is past the block magic
    if offset is None and fd.seekable():
        offset = fd.tell()
    header = read_block_header(fd, offset)
    if fd.seekable():
        data_offset = fd.tell()
    else:
        data_offset = None
    if lazy_load and fd.seekable():
        # setup a callback to later load the data
        fd_ref = weakref.ref(fd)

        def callback():
            fd = fd_ref()
            if fd is None or fd.is_closed():
                msg = "ASDF file has already been closed. Can not get the data."
                raise OSError(msg)
            position = fd.tell()
            data = read_block_data(fd, header, offset=data_offset, memmap=memmap)
            fd.seek(position)
            return data

        data = callback
        if header["flags"] & constants.BLOCK_FLAG_STREAMED:
            fd.seek(0, os.SEEK_END)
        else:
            fd.fast_forward(header["allocated_size"])
    else:
        data = read_block_data(fd, header, offset=None, memmap=memmap)
    return offset, header, data_offset, data


def generate_write_header(data, stream=False, compression_kwargs=None, padding=False, fs_block_size=1, **header_kwargs):
    """
    Generate a dict representation of a ASDF block header that can be
    used for writing a block.

    Note that if a compression key is provided in ``header_kwargs`` this
    function will compress ``data`` to determine the used_size (the
    compressed data will be returned via the ``buff`` result to avoid
    needing to re-compress the data before writing).

    Parameters
    ----------

    data : ndarray
        A one-dimensional ndarray of dtype uint8.

    stream : bool, optional, default False
        If True, generate a header for a streamed block.

    compression_kwargs : dict, optional
        If provided, these will be passed on to `asdf.compression.compress`
        if the data is compressed (see header_kwargs).

    padding : bool or float, optional, default False
        If the block should contain additional padding bytes. See the
        `asdf.util.calculate_padding` argument ``pad_blocks`` for more
        details.

    fs_block_size : int, optional, default 1
        The filesystem block size. See the `asdf.util.calculate_padding`
        ``block_size`` argument for more details.

    **header_kwargs : dict, optional
        Block header settings that will be read, updated, and used
        to generate the binary block header representation by packing
        with `BLOCK_HEADER`.

    Returns
    -------

    header : dict
        Dictionary representation of an ASDF block header.

    buff : bytes or None
        If this block is compressed buff will contained the compressed
        representation of data or None if the data is uncompressed.

    padding_bytes: int
        The number of padding bytes that must be written after
        the block data.
    """
    if data.ndim != 1 or data.dtype != "uint8":
        msg = "Data must be of ndim==1 and dtype==uint8"
        raise ValueError(msg)
    if stream:
        header_kwargs["flags"] = header_kwargs.get("flags", 0) | constants.BLOCK_FLAG_STREAMED
        header_kwargs["data_size"] = 0
        header_kwargs["checksum"] = b"\0" * 16
    else:
        header_kwargs["flags"] = 0
        header_kwargs["data_size"] = data.nbytes
        header_kwargs["checksum"] = calculate_block_checksum(data)

    header_kwargs["compression"] = mcompression.to_compression_header(header_kwargs.get("compression", None))

    if header_kwargs["compression"] == b"\0\0\0\0":
        used_size = header_kwargs["data_size"]
        buff = None
    else:
        buff = io.BytesIO()
        mcompression.compress(buff, data, header_kwargs["compression"], config=compression_kwargs)
        used_size = buff.tell()
    if stream:
        header_kwargs["used_size"] = 0
        header_kwargs["allocated_size"] = 0
    else:
        header_kwargs["used_size"] = used_size
        padding = util.calculate_padding(used_size, padding, fs_block_size)
        header_kwargs["allocated_size"] = header_kwargs.get("allocated_size", used_size + padding)

    if header_kwargs["allocated_size"] < header_kwargs["used_size"]:
        msg = (
            f"Block used size {header_kwargs['used_size']} larger than "
            f"allocated size {header_kwargs['allocated_size']}",
        )
        raise RuntimeError(msg)
    padding_bytes = header_kwargs["allocated_size"] - header_kwargs["used_size"]
    return header_kwargs, buff, padding_bytes


def write_block(fd, data, offset=None, stream=False, compression_kwargs=None, padding=False, **header_kwargs):
    """
    Write an ASDF block.

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to write to.

    offset : int, optional
        If provided, seek to this offset before writing.

    stream : bool, optional, default False
        If True, write this as a streamed block.

    compression_kwargs : dict, optional
        If block is compressed, use these additional arguments during
        compression. See `generate_write_header`.

    padding : bool, optional, default False
        Optionally pad the block data. See `generate_write_header`.

    **header_kwargs : dict
        Block header settings. See `generate_write_header`.

    Returns
    -------

    header : dict
        The ASDF block header as unpacked from the `BLOCK_HEADER` used
        for writing.
    """
    header_dict, buff, padding_bytes = generate_write_header(
        data, stream, compression_kwargs, padding, fd.block_size, **header_kwargs
    )
    header_bytes = BLOCK_HEADER.pack(**header_dict)

    if offset is not None:
        if fd.seekable():
            fd.seek(offset)
        else:
            msg = "write_block received offset for non-seekable file"
            raise ValueError(msg)
    fd.write(struct.pack(b">H", len(header_bytes)))
    fd.write(header_bytes)
    if buff is None:  # data is uncompressed
        fd.write_array(data)
    else:
        fd.write(buff.getvalue())
    fd.fast_forward(padding_bytes)
    return header_dict


def _candidate_offsets(min_offset, max_offset, block_size):
    offset = (max_offset // block_size) * block_size
    if offset == max_offset:
        offset -= block_size
    while offset > min_offset:
        yield offset
        offset -= block_size
    if offset <= min_offset:
        yield min_offset


def find_block_index(fd, min_offset=None, max_offset=None):
    """
    Find the location of an ASDF block index within a seekable file.

    Searching will begin at the end of the file (or max_offset
    if it is provided).

    Parameters
    ----------

    fd : file or generic_io.GenericIO
        A seekable file that will be searched to try and find
        the start of an ASDF block index within the file.

    min_offset : int, optional
        The minimum search offset. A block index will not be
        found before this point.

    max_offset : int, optional
        The maximum search offset. A block index will not be
        found after this point.

    Returns
    -------

    offset : int or None
        Index of start of ASDF block index. This is the location of the
        ASDF block index header.

    """
    if min_offset is None:
        min_offset = fd.tell()
    if max_offset is None:
        fd.seek(0, os.SEEK_END)
        max_offset = fd.tell()
    block_size = fd.block_size
    block_index_offset = None
    buff = b""
    pattern = constants.INDEX_HEADER
    for offset in _candidate_offsets(min_offset, max_offset, block_size):
        fd.seek(offset)
        buff = fd.read(block_size) + buff
        index = buff.find(pattern)
        if index != -1:
            block_index_offset = offset + index
            if block_index_offset >= max_offset:
                return None
            break
        buff = buff[: len(pattern)]
    return block_index_offset


def read_block_index(fd, offset=None):
    """
    Read an ASDF block index from a file.

    Parameters
    ----------

    fd : file or generic_io.GenericIO
        File to read the block index from.

    offset : int, optional
        Offset within the file where the block index starts
        (the start of the ASDF block index header). If not provided
        reading will start at the current position of the file
        pointer. See `find_block_index` to locate the block
        index prior to calling this function.

    Returns
    -------

    block_index : list of ints
        A list of ASDF block offsets read and parsed from the
        block index.

    Raises
    ------
    BlockIndexError
        The data read from the file did not contain a valid
        block index.
    """
    if offset is not None:
        fd.seek(offset)
    buff = fd.read(len(constants.INDEX_HEADER))
    if buff != constants.INDEX_HEADER:
        msg = "Failed to read block index header at offset {offset}"
        raise BlockIndexError(msg)
    try:
        # the noqa is needed here since the linter doesn't know
        # that BaseLoader here is either SafeLoader or CSafeLoader
        # both of which do not violate S506.
        block_index = yaml.load(fd.read(-1), BaseLoader)  # noqa: S506
    except yaml.error.YAMLError:
        raise BlockIndexError("Failed to parse block index as yaml")
    if (
        not isinstance(block_index, list)
        or any(not isinstance(v, int) for v in block_index)
        or block_index != sorted(block_index)
    ):
        raise BlockIndexError("Invalid block index")
    return block_index


def write_block_index(fd, offsets, offset=None, yaml_version=None):
    """
    Write a list of ASDF block offsets to a file in the form
    of an ASDF block index.

    Parameters
    ----------
    fd : file or generic_io.GenericIO
        File to write to.

    offsets : list of ints
        List of byte offsets (from the start of the file) where
        ASDF blocks are located.

    offset : int, optional
        If provided, seek to this offset before writing.

    yaml_version : tuple, optional, default (1, 1)
        YAML version to use when writing the block index. This
        will be passed to ``yaml.dump`` as the version argument.
    """
    if yaml_version is None:
        yaml_version = (1, 1)
    if offset is not None:
        fd.seek(offset)
    fd.write(constants.INDEX_HEADER)
    fd.write(b"\n")
    yaml.dump(
        offsets,
        stream=fd,
        Dumper=yaml.SafeDumper,
        explicit_start=True,
        explicit_end=True,
        allow_unicode=True,
        encoding="utf-8",
        version=yaml_version,
    )
