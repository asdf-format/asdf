import io
import os

import numpy as np
import pytest
from numpy.random import random
from numpy.testing import assert_array_equal

import asdf
from asdf import block, constants, generic_io

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

    b = block.Block()
    b._array_storage = "foo"

    with pytest.raises(ValueError, match=r"Unknown array storage type foo"):
        ff._blocks.add(b)

    with pytest.raises(ValueError, match=r"Unknown array storage type foo"):
        ff._blocks.remove(b)


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


def test_update_expand_tree(tmp_path):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.arange(64) * 1
    my_array2 = np.arange(64) * 2
    tree = {"arrays": [my_array, my_array2, np.arange(3)]}

    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["arrays"][2], "inline")
    assert len(list(ff._blocks.inline_blocks)) == 1
    ff.write_to(testpath, pad_blocks=True)
    with asdf.open(testpath, mode="rw") as ff:
        assert_array_equal(ff.tree["arrays"][0], my_array)
        orig_offset = ff._blocks[ff.tree["arrays"][0]].offset
        ff.tree["extra"] = [0] * 6000
        ff.update()

    with asdf.open(testpath) as ff:
        assert orig_offset <= ff._blocks[ff.tree["arrays"][0]].offset
        assert ff._blocks[ff.tree["arrays"][2]].array_storage == "inline"
        assert_array_equal(ff.tree["arrays"][0], my_array)
        assert_array_equal(ff.tree["arrays"][1], my_array2)

    # Now, we expand the header only by a little bit
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["arrays"][2], "inline")
    ff.write_to(os.path.join(tmp_path, "test2.asdf"), pad_blocks=True)
    with asdf.open(os.path.join(tmp_path, "test2.asdf"), mode="rw") as ff:
        orig_offset = ff._blocks[ff.tree["arrays"][0]].offset
        ff.tree["extra"] = [0] * 2
        ff.update()

    with asdf.open(os.path.join(tmp_path, "test2.asdf")) as ff:
        assert orig_offset == ff._blocks[ff.tree["arrays"][0]].offset
        assert ff._blocks[ff.tree["arrays"][2]].array_storage == "inline"
        assert_array_equal(ff.tree["arrays"][0], my_array)
        assert_array_equal(ff.tree["arrays"][1], my_array2)


def _get_update_tree():
    return {"arrays": [np.arange(64) * 1, np.arange(64) * 2, np.arange(64) * 3]}


def test_update_delete_first_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        del ff.tree["arrays"][0]
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][2])


def test_update_delete_last_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        del ff.tree["arrays"][-1]
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])


def test_update_delete_middle_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        del ff.tree["arrays"][1]
        ff.update()
        assert len(ff._blocks._internal_blocks) == 2

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert len(ff.tree["arrays"]) == 2
        assert ff.tree["arrays"][0]._source == 0
        assert ff.tree["arrays"][1]._source == 1
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][2])


def test_update_replace_first_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        ff.tree["arrays"][0] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], np.arange(32))
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])


def test_update_replace_last_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        ff.tree["arrays"][2] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], np.arange(32))


def test_update_replace_middle_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        ff.tree["arrays"][1] = np.arange(32)
        ff.update()

    assert os.stat(path).st_size <= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], np.arange(32))
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])


def test_update_add_array(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        ff.tree["arrays"].append(np.arange(32))
        ff.update()

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])
        assert_array_equal(ff.tree["arrays"][3], np.arange(32))


def test_update_add_array_at_end(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    tree = _get_update_tree()

    ff = asdf.AsdfFile(tree)
    ff.write_to(path, pad_blocks=True)

    original_size = os.stat(path).st_size

    with asdf.open(os.path.join(tmp_path, "test.asdf"), mode="rw") as ff:
        ff.tree["arrays"].append(np.arange(65536, dtype="<i8"))
        ff.update()
        assert len(ff._blocks) == 4

    assert os.stat(path).st_size >= original_size

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        assert_array_equal(ff.tree["arrays"][0], tree["arrays"][0])
        assert_array_equal(ff.tree["arrays"][1], tree["arrays"][1])
        assert_array_equal(ff.tree["arrays"][2], tree["arrays"][2])
        assert_array_equal(ff.tree["arrays"][3], np.arange(65536, dtype="<i8"))


def test_update_replace_all_arrays(tmp_path):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        "my_array": my_array,
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(testpath, pad_blocks=True)

    with asdf.open(testpath, mode="rw") as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 1)
        ff.tree["my_array"] = np.ones((64, 64)) * 2
        ff.update()

    with asdf.open(testpath) as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 2)


def test_update_array_in_place(tmp_path):
    tmp_path = str(tmp_path)
    testpath = os.path.join(tmp_path, "test.asdf")

    # This is the case where the new tree can't fit in the available space
    my_array = np.ones((64, 64)) * 1
    tree = {
        "my_array": my_array,
    }

    ff = asdf.AsdfFile(tree)
    ff.write_to(testpath, pad_blocks=True)

    with asdf.open(testpath, mode="rw") as ff:
        array = np.asarray(ff.tree["my_array"])
        array *= 2
        ff.update()

    with asdf.open(testpath) as ff:
        assert_array_equal(ff.tree["my_array"], np.ones((64, 64)) * 2)


def test_init_from_asdffile(tmp_path):
    tmp_path = str(tmp_path)

    my_array = RNG.normal(size=(8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff2 = asdf.AsdfFile(ff)
    assert ff.tree["my_array"] is ff2.tree["my_array"]
    assert_array_equal(ff.tree["my_array"], ff2.tree["my_array"])
    assert ff._blocks[my_array] != ff2._blocks[my_array]

    ff2.tree["my_array"] = None
    assert_array_equal(ff.tree["my_array"], my_array)

    ff.write_to(os.path.join(tmp_path, "test.asdf"))

    with asdf.open(os.path.join(tmp_path, "test.asdf")) as ff:
        ff2 = asdf.AsdfFile(ff)
        assert ff.tree["my_array"] is not ff2.tree["my_array"]
        assert_array_equal(ff.tree["my_array"], ff2.tree["my_array"])
        assert ff._blocks[my_array] != ff2._blocks[my_array]

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
    content += b"\0" * (io.DEFAULT_BUFFER_SIZE - 2) + constants.BLOCK_MAGIC + b"\0\x30" + b"\0" * 50

    buff = io.BytesIO(content)
    ff = asdf.open(buff)
    assert len(ff._blocks) == 1

    buff.seek(0)
    fd = generic_io.InputStream(buff, "r")
    ff = asdf.open(fd)
    assert len(ff._blocks) == 1


def test_checksum(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    my_array = np.arange(0, 64, dtype="<i8").reshape((8, 8))
    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path, validate_checksums=True) as ff:
        assert type(ff._blocks._internal_blocks[0].checksum) == bytes
        assert ff._blocks._internal_blocks[0].checksum == b"\xcaM\\\xb8t_L|\x00\n+\x01\xf1\xcfP1"


def test_checksum_update(tmp_path):
    tmp_path = str(tmp_path)
    path = os.path.join(tmp_path, "test.asdf")

    my_array = np.arange(0, 64, dtype="<i8").reshape((8, 8))

    tree = {"my_array": my_array}
    ff = asdf.AsdfFile(tree)
    ff.write_to(path)

    with asdf.open(path, mode="rw") as ff:
        ff.tree["my_array"][7, 7] = 0.0
        # update() should update the checksum, even if the data itself
        # is memmapped and isn't expressly re-written.
        ff.update()

    with asdf.open(path, validate_checksums=True) as ff:
        assert ff._blocks._internal_blocks[0].checksum == b"T\xaf~[\x90\x8a\x88^\xc2B\x96D,N\xadL"


def test_deferred_block_loading(small_tree):
    buff = io.BytesIO()

    ff = asdf.AsdfFile(small_tree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(buff, include_block_index=False, all_array_storage="internal")

    buff.seek(0)
    with asdf.open(buff) as ff2:
        assert len([x for x in ff2._blocks.blocks if isinstance(x, block.Block)]) == 1
        ff2.tree["science_data"] * 2
        ff2.tree["not_shared"] * 2
        assert len([x for x in ff2._blocks.blocks if isinstance(x, block.Block)]) == 2

        with pytest.raises(ValueError, match=r"Block .* not found."):
            ff2._blocks.get_block(2)


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
        assert isinstance(ff2._blocks._internal_blocks[0], block.Block)
        assert len(ff2._blocks._internal_blocks) == 100
        for i in range(2, 99):
            assert isinstance(ff2._blocks._internal_blocks[i], block.UnloadedBlock)
        assert isinstance(ff2._blocks._internal_blocks[99], block.Block)

        # Force the loading of one array
        ff2.tree["arrays"][50] * 2

        for i in range(2, 99):
            if i == 50:
                assert isinstance(ff2._blocks._internal_blocks[i], block.Block)
            else:
                assert isinstance(ff2._blocks._internal_blocks[i], block.UnloadedBlock)


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
        assert isinstance(ff2._blocks._internal_blocks[0], block.Block)
        assert len(ff2._blocks._internal_blocks) == narrays


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
    # should fall back to the skip method, which
    # only loads the first block.
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


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
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_invalid_block_index_values():
    # This adds a value in the block index that points to something
    # past the end of the file.  In that case, we should just reject
    # the index altogether.

    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=False)
    ff._blocks._internal_blocks.append(block.UnloadedBlock(buff, 123456789))
    ff._blocks.write_block_index(buff, ff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_invalid_last_block_index():
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
    ff.write_to(buff, include_block_index=False)
    ff._blocks._internal_blocks[-1]._offset -= 4
    ff._blocks.write_block_index(buff, ff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_unordered_block_index():
    """
    This creates a block index that isn't in increasing order
    """

    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=False)
    ff._blocks._internal_blocks = ff._blocks._internal_blocks[::-1]
    ff._blocks.write_block_index(buff, ff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_invalid_block_index_first_block_value():
    """
    This creates a bogus block index where the offset of the first
    block doesn't match what we already know it to be.  In this
    case, we should reject the whole block index.
    """
    buff = io.BytesIO()

    arrays = []
    for i in range(10):
        arrays.append(np.ones((8, 8)) * i)

    tree = {"arrays": arrays}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=False)
    ff._blocks._internal_blocks[0]._offset -= 4
    ff._blocks.write_block_index(buff, ff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_invalid_block_id():
    ff = asdf.AsdfFile()
    with pytest.raises(ValueError, match=r"Invalid source id .*"):
        ff._blocks.get_block(-2)


def test_dots_but_no_block_index():
    """
    This puts `...` at the end of the file, so we sort of think
    we might have a block index, but as it turns out, we don't
    after reading a few chunks from the end of the file.
    """
    buff = io.BytesIO()

    tree = {"array": np.ones((8, 8))}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, include_block_index=False)

    buff.write(b"A" * 64000)
    buff.write(b"...\n")

    buff.seek(0)
    with asdf.open(buff) as ff:
        assert len(ff._blocks) == 1


def test_open_no_memmap(tmp_path):
    tmpfile = os.path.join(str(tmp_path), "random.asdf")

    tree = {"array": np.random.random((20, 20))}

    ff = asdf.AsdfFile(tree)
    ff.write_to(tmpfile)

    # Test that by default we use memmapped arrays when possible
    with asdf.open(tmpfile) as af:
        array = af.tree["array"]
        # Make sure to access the block so that it gets loaded
        array[0]
        assert array.block._memmapped is True
        assert isinstance(array.block._data, np.memmap)

    # Test that if we ask for copy, we do not get memmapped arrays
    with asdf.open(tmpfile, copy_arrays=True) as af:
        array = af.tree["array"]
        assert array.block._memmapped is False
        # We can't just check for isinstance(..., np.array) since this will
        # be true for np.memmap as well
        assert not isinstance(array.block._data, np.memmap)


def test_fd_not_seekable():
    data = np.ones(1024)
    b = block.Block(data=data)
    fd = io.BytesIO()

    seekable = lambda: False  # noqa: E731
    fd.seekable = seekable

    write_array = lambda arr: fd.write(arr.tobytes())  # noqa: E731
    fd.write_array = write_array

    read_blocks = lambda us: [fd.read(us)]  # noqa: E731
    fd.read_blocks = read_blocks

    fast_forward = lambda offset: fd.seek(offset, 1)  # noqa: E731
    fd.fast_forward = fast_forward

    b.output_compression = "zlib"
    b.write(fd)
    fd.seek(0)
    b = block.Block()
    b.read(fd)
    # We lost the information about the underlying array type,
    # but still can compare the bytes.
    assert b.data.tobytes() == data.tobytes()


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


def test_block_allocation_on_validate():
    """
    Verify that no additional block is allocated when a tree
    containing a fortran ordered array is validated

    See https://github.com/asdf-format/asdf/issues/1205
    """
    array = np.array([[11, 12, 13], [21, 22, 23]], order="F")
    af = asdf.AsdfFile({"array": array})
    assert len(list(af._blocks.blocks)) == 1
    af.validate()
    assert len(list(af._blocks.blocks)) == 1
