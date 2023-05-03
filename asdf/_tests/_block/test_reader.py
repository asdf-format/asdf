import contextlib
import io
import mmap
import os

import numpy as np
import pytest

from asdf import constants, generic_io, util
from asdf._block import io as bio
from asdf._block.reader import read_blocks


@contextlib.contextmanager
def gen_blocks(fn=None, n=5, size=10, padding=0, padding_byte=b"\0", with_index=False, block_padding=False):
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
            bio.write_block(fd, data, padding=block_padding)
        if with_index:
            bio.write_block_index(fd, offsets)
        fd.seek(0)
        yield fd, check


# test a few paddings to test read_blocks checking 4 bytes while searching for the first block
@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
@pytest.mark.parametrize("with_index", [True, False])
@pytest.mark.parametrize("padding", [0, 3, 4, 5])
def test_read(tmp_path, lazy_load, memmap, with_index, padding):
    fn = tmp_path / "test.bin"
    n = 5
    size = 10
    with gen_blocks(fn=fn, n=n, size=size, padding=padding, with_index=with_index) as (fd, check):
        r = read_blocks(fd, memmap=memmap, lazy_load=lazy_load)
        if lazy_load and with_index:
            assert r[0].loaded
            assert r[-1].loaded
            for blk in r[1:-1]:
                assert not blk.loaded
        else:
            for blk in r:
                assert blk.loaded
        if memmap:
            for blk in r:
                base = util.get_array_base(blk.data)
                assert isinstance(base.base, mmap.mmap)
        check(r)


def test_read_invalid_padding():
    with gen_blocks(padding=1, padding_byte=b"\1") as (fd, check):
        with pytest.raises(OSError, match="Invalid bytes.*"):
            check(read_blocks(fd))


def test_read_post_padding():
    with gen_blocks(padding=1) as (fd, check):
        fd.seek(0, os.SEEK_END)
        # acceptable to have <4 bytes after the last block
        fd.write(b"\0" * 3)
        fd.seek(0)
        check(read_blocks(fd))


# TODO non-seekable


@pytest.mark.parametrize("invalid_block_index", [0, 1, -1])
def test_invalid_block_index(tmp_path, invalid_block_index):
    fn = tmp_path / "test.bin"
    with gen_blocks(fn=fn, with_index=True) as (fd, check):
        offset = bio.find_block_index(fd)
        assert offset is not None
        block_index = bio.read_block_index(fd, offset)
        block_index[invalid_block_index] += 4
        fd.seek(offset)
        bio.write_block_index(fd, block_index)
        fd.seek(0)
        # when the block index is read, only the first and last blocks
        # are check, so any other invalid entry should result in failure
        if invalid_block_index in (0, -1):
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
        check(read_blocks(fd, lazy_load=True))


def test_closed_file(tmp_path):
    fn = tmp_path / "test.bin"
    with gen_blocks(fn=fn, with_index=True) as (fd, check):
        blocks = read_blocks(fd, lazy_load=True)
        blk = blocks[1]
    with pytest.raises(OSError, match="Attempt to load block from closed file"):
        blk.load()
