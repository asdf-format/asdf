import numpy as np
import pytest

import asdf._block.io as bio
from asdf import constants, generic_io
from asdf._block import reader, writer

# TODO write blocks, with compression_kwargs: how to check this worked?
# TODO invalid inputs


@pytest.mark.parametrize("lazy", [True, False])
@pytest.mark.parametrize("index", [True, False])
@pytest.mark.parametrize("padding", [True, False, 0.1, 0.9])
@pytest.mark.parametrize("compression", [None, b"zlib"])
@pytest.mark.parametrize("stream", [True, False])
def test_write_blocks(tmp_path, lazy, index, padding, compression, stream):
    data = [np.ones(10, dtype=np.uint8), np.zeros(5, dtype=np.uint8)]
    if lazy:
        blocks = [writer.WriteBlock(lambda bd=d: bd, compression=compression) for d in data]
    else:
        blocks = [writer.WriteBlock(d, compression=compression) for d in data]
    if stream:
        streamed_block = writer.WriteBlock(np.ones(15, dtype=np.uint8))
    else:
        streamed_block = None
    fn = tmp_path / "test.bin"
    with generic_io.get_file(fn, mode="w") as fd:
        writer.write_blocks(fd, blocks, padding=padding, streamed_block=streamed_block, write_index=index)
    with generic_io.get_file(fn, mode="r") as fd:
        if index and not stream:
            assert bio.find_block_index(fd) is not None
        else:
            assert bio.find_block_index(fd) is None
        fd.seek(0)
        read_blocks = reader.read_blocks(fd)
        if stream:
            assert len(read_blocks) == (len(data) + 1)
        else:
            assert len(read_blocks) == len(data)
        for r, d in zip(read_blocks, data):
            np.testing.assert_array_equal(r.data, d)
            if compression is not None:
                assert r.header["compression"] == compression
            if padding:
                assert r.header["allocated_size"] > r.header["used_size"]
        if stream:
            read_stream_block = read_blocks[-1]
            np.testing.assert_array_equal(read_stream_block.data, streamed_block.data)
            assert read_stream_block.header["flags"] & constants.BLOCK_FLAG_STREAMED
