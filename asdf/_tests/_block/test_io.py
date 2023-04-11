import io
import mmap

import numpy as np
import pytest

from asdf import constants, generic_io
from asdf._block import io as bio


def test_checksum(tmp_path):
    my_array = np.arange(0, 64, dtype="<i8")
    target_checksum = b"\xcaM\\\xb8t_L|\x00\n+\x01\xf1\xcfP1"
    assert bio.calculate_block_checksum(my_array) == target_checksum
    assert bio.calculate_block_checksum(my_array.reshape((8, 8))) == target_checksum

    # check that when written, a block generates the correct checksum
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        bio.write_block(fd, my_array.view(dtype="uint8"))
    with generic_io.get_file(path, mode="r") as fd:
        _, header, _, _ = bio.read_block(fd)
    assert header["checksum"] == target_checksum


def test_validate_block_header():
    # check for invalid compression
    with pytest.raises(ValueError):
        bio.validate_block_header({"compression": b"foo"})

    # streamed blocks cannot be compressed
    with pytest.raises(ValueError):
        bio.validate_block_header({"compression": b"zlib", "flags": constants.BLOCK_FLAG_STREAMED})
    bio.validate_block_header(
        {"compression": b"\0\0\0\0", "flags": constants.BLOCK_FLAG_STREAMED, "used_size": 0, "data_size": 0},
    )

    # if not compressed, used_size must equal data_size
    with pytest.raises(ValueError):
        bio.validate_block_header({"compression": b"\0\0\0\0", "flags": 0, "used_size": 1, "data_size": 0})
    bio.validate_block_header({"compression": b"zlib", "flags": 0, "used_size": 1, "data_size": 0})


def test_read_block_header(tmp_path):
    # first write out a file with a block
    my_array = np.arange(0, 64, dtype="<i8")
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        written_header = bio.write_block(fd, my_array.view("uint8"))

    # try reading the block header at the start
    with generic_io.get_file(path, mode="r") as fd:
        header = bio.read_block_header(fd)
    assert header == written_header

    # seek into the header, creating an invalid starting position
    # where the header size will be 0
    with generic_io.get_file(path, mode="r") as fd:
        fd.seek(10)
        with pytest.raises(ValueError):
            header = bio.read_block_header(fd)

    # check that offset, when provided is used
    with generic_io.get_file(path, mode="r") as fd, pytest.raises(ValueError):
        header = bio.read_block_header(fd, offset=10)
    with generic_io.get_file(path, mode="r") as fd:
        fd.seek(4)
        header = bio.read_block_header(fd, offset=0)
    assert header == written_header


def test_read_block_data(tmp_path):
    # first write out a file with a block
    my_array = np.arange(0, 64, dtype="uint8")
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        bio.write_block(fd, my_array)

    # read the header and get the offset within the file where the
    # data is located
    with generic_io.get_file(path, mode="r") as fd:
        header = bio.read_block_header(fd)
        data_offset = fd.tell()
        data = bio.read_block_data(fd, header)
        assert np.array_equal(data, my_array)
        # check that offset works as expected
        data = bio.read_block_data(fd, header, offset=data_offset)
        assert np.array_equal(data, my_array)

    # not lazy loaded, memmapped
    with generic_io.get_file(path, mode="r") as fd:
        offset, header, read_data_offset, data = bio.read_block(fd, lazy_load=False, memmap=True)
        assert offset == 0
        assert read_data_offset == data_offset
        assert np.array_equal(data, my_array)
        base = data
        while getattr(base, "base", None) is not None:
            base = base.base
        assert isinstance(base, mmap.mmap)

    # not memmapped, lazy
    with generic_io.get_file(path, mode="r") as fd:
        offset, header, read_data_offset, data = bio.read_block(fd, lazy_load=True, memmap=False)
        assert offset == 0
        assert read_data_offset == data_offset
        assert np.array_equal(data(), my_array)
        base = data()
        while getattr(base, "base", None) is not None:
            base = base.base
        assert not isinstance(base, mmap.mmap)


def test_read_block(tmp_path):
    block_bytes = io.BytesIO(
        b"\x000"  # header size = 2
        + b"\0\0\0\0"  # flags = 4
        + b"\0\0\0\0"  # compression = 4
        + b"\0\0\0\0\0\0\0\0"  # allocated size = 8
        + b"\0\0\0\0\0\0\0\0"  # used size = 8
        + b"\0\0\0\0\0\0\0\0"  # data size = 8
        + b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~",  # checksum = 16
    )

    with generic_io.get_file(block_bytes, mode="r") as fd:
        offset, header, data_offset, data = bio.read_block(fd)
        assert offset == 0
        assert data_offset == 50
        assert len(data) == 0
        for k in "flags", "allocated_size", "used_size", "data_size":
            assert header[k] == 0


def test_write_block(tmp_path):
    expected = (
        b"\x000"  # header size = 2
        + b"\0\0\0\0"  # flags
        + b"\0\0\0\0"  # compression
        + b"\0\0\0\0\0\0\0\0"  # allocated size
        + b"\0\0\0\0\0\0\0\0"  # used size
        + b"\0\0\0\0\0\0\0\0"  # data size
        + b"\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~"  # checksum
    )

    # first write out a file with a block
    my_array = np.array([], dtype="uint8")
    path = tmp_path / "test"
    with generic_io.get_file(path, mode="w") as fd:
        bio.write_block(fd, my_array)

    with generic_io.get_file(path, mode="r") as fd:
        buff = fd.read(-1)
        assert buff == expected


def test_write_block_offset():
    data = np.ones(30, dtype="uint8")
    raw_fd = io.BytesIO()
    fd = generic_io.get_file(raw_fd, mode="rw")
    fd.write(b"0000000")
    bio.write_block(fd, data, offset=0)
    fd.seek(0)
    _, _, _, d = bio.read_block(fd)
    np.testing.assert_array_equal(data, d)


def test_write_oversized_block():
    # check that writing does not occur if data_size > allocated_size
    data = np.ones(30, dtype="uint8")
    raw_fd = io.BytesIO()
    fd = generic_io.get_file(raw_fd, mode="rw")
    with pytest.raises(RuntimeError, match="Block used size.*"):
        bio.write_block(fd, data, allocated_size=0)
    assert fd.tell() == 0


def test_fd_not_seekable():
    data = np.ones(30, dtype="uint8")
    raw_fd = io.BytesIO()
    fd = generic_io.get_file(raw_fd, mode="rw")
    bio.write_block(fd, data)

    raw_fd.seek(0)
    fd = generic_io.get_file(raw_fd, mode="rw")

    seekable = lambda: False  # noqa: E731
    fd.seekable = seekable

    _, _, _, d = bio.read_block(fd)

    np.testing.assert_array_equal(d, data)

    with pytest.raises(ValueError, match="write_block received offset.*"):
        bio.write_block(fd, data, offset=0)


def test_compressed_block():
    data = np.ones(30, dtype="uint8")
    fd = generic_io.get_file(io.BytesIO(), mode="rw")
    write_header = bio.write_block(fd, data, compression="zlib")
    assert write_header["compression"] == b"zlib"
    _, _, _, rdata = bio.read_block(fd, offset=0)
    np.testing.assert_array_equal(rdata, data)


def test_stream_block():
    data = np.ones(10, dtype="uint8")
    fd = generic_io.get_file(io.BytesIO(), mode="rw")
    write_header = bio.write_block(fd, data, stream=True)
    assert write_header["flags"] & constants.BLOCK_FLAG_STREAMED
    # now write extra data to file
    extra_data = np.ones(10, dtype="uint8")
    fd.write_array(extra_data)
    _, _, _, rdata = bio.read_block(fd, offset=0)
    assert rdata.size == 20
    assert np.all(rdata == 1)


def test_read_from_closed(tmp_path):
    fn = tmp_path / "test.blk"
    data = np.ones(10, dtype="uint8")
    with generic_io.get_file(fn, mode="w") as fd:
        bio.write_block(fd, data, stream=True)
    with generic_io.get_file(fn, mode="rw") as fd:
        _, _, _, callback = bio.read_block(fd, offset=0, lazy_load=True)
    with pytest.raises(OSError, match="Attempt to read data from closed file"):
        callback()


@pytest.mark.parametrize("data", [np.ones(10, dtype="f4"), np.ones((3, 3), dtype="uint8")])
def test_invalid_data(data):
    fd = generic_io.get_file(io.BytesIO(), mode="rw")
    with pytest.raises(ValueError, match="Data must be of.*"):
        bio.write_block(fd, data, stream=True)
