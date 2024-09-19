import contextlib
import gc

import numpy as np
from numpy.testing import assert_array_equal

import asdf
from asdf.extension import Converter, Extension
from asdf.testing import helpers


class BlockData:
    def __init__(self, payload):
        self.payload = payload


class BlockConverter(Converter):
    tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
    types = [BlockData]
    _return_invalid_keys = False

    def to_yaml_tree(self, obj, tag, ctx):
        # lookup source for obj
        block_index = ctx.find_available_block_index(
            lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
        )
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]
        data = ctx.get_block_data_callback(block_index)()
        obj = BlockData(data.tobytes())
        return obj


class BlockExtension(Extension):
    tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
    converters = [BlockConverter()]
    extension_uri = "asdf://somewhere.org/extensions/block_data-1.0.0"


@contextlib.contextmanager
def with_extension(ext_class):
    with asdf.config_context() as cfg:
        cfg.add_extension(ext_class())
        yield


@with_extension(BlockExtension)
def test_roundtrip_block_data():
    a = BlockData(b"abcdefg")
    b = helpers.roundtrip_object(a)
    assert a.payload == b.payload


@with_extension(BlockExtension)
def test_block_converter_block_allocation(tmp_path):
    a = BlockData(b"abcdefg")

    # make a tree without the BlockData instance to avoid
    # the initial validate which will trigger block allocation
    af = asdf.AsdfFile({"a": None})
    # now assign to the tree item (avoiding validation)
    af["a"] = a

    # they currently hold storage settings
    fn = tmp_path / "test.asdf"
    af.write_to(fn)

    # if we read a file
    with asdf.open(fn, mode="rw") as af:
        fn2 = tmp_path / "test2.asdf"
        # there should be 1 block
        assert len(af._blocks.blocks) == 1
        # validate should use that block
        af.validate()
        assert len(af._blocks.blocks) == 1
        # as should write_to
        af.write_to(fn2)
        assert len(af._blocks.blocks) == 1
        # and update
        af.update()
        assert len(af._blocks.blocks) == 1


class BlockDataCallback:
    """An example object that uses the data callback to read block data"""

    def __init__(self, callback):
        self.callback = callback

    @property
    def data(self):
        return self.callback()


class BlockDataCallbackConverter(Converter):
    tags = ["asdf://somewhere.org/tags/block_data_callback-1.0.0"]
    types = [BlockDataCallback]

    def to_yaml_tree(self, obj, tag, ctx):
        block_index = ctx.find_available_block_index(obj.callback)
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]

        obj = BlockDataCallback(ctx.get_block_data_callback(block_index))
        return obj


class BlockDataCallbackExtension(Extension):
    tags = ["asdf://somewhere.org/tags/block_data_callback-1.0.0"]
    converters = [BlockDataCallbackConverter()]
    extension_uri = "asdf://somewhere.org/extensions/block_data_callback-1.0.0"


@with_extension(BlockDataCallbackExtension)
def test_block_data_callback_converter(tmp_path):
    # use a callback that every time generates a new array
    # this would cause issues for the old block management as the
    # id(arr) would change every time
    a = BlockDataCallback(lambda: np.zeros(3, dtype="uint8"))

    tfn = tmp_path / "tmp.asdf"
    asdf.AsdfFile({"obj": a}).write_to(tfn)
    with asdf.open(tfn) as af:
        assert_array_equal(a.data, af["obj"].data)

    # make a tree without the BlockData instance to avoid
    # the initial validate which will trigger block allocation
    af = asdf.AsdfFile({"a": None})
    # now assign to the tree item (avoiding validation)
    af["a"] = a
    # write_to will use the block
    fn1 = tmp_path / "test.asdf"
    af.write_to(fn1)

    # if we read a file
    with asdf.open(fn1, mode="rw") as af:
        fn2 = tmp_path / "test2.asdf"
        # there should be 1 block
        assert len(af._blocks.blocks) == 1
        # validate should use that block
        af.validate()
        assert len(af._blocks.blocks) == 1
        # as should write_to
        af.write_to(fn2)
        assert len(af._blocks.blocks) == 1
        # and update
        af.update()
        assert len(af._blocks.blocks) == 1

    # check that data was preserved
    for fn in (fn1, fn2):
        with asdf.open(fn) as af:
            assert_array_equal(af["a"].data, a.data)


@with_extension(BlockDataCallbackExtension)
def test_block_with_callback_removal(tmp_path):
    fn1 = tmp_path / "test1.asdf"
    fn2 = tmp_path / "test2.asdf"

    a = BlockDataCallback(lambda: np.zeros(3, dtype="uint8"))
    b = BlockDataCallback(lambda: np.ones(3, dtype="uint8"))
    base_af = asdf.AsdfFile({"a": a, "b": b})
    base_af.write_to(fn1)

    for remove_key, check_key in [("a", "b"), ("b", "a")]:
        # check that removing one does not interfere with the other
        with asdf.open(fn1) as af:
            af[remove_key] = None
            af.write_to(fn2)
        with asdf.open(fn2) as af:
            af[check_key] = b.data
        # also test update
        # first copy fn1 to fn2
        with asdf.open(fn1) as af:
            af.write_to(fn2)
        with asdf.open(fn2, mode="rw") as af:
            af[remove_key] = None
            af.update()
            af[check_key] = b.data


class MultiBlockData:
    def __init__(self, data):
        self.data = data
        self.keys = []


class MultiBlockConverter(Converter):
    tags = ["asdf://somewhere.org/tags/multi_block_data-1.0.0"]
    types = [MultiBlockData]

    def to_yaml_tree(self, obj, tag, ctx):
        if not len(obj.keys):
            obj.keys = [ctx.generate_block_key() for _ in obj.data]
        indices = [ctx.find_available_block_index(d, k) for d, k in zip(obj.data, obj.keys)]
        return {
            "indices": indices,
        }

    def from_yaml_tree(self, node, tag, ctx):
        indices = node["indices"]
        keys = [ctx.generate_block_key() for _ in indices]
        cbs = [ctx.get_block_data_callback(i, k) for i, k in zip(indices, keys)]
        obj = MultiBlockData([cb() for cb in cbs])
        obj.keys = keys
        return obj


class MultiBlockExtension(Extension):
    tags = ["asdf://somewhere.org/tags/multi_block_data-1.0.0"]
    converters = [MultiBlockConverter()]
    extension_uri = "asdf://somewhere.org/extensions/multi_block_data-1.0.0"


@with_extension(MultiBlockExtension)
def test_mutli_block():
    a = MultiBlockData([np.arange(3, dtype="uint8") for i in range(3)])
    b = helpers.roundtrip_object(a)
    assert len(a.data) == len(b.data)
    assert [np.testing.assert_array_equal(aa, ab) for aa, ab in zip(a.data, b.data)]


class SharedBlockData:
    def __init__(self, callback):
        self.callback = callback

    @property
    def data(self):
        return self.callback()


class SharedBlockConverter(Converter):
    tags = ["asdf://somewhere.org/tags/shared_block_data-1.0.0"]
    types = [SharedBlockData]
    _return_invalid_keys = False

    def to_yaml_tree(self, obj, tag, ctx):
        # lookup source for obj
        block_index = ctx.find_available_block_index(
            lambda: obj.data,
        )
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]
        callback = ctx.get_block_data_callback(block_index)
        obj = SharedBlockData(callback)
        return obj


class SharedBlockExtension(Extension):
    tags = ["asdf://somewhere.org/tags/shared_block_data-1.0.0"]
    converters = [SharedBlockConverter()]
    extension_uri = "asdf://somewhere.org/extensions/shared_block_data-1.0.0"


@with_extension(SharedBlockExtension)
def test_shared_block_reassignment(tmp_path):
    fn = tmp_path / "test.asdf"
    arr1 = np.arange(10, dtype="uint8")
    arr2 = np.arange(5, dtype="uint8")
    a = SharedBlockData(lambda: arr1)
    b = SharedBlockData(lambda: arr1)
    asdf.AsdfFile({"a": a, "b": b}).write_to(fn)
    with asdf.open(fn, mode="rw") as af:
        af["b"].callback = lambda: arr2
        af.update()
    with asdf.open(fn) as af:
        np.testing.assert_array_equal(af["a"].data, arr1)
        np.testing.assert_array_equal(af["b"].data, arr2)


@with_extension(SharedBlockExtension)
def test_shared_block_obj_removal(tmp_path):
    fn = tmp_path / "test.asdf"
    arr1 = np.arange(10, dtype="uint8")
    a = SharedBlockData(lambda: arr1)
    b = SharedBlockData(lambda: arr1)
    asdf.AsdfFile({"a": a, "b": b}).write_to(fn)
    with asdf.open(fn, mode="rw") as af:
        af["b"] = None
        del b
        gc.collect(2)
        af.update()
    with asdf.open(fn) as af:
        np.testing.assert_array_equal(af["a"].data, arr1)
        assert af["b"] is None
