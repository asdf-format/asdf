import io
import os

import numpy as np
import pytest
import yaml
from numpy.random import random
from numpy.testing import assert_array_equal

import asdf
from asdf import constants, generic_io
from asdf._block import io as bio
from asdf.exceptions import AsdfBlockIndexWarning

RNG = np.random.default_rng(6)


def test_external_block(tmp_path):
    tmp_path = str(tmp_path)

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(my_array, "external")
    assert ff.get_array_storage(my_array) == "external"

    ff.write_to(os.path.join(tmp_path, "test.asdf"))

    assert "test0000.asdf" in os.listdir(tmp_path)


def test_external_block_url():
    uri = "asdf://foo"
    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    asdf.get_config().all_array_storage = "external"
    # this should not raise a ValueError since uri is provided
    asdf.AsdfFile(tree, uri=uri)


def test_external_block_non_url():
    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(my_array, "external")
    assert ff.get_array_storage(my_array) == "external"

    buff = io.BytesIO()
    with pytest.raises(ValueError, match=r"Can't write external blocks, since URI of main file is unknown."):
        ff.write_to(buff)


def test_invalid_array_storage():
    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError, match=r"array_storage must be one of.*"):
        ff.set_array_storage(my_array, "foo")


def test_transfer_array_sources(tmp_path):
    tmp_path = str(tmp_path)

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(os.path.join(tmp_path, "test.asdf"))

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(my_array, ff.tree["my_array"])
        ff.write_to(os.path.join(tmp_path, "test2.asdf"))
        # write_to should have no effect on getting the original data
        assert_array_equal(my_array, ff.tree["my_array"])

    assert ff._fd is None


def test_write_to_same(tmp_path):
    tmp_path = str(tmp_path)

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(os.path.join(tmp_path, "test.asdf"))

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        assert_array_equal(my_array, ff.tree["my_array"])
        ff.tree["extra"] = [0] * 1000
        ff.write_to(os.path.join(tmp_path, "test2.asdf"))

    with asdf.open(os.path.join(tmp_path, "test2.asdf"), mode="rw") as ff:
        assert_array_equal(my_array, ff.tree["my_array"])


def test_pad_blocks(tmp_path):
    tmp_path = str(tmp_path)

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((8, 8)) * 1
    my_array2 = np.ones((42, 5)) * 2
    tree = {"my_array": my_array, "my_array2": my_array2}

    ff = asdf.AsdfFile(tree)
    ff.write_to(os.path.join(tmp_path, "test.asdf"), pad_blocks=True)

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["my_array"], my_array)
        assert_array_equal(ff.tree["my_array2"], my_array2)


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_expand_tree(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.arange(64) * 1
    my_array2 = np.arange(64) * 2
    tree = {"arrays": [my_array, my_array2, np.arange(3)]}

    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["arrays"][2], "inline")
    ff.write_to(testpath, pad_blocks=True)
    with asdf.open(testpath, lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        assert len(list(ff._blocks.blocks)) == 2
        assert_array_equal(ff.tree["arrays"][0], my_array)
        ff.tree["extra"] = [0] * 6000
        ff.update()

    with asdf.open(testpath) as ff:
        assert ff.get_array_storage(ff.tree["arrays"][2]) == "inline"
        assert_array_equal(ff.tree["arrays"][0], my_array)
        assert_array_equal(ff.tree["arrays"][1], my_array2)

    # Now, we expand the header only by a little bit
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["arrays"][2], "inline")
    ff.write_to(os.path.join(tmp_path, "test2.asdf"), pad_blocks=True)
    with asdf.open(os.path.join(tmp_path, "test2.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["extra"] = [0] * 2
        ff.update()

    with asdf.open(os.path.join(tmp_path, "test2.asdf")) as ff:
        assert ff.get_array_storage(ff.tree["arrays"][2]) == "inline"
        assert_array_equal(ff.tree["arrays"][0], my_array)
        assert_array_equal(ff.tree["arrays"][1], my_array2)


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_all_external(tmp_path, lazy_load, memmap):
    fn = tmp_path / "test.asdf"

    my_array = np.arange(64) * 1
    my_array2 = np.arange(64) * 2
    tree = {"arrays": [my_array, my_array2]}

    af = asdf.AsdfFile(tree)
    af.write_to(fn)

    with asdf.config.config_context() as cfg:
        cfg.array_inline_threshold = 10
        cfg.all_array_storage = "external"
        with asdf.open(fn, lazy_load=lazy_load, memmap=memmap, mode="rw") as af:
            af.update()

    assert "test0000.asdf" in os.listdir(tmp_path)
    assert "test0001.asdf" in os.listdir(tmp_path)


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_some_external(tmp_path, lazy_load, memmap):
    fn = tmp_path / "test.asdf"

    my_array = np.arange(64) * 1
    my_array2 = np.arange(64) * 2
    tree = {"arrays": [my_array, my_array2]}

    af = asdf.AsdfFile(tree)
    af.write_to(fn)

    with asdf.open(fn, lazy_load=lazy_load, memmap=memmap, mode="rw") as af:
        af.set_array_storage(af["arrays"][0], "external")
        af.update()

    assert "test0000.asdf" in os.listdir(tmp_path)
    assert "test0001.asdf" not in os.listdir(tmp_path)


def _get_update_tree():
    return {"arrays": [np.arange(64) * 1, np.arange(64) * 2, np.arange(64) * 3]}


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_delete_first_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        del ff.tree["arrays"][0]
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][2])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_delete_last_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        del ff.tree["arrays"][-1]
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_delete_middle_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        del ff.tree["arrays"][1]
        ff.update()
        assert len(ff._blocks.blocks) == 2

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert len(ff.tree["arrays"]) == 2
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][2])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_replace_first_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["arrays"][0] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], np.arange(32))
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_replace_last_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["arrays"][2] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], np.arange(32))


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_replace_middle_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["arrays"][1] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], np.arange(32))
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_add_array(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["arrays"].append(np.arange(32))
        ff.update()

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])
        assert_array_equal(ff.tree["arrays"][3], np.arange(32))


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_add_array_at_end(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["arrays"].append(np.arange(65536, dtype="<i8"))
        ff.update()
        assert len(ff._blocks.blocks) == 4

    assert os.stat(path).st_size >= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])
        assert_array_equal(ff.tree["arrays"][3], np.arange(65536, dtype="<i8"))


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_replace_all_arrays(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        "my_array": my_array,
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(testpath, pad_blocks=True)

    with asdf.open(os.path.join(tmp_path, "test.asdf"), lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 1)
        ff.tree["my_array"] = np.ones((64, 64)) * 2
        ff.update()

    with asdf.open(testpath) as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 2)


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_array_in_place(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        "my_array": my_array,
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(testpath, pad_blocks=True)

    with asdf.open(testpath, lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        array = np.asarray(ff.tree["my_array"])
        array *= 2
        ff.update()

    with asdf.open(testpath) as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 2)


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_update_compressed_blocks(tmp_path, lazy_load, memmap):
    """
    This test was originally constructed to test an issue where
    a failed update left a corrupt file. The issue that resulted in
    the failed update (a compressed block growing in size) was fixed
    so this is no longer a good test for a failed update.

    See: https://github.com/asdf-format/asdf/issues/1520

    However, the test does serve to make sure that updating the
    contents of compressed blocks in a way that causes them to grow
    in size on disk does not result in a failed update.
    """
    fn = tmp_path / "test.asdf"
    n_arrays = 10
    array_size = 10000

    # make a tree with many arrays that will compress well
    af = asdf.AsdfFile()
    for i in range(n_arrays):
        af[i] = np.zeros(array_size, dtype="uint8") + i
        af.set_array_compression(af[i], "zlib")
    af.write_to(fn)

    with asdf.open(fn, lazy_load=lazy_load, memmap=memmap, mode="rw") as af:
        # now make the data are difficult to compress
        for i in range(n_arrays):
            assert np.all(af[i] == i)
            af[i][:] = np.random.randint(255, size=array_size)
            af[i][0] = i + 1
        af.update()

    with asdf.open(fn, mode="r") as af:
        for i in range(n_arrays):
            assert af[i][0] == i + 1


def test_init_from_asdffile(tmp_path):
    tmp_path = str(tmp_path)

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff2 = asdf.AsdfFile(ff)
    assert ff.tree["my_array"] is ff2.tree["my_array"]
    assert_array_equal(ff.tree["my_array"], ff2.tree["my_array"])

    ff2.tree["my_array"] = None
    assert_array_equal(ff.tree["my_array"], my_array)

    ff.write_to(os.path.join(tmp_path, "test.asdf"))

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        ff2 = asdf.AsdfFile(ff)
        # assert ff.tree["my_array"] is not ff2.tree["my_array"]
        assert_array_equal(ff.tree["my_array"], ff2.tree["my_array"])

        ff2.tree["my_array"] = None
        assert_array_equal(ff.tree["my_array"], my_array)


def test_seek_until_on_block_boundary():
    # Create content where the first block begins on a
    # file-reading-block boundary.

    content = b"""#ASDF 1.0.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.0.0
foo : bar
...
"""
    content += b"\0" * (io.DEFAULT_BUFFER_SIZE - 2) + constants.BLOCK_MAGIC + b"\0\x30" + b"\0" * 48

    buff = io.BytesIO(content)
    ff = asdf.open(buff)
    assert len(ff._blocks.blocks) == 1

    buff.seek(0)
    fd = generic_io.InputStream(buff, "r")
    ff = asdf.open(fd)
    assert len(ff._blocks.blocks) == 1


def test_checksum(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    my_array = np.arange(0, 64, dtype="<i8").reshape((8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path, validate_checksums=True) as ff:
        assert ff._blocks.blocks[0].header["checksum"] == b"\xcaM\\\xb8t_L|\x00\n+\x01\xf1\xcfP1"


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_checksum_update(tmp_path, lazy_load, memmap):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    my_array = np.arange(0, 64, dtype="<i8").reshape((8, 8))

    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path, lazy_load=lazy_load, memmap=memmap, mode="rw") as ff:
        ff.tree["my_array"][7, 7] = 0.0
        # update() should update the checksum, even if the data itself
        # is memmapped and isn't expressly re-written.
        ff.update()

    with asdf.open(path, validate_checksums=True) as ff:
        assert ff._blocks.blocks[0].header["checksum"] == b"T\xaf~[\x90\x8a\x88^\xc2B\x96D,N\xadL"


def test_block_index():
    buff = io.BytesIO()

    arrays = []
    for i in range(100):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff) as ff2:
        assert len(ff2._blocks.blocks) == 100
        assert ff2._blocks.blocks[0].loaded
        for i in range(2, 99):
            assert not ff2._blocks.blocks[i].loaded
        assert ff2._blocks.blocks[99].loaded

        # Force the loading of one array
        ff2.tree["arrays"][50] * 2

        for i in range(2, 99):
            if i == 50:
                assert ff2._blocks.blocks[i].loaded
            else:
                assert not ff2._blocks.blocks[i].loaded


def test_large_block_index():
    """
    This test is designed to test reading of a block index that is
    larger than a single file system block, which is why we create
    io.DEFAULT_BUFFER_SIZE / 4 arrays, and assuming each entry has more
    than one digit in its address, we're guaranteed to have an index
    larger than a filesystem block.
    """

    # TODO: It would be nice to find a way to make this test faster.  The
    # real bottleneck here is the enormous YAML section.

    buff = io.BytesIO()

    narrays = int(io.DEFAULT_BUFFER_SIZE / 4)

    arrays = []
    for i in range(narrays):
        arrays.append(np.array([i], np.uint16))

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(buff, all_array_storage="internal")

    buff.seek(0)
    with asdf.open(buff) as ff2:
        assert ff2._blocks.blocks[0].loaded
        assert len(ff2._blocks.blocks) == narrays


def test_no_block_index():
    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=False)

    assert constants.INDEX_HEADER not in buff.getvalue()


def test_junk_after_index():
    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    buff.write(b"JUNK")

    buff.seek(0)

    # This has junk after the block index, so it
    # should fall back to reading serially
    with pytest.warns(AsdfBlockIndexWarning, match="Failed to read block index"):
        with asdf.open(buff) as ff:
            assert ff._blocks.blocks[1].loaded


def test_short_file_find_block_index():
    # This tests searching for a block index in a file that looks like
    # it might have an index, in the last filesystem block or so, but
    # ultimately proves to not have an index.

    buff = io.BytesIO()

    ff = asdf.AsdfFile({"arr": np.ndarray([1]), "arr2": np.ndarray([2])})
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(buff, include_block_index=False, all_array_storage="internal")

    buff.write(b"#ASDF BLOCK INDEX\n")
    buff.write(b"0" * (io.DEFAULT_BUFFER_SIZE * 4))

    buff.seek(0)
    with pytest.warns(AsdfBlockIndexWarning, match="Failed to read block index"):
        with asdf.open(buff) as ff:
            assert len(ff._blocks.blocks) == 2
            assert ff._blocks.blocks[1].loaded


def test_invalid_block_index_values():
    # This adds a value in the block index that points to something
    # past the end of the file.  In that case, we should just reject
    # the index altogether.

    buff = generic_io.get_file(io.BytesIO(), mode="w")

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=True)
    buff.seek(0)
    offset = bio.find_block_index(buff)
    buff.seek(offset)
    block_index = bio.read_block_index(buff)
    block_index.append(123456789)
    buff.seek(offset)
    bio.write_block_index(buff, block_index)

    buff.seek(0)
    with pytest.warns(AsdfBlockIndexWarning, match="Invalid block index contents"):
        with asdf.open(buff) as ff:
            assert len(ff._blocks.blocks) == 10
            assert ff._blocks.blocks[1].loaded


@pytest.mark.parametrize("block_index_index", [0, -1])
def test_invalid_block_index_offset(block_index_index):
    """
    This adds a value in the block index that points to something
    that isn't a block
    """

    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    # now overwrite the block index with the first entry
    # incorrectly pointing to a non-block offset
    buff.seek(0)
    bs = buff.read()
    block_index_header_start = bs.index(constants.INDEX_HEADER)
    block_index_start = block_index_header_start + len(constants.INDEX_HEADER)
    block_index = yaml.load(bs[block_index_start:], yaml.SafeLoader)
    block_index[block_index_index] -= 4
    buff.seek(block_index_start)
    yaml.dump(
        block_index,
        stream=buff,
        explicit_start=True,
        explicit_end=True,
        version=asdf.versioning._YAML_VERSION,
        allow_unicode=True,
        encoding="utf-8",
    )

    buff.seek(0)
    with pytest.warns(AsdfBlockIndexWarning, match="Invalid block index contents"):
        with asdf.open(buff) as ff:
            assert len(ff._blocks.blocks) == 10
            for i, a in enumerate(arrays):
                assert ff._blocks.blocks[i].loaded
                assert_array_equal(ff["arrays"][i], a)


def test_unordered_block_index():
    """
    This creates a block index that isn't in increasing order
    """

    buff = generic_io.get_file(io.BytesIO(), mode="w")

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=True)
    buff.seek(0)
    offset = bio.find_block_index(buff)
    buff.seek(offset)
    block_index = bio.read_block_index(buff)
    buff.seek(offset)
    bio.write_block_index(buff, block_index[::-1])
    buff.seek(0)

    buff.seek(0)
    with pytest.warns(AsdfBlockIndexWarning, match="Failed to read block index"):
        with asdf.open(buff) as ff:
            assert len(ff._blocks.blocks) == 10
            assert ff._blocks.blocks[1].loaded


@pytest.fixture(scope="module")
def filename_with_array(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "filename_with_array.asdf"
    tree = {"array": np.random.random((20, 20))}
    ff = asdf.AsdfFile(tree)
    ff.write_to(fn)
    return fn


@pytest.mark.parametrize(
    "open_kwargs,should_memmap",
    [
        ({}, False),
        ({"lazy_load": True, "memmap": True}, True),
        ({"lazy_load": False, "memmap": True}, True),
        ({"lazy_load": True, "memmap": False}, False),
        ({"lazy_load": False, "memmap": False}, False),
    ],
)
def test_open_no_memmap(filename_with_array, open_kwargs, should_memmap):
    """
    Test that asdf.open does not (or does) return memmaps for arrays
    depending on a number of arguments including:
        default (no kwargs)
        memmap
    """
    with asdf.open(filename_with_array, **open_kwargs) as af:
        array = af.tree["array"]
        if should_memmap:
            assert isinstance(array.base, np.memmap)
        else:
            assert not isinstance(array.base, np.memmap)


def test_add_block_before_fully_loaded(tmp_path):
    """
    This test covers a subtle case where a block is added
    to a file before all pre-existing internal blocks have
    been located.  If the BlockManager isn't careful to
    locate them all first, the new block will take the index
    of an existing block and views over that index will
    point to the wrong data.

    See https://github.com/asdf-format/asdf/issues/999
    """
    file_path1 = tmp_path / "test1.asdf"
    file_path2 = tmp_path / "test2.asdf"
    arr0 = random(10)
    arr1 = random(10)
    arr2 = random(10)

    with asdf.AsdfFile() as af:
        af["arr0"] = None
        af["arr1"] = arr1
        af["arr2"] = arr2
        af.write_to(file_path1, include_block_index=False)

    with asdf.open(file_path1) as af:
        af["arr0"] = arr0
        af.write_to(file_path2)

    with asdf.open(file_path2) as af:
        assert_array_equal(af["arr0"], arr0)
        assert_array_equal(af["arr1"], arr1)
        assert_array_equal(af["arr2"], arr2)


@pytest.mark.parametrize("all_array_storage", ["internal", "external", "inline"])
@pytest.mark.parametrize("all_array_compression", [None, "", "zlib", "bzp2", "lz4", "input"])
@pytest.mark.parametrize("compression_kwargs", [None, {}])
def test_write_to_update_storage_options(tmp_path, all_array_storage, all_array_compression, compression_kwargs):
    if all_array_compression == "bzp2" and compression_kwargs is not None:
        compression_kwargs = {"compresslevel": 1}

    def assert_result(ff):
        if all_array_storage == "external":
            assert "test0000.asdf" in os.listdir(tmp_path)
        else:
            assert "test0000.asdf" not in os.listdir(tmp_path)
        if all_array_storage == "internal":
            assert len(ff._blocks.blocks) == 1
        else:
            assert len(ff._blocks.blocks) == 0

        if all_array_storage == "internal":
            target_compression = all_array_compression or None
            if target_compression == "input":
                target_compression = None
            assert ff.get_array_compression(ff["array"]) == target_compression

    arr1 = np.ones((8, 8))
    tree = {"array": arr1}
    fn = tmp_path / "test.asdf"

    ff1 = asdf.AsdfFile(tree)

    # first check write_to
    ff1.write_to(
        fn,
        all_array_storage=all_array_storage,
        all_array_compression=all_array_compression,
        compression_kwargs=compression_kwargs,
    )

    # then reuse the file to check update
    arr2 = np.ones((8, 8)) * 42
    with asdf.open(fn, mode="rw") as ff2:
        assert_result(ff2)
        np.testing.assert_array_equal(arr1, ff2["array"])
        ff2["array"] = arr2
        ff2.update(
            all_array_storage=all_array_storage,
            all_array_compression=all_array_compression,
            compression_kwargs=compression_kwargs,
        )
        assert_result(ff2)
    with asdf.open(fn) as ff3:
        assert_result(ff3)
        np.testing.assert_array_equal(arr2, ff3["array"])


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("memmap", [True, False])
def test_remove_blocks(tmp_path, lazy_load, memmap):
    fn1 = tmp_path / "test.asdf"
    fn2 = tmp_path / "test2.asdf"

    tree = {"a": np.zeros(3), "b": np.ones(10)}
    tree["c"] = tree["b"][:5]

    for key in tree:
        af = asdf.AsdfFile(tree)
        af.write_to(fn1)

        with asdf.open(fn1, lazy_load=lazy_load, memmap=memmap, mode="rw") as af:
            assert len(af._blocks.blocks) == 2
            af[key] = None
            af.write_to(fn2)

        with asdf.open(fn1, lazy_load=lazy_load, memmap=memmap, mode="rw") as af:
            assert len(af._blocks.blocks) == 2
            af[key] = None
            af.update()

        for fn in (fn1, fn2):
            with asdf.open(fn) as af:
                if key == "a":
                    assert len(af._blocks.blocks) == 1
                else:
                    assert len(af._blocks.blocks) == 2
                for key2 in tree:
                    if key == key2:
                        continue
                    np.testing.assert_array_equal(af[key2], tree[key2])


def test_open_memmap_from_closed_file(tmp_path):
    fn = tmp_path / "test.asdf"
    arr = np.zeros(100)
    arr2 = np.ones(100)
    tree = {"base": arr, "view": arr[:50], "base2": arr2}
    af = asdf.AsdfFile(tree)
    af.write_to(fn)

    with asdf.open(fn, lazy_load=True, memmap=False) as af:
        # load the base so we can test if accessing the view after the
        # file is closed will trigger an error
        af["base"][:]
        view = af["view"]
        base2 = af["base2"]

    msg = r"ASDF file has already been closed. Can not get the data."
    with pytest.raises(OSError, match=msg):
        view[:]

    with pytest.raises(OSError, match=msg):
        base2[:]


@pytest.mark.parametrize("default_array_save_base", [True, False])
@pytest.mark.parametrize("save_base", [True, False, None])
def test_views_save_base(tmp_path, default_array_save_base, save_base):
    fn = tmp_path / "test.asdf"
    arr = np.zeros(100, dtype="uint8")
    tree = {"v": arr[:10]}
    with asdf.config_context() as cfg:
        cfg.default_array_save_base = default_array_save_base
        af = asdf.AsdfFile(tree)
        if save_base is not None:
            af.set_array_save_base(af["v"], save_base)
        af.write_to(fn)

    with asdf.open(fn, memmap=True) as af:
        base = af["v"].base
        if save_base or (save_base is None and default_array_save_base):
            assert len(base) == 100
        else:
            assert len(base) == 10
