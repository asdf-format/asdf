import contextlib

import numpy as np
from numpy.testing import assert_array_equal

import asdf
from asdf.extension import Converter, Extension
from asdf.testing import helpers


class BlockData:
    def __init__(self, payload):
        self.payload = payload
        # generate a unique id
        self._asdf_key = asdf.util.BlockKey()


class BlockConverter(Converter):
    tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
    types = [BlockData]
    _return_invalid_keys = False
    _double_assign_block = False

    def to_yaml_tree(self, obj, tag, ctx):
        # lookup source for obj
        block_index = ctx.find_block_index(
            obj._asdf_key,
            lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
        )
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]
        data = ctx.get_block_data_callback(block_index)()
        obj = BlockData(data.tobytes())
        ctx.assign_block_key(block_index, obj._asdf_key)
        if self._double_assign_block:
            self._double_assign_block = False
            key2 = asdf.util.BlockKey()
            ctx.assign_block_key(block_index, key2)
        return obj

    def reserve_blocks(self, obj, tag):
        if self._return_invalid_keys:
            # return something unhashable
            self._return_invalid_keys = False
            return [[]]
        return [obj._asdf_key]


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


@with_extension(BlockExtension)
def test_invalid_reserve_block_keys(tmp_path):
    a = BlockData(b"abcdefg")
    af = asdf.AsdfFile({"a": a})
    fn = tmp_path / "test.asdf"
    BlockExtension.converters[0]._return_invalid_keys = True
    with pytest.raises(TypeError, match="unhashable type: .*"):
        af.write_to(fn)


@with_extension(BlockExtension)
def test_double_assign_block(tmp_path):
    a = BlockData(b"abcdefg")
    af = asdf.AsdfFile({"a": a})
    fn = tmp_path / "test.asdf"
    af.write_to(fn)
    BlockExtension.converters[0]._double_assign_block = True
    with pytest.raises(ValueError, match="block 0 is already assigned to a key"):
        with asdf.open(fn):
            pass


class BlockDataCallback:
    """An example object that uses the data callback to read block data"""

    def __init__(self, callback):
        self.callback = callback
        self._asdf_key = asdf.util.BlockKey()

    @property
    def data(self):
        return self.callback()


class BlockDataCallbackConverter(Converter):
    tags = ["asdf://somewhere.org/tags/block_data_callback-1.0.0"]
    types = [BlockDataCallback]

    def to_yaml_tree(self, obj, tag, ctx):
        block_index = ctx.find_block_index(obj._asdf_key, obj.callback)
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]

        obj = BlockDataCallback(ctx.get_block_data_callback(block_index))
        ctx.assign_block_key(block_index, obj._asdf_key)
        return obj

    def reserve_blocks(self, obj, tag):
        return [obj._asdf_key]


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

    b = helpers.roundtrip_object(a)
    assert_array_equal(a.data, b.data)

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


def test_seralization_context_block_access():
    af = asdf.AsdfFile()
    sctx = af._create_serialization_context()

    # finding an index for an unknown block should
    # create one
    key = 42
    arr = np.ones(3, dtype="uint8")
    index = sctx.find_block_index(key, lambda: arr)
    assert len(af._blocks) == 1
    assert id(arr) == id(sctx.get_block_data_callback(index)())
    # finding the same block should not create a new one
    index = sctx.find_block_index(key, lambda: arr)
    assert len(af._blocks) == 1

    new_key = 26
    with pytest.raises(ValueError, match="block 0 is already assigned to a key"):
        sctx.assign_block_key(index, new_key)
    assert len(af._blocks) == 1

    arr2 = np.zeros(3, dtype="uint8")
    # test that providing a new callback won't overwrite
    # the first one
    index = sctx.find_block_index(key, lambda: arr2)
    assert id(arr2) != id(sctx.get_block_data_callback(index)())
