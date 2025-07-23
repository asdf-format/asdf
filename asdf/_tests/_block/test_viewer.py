import numpy as np
import pytest

import asdf
from asdf.constants import BLOCK_MAGIC


@pytest.fixture()
def asdf_file(tmp_path):
    fn = tmp_path / "test.asdf"
    tree = {
        "array_0": np.arange(42),
        "array_1": np.arange(720, dtype="f8"),
    }
    tree["view_0"] = tree["array_0"]
    tree["view_1"] = tree["array_1"][:42]
    tree["stream"] = asdf.Stream([1], "f4")
    af = asdf.AsdfFile(tree)
    af.set_array_compression(tree["array_1"], "bzp2")
    af.write_to(fn, pad_blocks=0.1)
    with asdf.open(fn) as af:
        yield af


def test_count_blocks(asdf_file):
    assert len(asdf_file.blocks) == 3


def test_flags(asdf_file):
    assert asdf_file.blocks[0].header["flags"] == 0
    assert asdf_file.blocks[1].header["flags"] == 0
    assert asdf_file.blocks[2].header["flags"] == 1


def test_compression(asdf_file):
    assert asdf_file.blocks[0].header["compression"] == b"\x00\x00\x00\x00"
    assert asdf_file.blocks[1].header["compression"] == b"bzp2"
    assert asdf_file.blocks[2].header["compression"] == b"\x00\x00\x00\x00"


def test_header_read_only(asdf_file):
    with pytest.raises(TypeError, match="does not support item assignment"):
        asdf_file.blocks[0].header["flags"] = 42


@pytest.mark.parametrize("attr", ("offset", "data_offset", "loaded"))
def test_attr_read_only(asdf_file, attr):
    # message varies by python version
    with pytest.raises(AttributeError, match="(can't set attribute|object has no setter)"):
        setattr(asdf_file.blocks[0], attr, 42)


def test_offset(asdf_file):
    # test a relative offset to make this test not depend on a specific tree size.
    relative_offset = asdf_file.blocks[1].offset - asdf_file.blocks[0].data_offset
    assert asdf_file.blocks[0].header["allocated_size"] + len(BLOCK_MAGIC) == relative_offset


def test_loaded(tmp_path):
    # can't use the asdf_file fixture here as the Stream
    # causes all blocks to be loaded
    fn = tmp_path / "test.asdf"
    asdf.dump({"arrays": [np.zeros(3) for _ in range(3)]}, fn)

    with asdf.open(fn) as af:
        assert not af.blocks[0].loaded
        assert not af.blocks[1].loaded
        assert not af.blocks[2].loaded

        # trigger loading of all blocks
        assert np.sum([a.sum() for a in af["arrays"]]) == 0

        assert af.blocks[0].loaded
        assert af.blocks[1].loaded
        assert af.blocks[2].loaded


def test_info(asdf_file, capsys):
    asdf_file.blocks.info()
    lines = capsys.readouterr().out.splitlines()
    assert "Block 0: 8192 bytes, 336 used" in lines[0]
    assert "Block 1: 8192 bytes, 878 used, bzp2 compression" in lines[1]
    assert "Block 2: Stream" in lines[2]


@pytest.mark.parametrize("show_blocks", (True, False))
@pytest.mark.parametrize(
    "max_rows, blocks_expected",
    (
        (None, True),
        (10, False),
        ((None, 10), True),
        ((10, None), False),
    ),
)
def test_info_limited(asdf_file, capsys, max_rows, blocks_expected, show_blocks):
    asdf_file.info(max_rows=max_rows, show_blocks=show_blocks)
    out = capsys.readouterr().out
    if blocks_expected and show_blocks:
        assert "Block 0" in out
    else:
        assert "Block 0" not in out


def test_info_many_blocks(tmp_path, capsys):
    fn = tmp_path / "test.asdf"
    asdf.dump({"arrays": [np.zeros(3) for _ in range(11)]}, fn)
    asdf.info(fn, max_rows=None)
    out = capsys.readouterr().out
    assert "Block  0" in out
