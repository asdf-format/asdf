import contextlib
import io
import mmap
import os

import numpy as np
import pytest

from asdf import constants, generic_io, util
from asdf._block import io as bio
from asdf._block.reader import read_blocks
from asdf.exceptions import AsdfBlockIndexWarning, AsdfWarning


@contextlib.contextmanager
def gen_blocks(
    fn=None, n=5, size=10, padding=0, padding_byte=b"\0", with_index=False, block_padding=False, streamed=False
):
    offsets = []
    if fn is not None:
        with generic_io.get_file(fn, mode="w") as fd:
            pass

    def check(blocks):
        assert len(blocks) == n
        for i, blk in enumerate(blocks):
            assert blk.data.size == size
            assert np.all(blk.data == i)

    with generic_io.get_file(fn or io.BytesIO(), mode="rw") as fd:
        fd.write(padding_byte * padding)
        for i in range(n):
            offsets.append(fd.tell())
            fd.write(constants.BLOCK_MAGIC)
            data = np.ones(size, dtype="uint8") * i
            bio.write_block(fd, data, stream=streamed and (i == n - 1), padding=block_padding)
        if with_index and not streamed:
            bio.write_block_index(fd, offsets)
        fd.seek(0)
        yield fd, check


# test a few paddings to test read_blocks checking 4 bytes while searching for the first block
@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
@pytest.mark.parametrize("with_index", [True, False])
@pytest.mark.parametrize("validate_checksums", [True, False])
@pytest.mark.parametrize("padding", [0, 3, 4, 5])
@pytest.mark.parametrize("streamed", [True, False])
def test_read(tmp_path, lazy_load, memmap, with_index, validate_checksums, padding, streamed):
    fn = tmp_path / "test.bin"
    n = 5
    size = 10
    with gen_blocks(fn=fn, n=n, size=size, padding=padding, with_index=with_index, streamed=streamed) as (fd, check):
        r = read_blocks(fd, memmap=memmap, lazy_load=lazy_load, validate_checksums=validate_checksums)
        if lazy_load and with_index and not streamed:
            assert r[0].loaded
            assert r[-1].loaded
            for blk in r[1:-1]:
                assert not blk.loaded
                # getting the header should load the block
                blk.header
                assert blk.loaded
        else:
            for blk in r:
                assert blk.loaded
        if memmap:
            for blk in r:
                base = util.get_array_base(blk.data)
                assert isinstance(base.base, mmap.mmap)
        check(r)
        if lazy_load:
            # if lazy loaded, each call to data should re-read the data
            assert r[0].data is not r[0].data
        else:
            assert r[0].data is r[0].data
        # getting cached_data should always return the same array
        assert r[0].cached_data is r[0].cached_data


@pytest.mark.parametrize("padding", (1, 4, 7))
@pytest.mark.parametrize("padding_byte", (b"\1", b"\0", b" ", b"\xd3", b"B", b"L", b"K", b"\xd3BL"))
def test_read_valid_padding(padding, padding_byte):
    """Test that reader allows padding bytes before the first block"""
    with gen_blocks(padding=padding, padding_byte=padding_byte) as (fd, check):
        check(read_blocks(fd))


@pytest.mark.parametrize("padding_byte", (b"\xd3BLK", b" \xd3BLK"))
def test_read_invalid_padding(padding_byte):
    with gen_blocks(padding=1, padding_byte=padding_byte) as (fd, check):
        with pytest.raises(ValueError, match="buffer is smaller than requested size"):
            check(read_blocks(fd))


def test_read_post_padding_null_bytes():
    with gen_blocks(padding=1) as (fd, check):
        fd.seek(0, os.SEEK_END)
        # acceptable to have <4 bytes after the last block
        fd.write(b"\x00" * 3)
        fd.seek(0)
        check(read_blocks(fd))


def test_read_post_padding_non_null_bytes():
    with gen_blocks(padding=1) as (fd, check):
        fd.seek(0, os.SEEK_END)
        # acceptable to have <4 bytes after the last block
        fd.write(b"\x01" * 3)
        fd.seek(0)
        with pytest.warns(AsdfWarning, match=r"Read invalid bytes.*"):
            check(read_blocks(fd))


@pytest.mark.parametrize("invalid_block_index", [0, 1, -1, "junk"])
def test_invalid_block_index(tmp_path, invalid_block_index):
    fn = tmp_path / "test.bin"
    with gen_blocks(fn=fn, with_index=True) as (fd, check):
        # trash the block index
        offset = bio.find_block_index(fd)
        assert offset is not None
        if invalid_block_index == "junk":
            # trash the whole index
            fd.seek(-4, 2)
            fd.write(b"junk")
        else:  # mess up one entry of the index
            block_index = bio.read_block_index(fd, offset)
            block_index[invalid_block_index] += 4
            fd.seek(offset)
            bio.write_block_index(fd, block_index)
        fd.seek(0)

        # when the block index is read, only the first and last blocks
        # are check, so any other invalid entry should result in failure
        if invalid_block_index in (0, -1):
            with pytest.warns(AsdfBlockIndexWarning, match="Invalid block index contents"):
                check(read_blocks(fd, lazy_load=True))
        elif invalid_block_index == "junk":
            # read_blocks should fall back to reading serially
            with pytest.warns(AsdfBlockIndexWarning, match="Failed to read block index"):
                check(read_blocks(fd, lazy_load=True))
        else:
            with pytest.raises(ValueError, match="Header size.*"):
                check(read_blocks(fd, lazy_load=True))


def test_invalid_block_in_index_with_valid_magic(tmp_path):
    fn = tmp_path / "test.bin"
    with gen_blocks(fn=fn, with_index=True, block_padding=1.0) as (fd, check):
        offset = bio.find_block_index(fd)
        assert offset is not None
        block_index = bio.read_block_index(fd, offset)
        # move the first block offset to the padding before
        # the second block with enough space to write
        # valid magic (but invalid header)
        block_index[0] = block_index[1] - 6
        fd.seek(block_index[0])
        fd.write(constants.BLOCK_MAGIC)
        fd.write(b"\0\0")

        fd.seek(offset)
        bio.write_block_index(fd, block_index)

        fd.seek(0)
        with pytest.warns(AsdfBlockIndexWarning, match="Invalid block index contents"):
            check(read_blocks(fd, lazy_load=True))


def test_closed_file(tmp_path):
    fn = tmp_path / "test.bin"
    with gen_blocks(fn=fn, with_index=True) as (fd, check):
        blocks = read_blocks(fd, lazy_load=True)
        blk = blocks[1]
    with pytest.raises(OSError, match="Attempt to load block from closed file"):
        blk.load()


@pytest.mark.parametrize("validate_checksums", [True, False])
def test_bad_checksum(validate_checksums):
    buff = io.BytesIO(
        constants.BLOCK_MAGIC
        + b"\x000"  # header size = 2
        + b"\0\0\0\0"  # flags = 4
        + b"\0\0\0\0"  # compression = 4
        + b"\0\0\0\0\0\0\0\0"  # allocated size = 8
        + b"\0\0\0\0\0\0\0\0"  # used size = 8
        + b"\0\0\0\0\0\0\0\0"  # data size = 8
        + b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"  # invalid checksum = 16
    )

    with generic_io.get_file(buff, mode="r") as fd:
        if validate_checksums:
            with pytest.raises(ValueError, match=".* does not match given checksum"):
                read_blocks(fd, lazy_load=False, validate_checksums=validate_checksums)[0].data
        else:
            read_blocks(fd, lazy_load=False, validate_checksums=validate_checksums)[0].data
