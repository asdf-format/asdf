import io
import mmap

import numpy as np
import pytest

from asdf import block, constants, generic_io


def test_checksum(tmp_path):
    my_array = np.arange(0, 64, dtype="<i8")
    target_checksum = b"\xcaM\\\xb8t_L|\x00\n+\x01\xf1\xcfP1"
    assert block.calculate_block_checksum(my_array) == target_checksum
    assert block.calculate_block_checksum(my_array.reshape((8, 8))) == target_checksum

    # check that when written, a block generates the correct checksum
    config = block.BlockConfig()
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        block.write_block(fd, my_array.view(dtype="uint8"), config)
    with generic_io.get_file(path, mode="r") as fd:
        block_state = block.read_block(fd, config)
    assert block_state.header["checksum"] == target_checksum


def test_validate_block_header():
    # check for invalid compression
    with pytest.raises(ValueError):
        block.validate_block_header({"compression": b"foo"})

    # streamed blocks cannot be compressed
    with pytest.raises(ValueError):
        block.validate_block_header({"compression": b"zlib", "flags": constants.BLOCK_FLAG_STREAMED})
    block.validate_block_header(
        {"compression": b"\0\0\0\0", "flags": constants.BLOCK_FLAG_STREAMED, "used_size": 0, "data_size": 0}
    )

    # if not compressed, used_size must equal data_size
    with pytest.raises(ValueError):
        block.validate_block_header({"compression": b"\0\0\0\0", "flags": 0, "used_size": 1, "data_size": 0})
    block.validate_block_header({"compression": b"zlib", "flags": 0, "used_size": 1, "data_size": 0})


def test_read_block_header(tmp_path):
    # first write out a file with a block
    my_array = np.arange(0, 64, dtype="<i8")
    config = block.BlockConfig()
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        written_header = block.write_block(fd, my_array.view("uint8"), config)

    # try reading the block header at the start
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config)
    assert header == written_header

    # check that block can be read without the starting block magic bytes
    with generic_io.get_file(path, mode="r") as fd:
        fd.seek(4)
        header = block.read_block_header(fd, config, past_magic=True)
    assert header == written_header

    # seek into the header, creating an invalid starting position
    # where the header size will be 0
    with generic_io.get_file(path, mode="r") as fd:
        fd.seek(10)
        with pytest.raises(ValueError):
            header = block.read_block_header(fd, config)

    # check that offset, when provided is used
    with generic_io.get_file(path, mode="r") as fd:
        with pytest.raises(ValueError):
            header = block.read_block_header(fd, config, offset=10)
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config, offset=4, past_magic=True)
    assert header == written_header

    bad_magic = io.BytesIO(b"\xd3BBB")
    with generic_io.get_file(bad_magic, mode="r") as fd:
        with pytest.raises(ValueError):
            header = block.read_block_header(fd, config)

    # if when reading the magic, not enough bytes are returned
    # the end-of-file is assumed and the header should return None
    empty = io.BytesIO(b"")
    with generic_io.get_file(empty, mode="r") as fd:
        header = block.read_block_header(fd, config)
        assert header is None

    # if the block index is encountered, None should be returned
    # to signify no more blocks are available
    block_index = io.BytesIO(constants.INDEX_HEADER)
    with generic_io.get_file(block_index, mode="r") as fd:
        header = block.read_block_header(fd, config)
        assert header is None


def test_read_block_data(tmp_path):
    # first write out a file with a block
    my_array = np.arange(0, 64, dtype="uint8")
    config = block.BlockConfig(lazy_load=True)
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        block.write_block(fd, my_array, config)

    # read the header and get the offset within the file where the
    # data is located
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config)
        data_offset = fd.tell()
        data = block.read_block_data(fd, header, config)
        # as this is lazy_loaded, data will be a function
        assert np.array_equal(data(), my_array)
        # check that offset works as expected
        data = block.read_block_data(fd, header, config, offset=data_offset)
        assert np.array_equal(data(), my_array)

    # not lazy loaded, memmapped
    config.lazy_load = False
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config)
        data_offset = fd.tell()
        data = block.read_block_data(fd, header, config)
        assert np.array_equal(data, my_array)
        data = block.read_block_data(fd, header, config, offset=data_offset)
        assert np.array_equal(data, my_array)
        base = data
        while getattr(base, "base", None) is not None:
            base = base.base
        assert isinstance(base, mmap.mmap)

    # not memmapped
    config.memmap = False
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config)
        data_offset = fd.tell()
        data = block.read_block_data(fd, header, config)
        assert np.array_equal(data, my_array)
        base = data
        while getattr(base, "base", None) is not None:
            base = base.base
        assert not isinstance(base, mmap.mmap)

    # stream, this ignored used_size and reads the rest of the file
    config.stream = True
    with generic_io.get_file(path, mode="r") as fd:
        header = block.read_block_header(fd, config)
        data_offset = fd.tell()
        data = block.read_block_data(fd, header, config)
        assert np.array_equal(data, my_array)
        fd.seek(data_offset)
        # fake a stream block header
        header["flags"] = constants.BLOCK_FLAG_STREAMED
        header["data_size"] = 0
        header["allocated_size"] = 0
        header["used_size"] = 0
        header["checksum"] = b"\0" * 16
        data = block.read_block_data(fd, header, config)

    # TODO error cases


def test_read_block(tmp_path):
    block_bytes = io.BytesIO(
        b"\xd3BLK"
        + b"\x000"  # magic
        + b"\0\0\0\0"  # header size
        + b"\0\0\0\0"  # flags
        + b"\0\0\0\0\0\0\0\0"  # compression
        + b"\0\0\0\0\0\0\0\0"  # allocated size
        + b"\0\0\0\0\0\0\0\0"  # used size
        + b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~"  # data size  # checksum
    )

    config = block.BlockConfig(lazy_load=False, memmap=False)
    with generic_io.get_file(block_bytes, mode="r") as fd:
        block_state = block.read_block(fd, config)
        assert len(block_state.data) == 0
        for k in "flags", "allocated_size", "used_size", "data_size":
            assert block_state.header[k] == 0

    # TODO error cases etc


def test_write_block(tmp_path):
    expected = (
        b"\xd3BLK"
        + b"\x000"  # magic
        + b"\0\0\0\0"  # header size
        + b"\0\0\0\0"  # flags
        + b"\0\0\0\0\0\0\0\0"  # compression
        + b"\0\0\0\0\0\0\0\0"  # allocated size
        + b"\0\0\0\0\0\0\0\0"  # used size
        + b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~"  # data size  # checksum
    )

    # first write out a file with a block
    my_array = np.array([], dtype="uint8")
    config = block.BlockConfig(lazy_load=False)
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        block.write_block(fd, my_array, config)

    with generic_io.get_file(path, mode="r") as fd:
        buff = fd.read(-1)
        assert buff == expected

    # TODO check that writing does not occur if data_size > allocated_size
    # TODO error cases etc


def test_fd_not_seekable():
    return
    # data = np.ones(1024)
    # b = block.Block(data=data)
    # fd = io.BytesIO()

    # seekable = lambda: False  # noqa: E731
    # fd.seekable = seekable

    # write_array = lambda arr: fd.write(arr.tobytes())  # noqa: E731
    # fd.write_array = write_array

    # read_blocks = lambda us: [fd.read(us)]  # noqa: E731
    # fd.read_blocks = read_blocks

    # fast_forward = lambda offset: fd.seek(offset, 1)  # noqa: E731
    # fd.fast_forward = fast_forward

    # b.output_compression = "zlib"
    # b.write(fd)
    # fd.seek(0)
    # b = block.Block()
    # b.read(fd)
    # # We lost the information about the underlying array type,
    # # but still can compare the bytes.
    # assert b.data.tobytes() == data.tobytes()
