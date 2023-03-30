import contextlib

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

    def to_yaml_tree(self, obj, tag, ctx):
        # lookup source for obj
        block_index = ctx.find_block_index(
            id(obj),
            lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
        )
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]
        data = ctx.load_block(block_index, by_index=True)
        obj = BlockData(data.tobytes())
        ctx.claim_block(block_index, id(obj))

        # -- alternatively, if data is not required to make the object --
        # obj = BlockData(b"")
        # obj.payload = ctx.load_block(block_index, id(obj))
        return obj

    def reserve_blocks(self, obj, tag, ctx):  # Is there a ctx or tag at this point?
        return [id(obj)]


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
    # the AsdfFile instance should have no blocks
    assert len(af._blocks._internal_blocks) == 0
    # until validate is called
    af.validate()
    assert len(af._blocks._internal_blocks) == 1
    assert af._blocks._internal_blocks[0].data.tobytes() == a.payload
    # a second validate shouldn't result in more blocks
    af.validate()
    assert len(af._blocks._internal_blocks) == 1
    fn = tmp_path / "test.asdf"
    # nor should write_to
    af.write_to(fn)
    assert len(af._blocks._internal_blocks) == 1

    # if we read a file
    with asdf.open(fn, mode="rw") as af:
        fn2 = tmp_path / "test2.asdf"
        # there should be 1 block
        assert len(af._blocks._internal_blocks) == 1
        # validate should use that block
        af.validate()
        assert len(af._blocks._internal_blocks) == 1
        # as should write_to
        af.write_to(fn2)
        assert len(af._blocks._internal_blocks) == 1
        # and update
        af.update()
        assert len(af._blocks._internal_blocks) == 1


@with_extension(BlockExtension)
def test_invalid_block_data():
    pass


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
        # this will be called during validate and might overwrite the callback
        # lookup source for obj
        block_index = ctx.find_block_index(id(obj), obj.callback)
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]

        obj = BlockDataCallback(lambda: None)
        # now that we have an object we use it's memory location
        # to generate a key
        key = id(obj)

        def callback(_ctx=ctx, _key=key):
            return _ctx.load_block(_key)

        obj.callback = callback

        ctx.claim_block(block_index, key)
        return obj

    def reserve_blocks(self, obj, tag, ctx):
        return [id(obj)]


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
    # the AsdfFile instance should have no blocks
    assert len(af._blocks._internal_blocks) == 0
    # until validate is called
    af.validate()
    assert len(af._blocks._internal_blocks) == 1
    assert np.all(af._blocks._internal_blocks[0].data == a.data)
    # a second validate shouldn't result in more blocks
    af.validate()
    assert len(af._blocks._internal_blocks) == 1
    fn1 = tmp_path / "test.asdf"
    # nor should write_to
    af.write_to(fn1)
    assert len(af._blocks._internal_blocks) == 1

    # if we read a file
    with asdf.open(fn1, mode="rw") as af:
        fn2 = tmp_path / "test2.asdf"
        # there should be 1 block
        assert len(af._blocks._internal_blocks) == 1
        # validate should use that block
        af.validate()
        assert len(af._blocks._internal_blocks) == 1
        # as should write_to
        af.write_to(fn2)
        assert len(af._blocks._internal_blocks) == 1
        # and update
        af.update()
        assert len(af._blocks._internal_blocks) == 1

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


# TODO tests to add
# - memmap/lazy_load other open options
# - block storage settings: compression, etc
# - error cases when data is not of the correct type (not an ndarray, an invalid ndarray, etc)
