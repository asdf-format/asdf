import contextlib

import numpy as np
import pytest

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
        # this is called during validate and write_to (and fill_defaults)
        #
        # During validate (and other non-writing times) ctx should have a
        # valid way to find blocks for the object. During (and after) reading
        # the block will correspond to the read block.
        #
        # During write_to, ctx should return the block_index for the block
        # that was allocate during reserve_blocks.
        #
        # One uncovered case is when an item that uses blocks is added
        # to the tree and validate is called prior to a write. In this case reserve_blocks
        # was never called and no block was read (the object is in memory).
        # The old code would allocate a block and validate the tree and then
        # throw away to block (if a subsequent write wasn't performed).
        # If the ctx is aware that this is not a read or a write, it should
        # be valid to return any number (perhaps an unused index) as the
        # return for this is never written anywhere. An alternative would
        # be that the ctx sees no block exists, then calls reserve_blocks on this
        # obj to allow it to claim a block. This requires that ctx be aware
        # of which obj is passed to to_yaml_tree and which converter is currently
        # being used.

        # lookup source for obj
        block_index = ctx.find_block_index(
            id(obj),
            lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
        )
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        # this is called during open and fill_defaults (also called during open).
        # In all cases, blocks have already been read (or are ready to read) from
        # the file.
        # So I don't see a need for from_blocks... Adding it would make the API
        # more symmetrical but would require another tree traversal and would
        # require that objects can be made (or preparations to make those objects)
        # without whatever is in the block. This function can return anything
        # so a special return value would be complicated. One option would
        # be to add something like: ctx.requires_block(id_required, extra)
        # that could be added to a list of future resolvable objects. After all
        # objects have been passed through from_yaml_tree, the ctx could
        # then go through and resolve all of the objects. This would require
        # some magic where we then need to swap out objects in the tree whereas
        # before the return value to this function was used to fill the tree.
        # Without a reason to add this complexity (aside from symmetry) I'm
        # inclined to leave out 'from_blocks'
        #
        # One complication here is that some objects (like zarray) will
        # not want to load the data right away and instead just have a way
        # to load the data when needed (and possibly multiple times).
        # It might be better to have ctx provide load_block for times
        # when data should be read and zarr can wrap this.
        #
        # Another complication is memmapping. It should not matter that
        # zarr receives a memmap I'm not sure I've fully thought this
        # though.
        block_index = node["block_index"]
        data = ctx.load_block(block_index)
        obj = BlockData(data.tobytes())
        ctx.claim_block(block_index, id(obj))

        # -- alternatively, if data is not required to make the object --
        # obj = BlockData(b"")
        # obj.payload = ctx.load_block(block_index, id(obj))

        # so I think this might need to 'claim' blocks so subsequent 'validate'/'write_to'/etc use
        # the read block (and don't create a new one). This can create a catch 22 when
        # the data is used to make the object (like here), since the id(obj) key is not known
        # until the object is created. What about something like
        # ctx.load_block(index) : loads block data WITHOUT claiming it
        # ctx.attach_block(index, key) : load and claim block
        # ctx.claim_block(key) : just claim/associate the block
        # this is pretty messy and I think could be cleaned up by a new block manager on write
        # there, the blocks would always be claimed and the 'read' block manager would be responsible
        # for only that... Update might still need an association
        # so maybe instead use
        # ctx.load_block(index, key=None) and ctx.claim_block(index, key)
        # ctx._block_manager._data_to_block_mapping[id(obj)] = ctx._block_manager._internal_blocks[0]
        return obj

    def reserve_blocks(self, obj, tag, ctx):  # Is there a ctx or tag at this point?
        # Reserve a block using a unique key (this will be used in to_yaml_tree
        # to find the block index) and a callable that will return the data/bytes
        # that will eventually be written to the block.
        return [ctx.reserve_block(id(obj), lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload))]


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
        # lookup source for obj
        block_index = ctx.find_block_index(id(obj), obj.callback)
        return {
            "block_index": block_index,
        }

    def from_yaml_tree(self, node, tag, ctx):
        block_index = node["block_index"]
        obj = BlockDataCallback(lambda: ctx.load_block(block_index))
        ctx.claim_block(block_index, id(obj))
        return obj

    def reserve_blocks(self, obj, tag, ctx):
        return [ctx.reserve_block(id(obj), obj.callback)]


class BlockDataCallbackExtension(Extension):
    tags = ["asdf://somewhere.org/tags/block_data_callback-1.0.0"]
    converters = [BlockDataCallbackConverter()]
    extension_uri = "asdf://somewhere.org/extensions/block_data_callback-1.0.0"


@pytest.mark.xfail(reason="callback use in a converter requires a new block manager on write")
@with_extension(BlockDataCallbackExtension)
def test_block_data_callback_converter(tmp_path):
    # use a callback that every time generates a new array
    # this would cause issues for the old block management as the
    # id(arr) would change every time
    a = BlockDataCallback(lambda: np.zeros(3, dtype="uint8"))

    b = helpers.roundtrip_object(a)
    assert np.all(a.data == b.data)

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
        af.write_to(fn2)  # TODO this will NOT work without a new block manager on write
        assert len(af._blocks._internal_blocks) == 1
        # and update
        af.update()
        assert len(af._blocks._internal_blocks) == 1


# TODO tests to add
# - memmap/lazy_load other open options
# - block storage settings
# - error cases when data is not of the correct type (not an ndarray, an invalid ndarray, etc)
