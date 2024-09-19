import gc

import numpy as np
import pytest

import asdf
from asdf._block import manager
from asdf._block.options import Options


def test_set_streamed_block_via_options():
    options = manager.OptionsStore(manager.ReadBlocks())
    arr1 = np.arange(10, dtype="uint8")
    arr2 = np.arange(5, dtype="uint8")
    options.set_options(arr1, Options("streamed"))
    with pytest.raises(ValueError, match=r"Can not add second streaming block"):
        options.set_options(arr2, Options("streamed"))
    del arr1
    gc.collect(2)
    options.set_options(arr2, Options("streamed"))


def test_set_streamed_block_via_manager():
    af = asdf.AsdfFile()
    m = af._blocks

    class Foo:
        pass

    arr = np.arange(10, dtype="uint8")
    obj = Foo()
    m.set_streamed_write_block(arr, obj)

    # setting again with the same data is ok
    m.set_streamed_write_block(arr, obj)

    # using a different array is not allowed
    arr2 = np.arange(3, dtype="uint8")
    with pytest.raises(ValueError, match="Can not add second streaming block"):
        m.set_streamed_write_block(arr2, obj)

    # a different object is ok as long as the array matches
    obj2 = Foo()
    m.set_streamed_write_block(arr, obj2)


def test_load_external_internal(tmp_path):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"arr": np.arange(10, dtype="uint8")}).write_to(fn)
    with asdf.open(fn) as af:
        m = af._blocks
        np.testing.assert_array_equal(m._load_external("#"), m.blocks[0].data)


def test_write_no_uri(tmp_path):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"arr": np.arange(10, dtype="uint8")}).write_to(fn)
    with asdf.open(fn) as af:
        m = af._blocks
        with pytest.raises(ValueError, match=r"Can't write external blocks.*"):
            m._write_external_blocks()


def test_write_outside_context(tmp_path):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"arr": np.arange(10, dtype="uint8")}).write_to(fn)
    with asdf.open(fn) as af:
        m = af._blocks
        with pytest.raises(OSError, match=r"write called outside of valid write_context"):
            m.write(False, False)


def test_update_outside_context(tmp_path):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"arr": np.arange(10, dtype="uint8")}).write_to(fn)
    with asdf.open(fn) as af:
        m = af._blocks
        with pytest.raises(OSError, match=r"update called outside of valid write_context"):
            m.update(0, False, False)


def test_input_compression(tmp_path):
    fn = tmp_path / "test.asdf"
    af = asdf.AsdfFile({"arr": np.arange(10, dtype="uint8")})
    af.set_array_compression(af["arr"], "zlib")
    af.write_to(fn)

    with asdf.open(fn) as af:
        assert af.get_array_compression(af["arr"]) == "zlib"
        af.set_array_compression(af["arr"], "bzp2")
        assert af.get_array_compression(af["arr"]) == "bzp2"
        af.set_array_compression(af["arr"], "input")
        assert af.get_array_compression(af["arr"]) == "zlib"
