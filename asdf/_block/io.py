import hashlib
import io
import os
import struct
import weakref

import yaml

from asdf import compression as mcompression
from asdf import constants, util

BLOCK_HEADER = util.BinaryStruct(
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
    m = hashlib.new("md5")  # noqa: S324
    m.update(data)
    return m.digest()


def validate_block_header(header):
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
    if fd.seekable():
        if offset is not None:
            fd.seek(offset)
        else:
            offset = fd.tell()

    # load and possibly decompress the data
    # read the raw bytes
    if header["flags"] & constants.BLOCK_FLAG_STREAMED:
        used_size = -1
    else:
        used_size = header["used_size"]

    # if no compression, just read data
    compression = mcompression.validate(header["compression"])
    if compression:
        # the old code ignored memmapping for compressed data
        data = mcompression.decompress(fd, used_size, header["data_size"], compression)
        fd.fast_forward(header["allocated_size"] - header["used_size"])
    else:
        if memmap and fd.can_memmap():
            data = fd.memmap_array(offset, used_size)
            fd.fast_forward(header["allocated_size"])
        else:
            data = fd.read_into_array(used_size)
            fd.fast_forward(header["allocated_size"] - header["used_size"])
        if (header["flags"] & constants.BLOCK_FLAG_STREAMED) and fd.seekable():
            fd.seek(0, os.SEEK_END)
    return data


def read_block(fd, offset=None, memmap=False, lazy_load=False):
    # expects the fd or offset is past the block magic
    if offset is None and fd.seekable():
        offset = fd.tell()
    header = read_block_header(fd, offset)
    data_offset = fd.tell()
    if lazy_load and fd.seekable():
        # setup a callback to later load the data
        fd_ref = weakref.ref(fd)

        def callback():
            fd = fd_ref()
            if fd is None or fd.is_closed():
                msg = "Attempt to read data from closed file"
                raise OSError(msg)
            return read_block_data(fd, header, offset=data_offset, memmap=memmap)

        data = callback
        fd.fast_forward(header["allocated_size"])
    else:
        data = read_block_data(fd, header, offset=None, memmap=memmap)
    return offset, header, data_offset, data


def validate_write_data(data):
    if data.ndim != 1 or data.dtype != "uint8":
        msg = "Data must be of ndim==1 and dtype==uint8"
        raise ValueError(msg)


def generate_write_header(fd, data, stream=False, compression_kwargs=None, padding=False, **header_kwargs):
    validate_write_data(data)
    if stream:
        header_kwargs["flags"] = header_kwargs.get("flags", 0) | constants.BLOCK_FLAG_STREAMED
        header_kwargs["data_size"] = 0
        header_kwargs["checksum"] = b"\0" * 16
    else:
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
        padding = util.calculate_padding(used_size, padding, fd.block_size)
        header_kwargs["allocated_size"] = header_kwargs.get("allocated_size", used_size + padding)

    if header_kwargs["allocated_size"] < header_kwargs["used_size"]:
        msg = (
            f"Block used size {header_kwargs['used_size']} larger than "
            f"allocated size {header_kwargs['allocated_size']}",
        )
        raise RuntimeError(msg)
    header = BLOCK_HEADER.pack(**header_kwargs)
    padding_bytes = header_kwargs["allocated_size"] - header_kwargs["used_size"]
    return header, buff, padding_bytes


def write_block(fd, data, offset=None, stream=False, compression_kwargs=None, padding=False, **header_kwargs):
    # TODO fd is only used for padding calculation, bring this out
    header, buff, padding_bytes = generate_write_header(fd, data, stream, compression_kwargs, padding, **header_kwargs)

    if offset is not None:
        if fd.seekable():
            fd.seek(offset)
        else:
            msg = "write_block received offset for non-seekable file"
            raise ValueError(msg)
    fd.write(struct.pack(b">H", len(header)))
    fd.write(header)
    if buff is None:  # data is uncompressed
        fd.write_array(data)
    else:
        fd.write(buff.getvalue())
    fd.fast_forward(padding_bytes)
    return BLOCK_HEADER.unpack(header)


def candidate_offsets(min_offset, max_offset, block_size):
    offset = (max_offset // block_size) * block_size
    if offset == max_offset:
        # don't include the max_offset
        offset -= block_size
    while offset > min_offset:
        yield offset
        offset -= block_size
    if offset <= min_offset:
        yield min_offset


def find_block_index(fd, min_offset=None, max_offset=None):
    if min_offset is None:
        min_offset = fd.tell()
    if max_offset is None:
        fd.seek(0, os.SEEK_END)
        max_offset = fd.tell()
    block_size = fd.block_size
    block_index_offset = None
    buff = b""
    pattern = constants.INDEX_HEADER
    for offset in candidate_offsets(min_offset, max_offset, block_size):
        fd.seek(offset)
        buff = fd.read(block_size) + buff
        index = buff.find(pattern)
        if index != -1:
            block_index_offset = offset + index
            if block_index_offset >= max_offset:
                return None
            break
        buff = buff[: len(pattern)]
    if block_index_offset is not None and block_index_offset < max_offset:
        return block_index_offset
    return None


def read_block_index(fd, offset=None):
    if offset is not None:
        fd.seek(offset)
    buff = fd.read(len(constants.INDEX_HEADER))
    if buff != constants.INDEX_HEADER:
        msg = "Failed to read block index header at offset {offset}"
        raise OSError(msg)
    try:
        block_index = yaml.load(fd.read(-1), yaml.SafeLoader)
    except yaml.parser.ParserError:
        raise OSError("Failed to parse block index as yaml")
    if (
        not isinstance(block_index, list)
        or any(not isinstance(v, int) for v in block_index)
        or block_index != sorted(block_index)
    ):
        raise OSError("Invalid block index")
    return block_index


def write_block_index(fd, offsets, offset=None, yaml_version=None):
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
