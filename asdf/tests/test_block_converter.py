import numpy as np

import asdf
from asdf.extension import Converter, Extension


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
        data = ctx.load_block(node["block_index"])
        return BlockData(data.tobytes())

    def reserve_blocks(self, obj, tag, ctx):  # Is there a ctx or tag at this point?
        # Reserve a block using a unique key (this will be used in to_yaml_tree
        # to find the block index) and a callable that will return the data/bytes
        # that will eventually be written to the block.
        return [ctx.reserve_block(id(obj), lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload))]

    # def from_blocks(self, obj, tag, ctx):
    #    # do I even need this?


class BlockExtension(Extension):
    tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
    converters = [BlockConverter()]
    extension_uri = "asdf://somewhere.org/extensions/block_data-1.0.0"


def test_block_converter(tmp_path):
    with asdf.config_context() as cfg:
        cfg.add_extension(BlockExtension())

        tree = {"b": BlockData(b"abcdefg")}
        af = asdf.AsdfFile(tree)
        fn = tmp_path / "test.asdf"
        af.write_to(fn)

        with asdf.open(fn) as af:
            assert af["b"].payload == tree["b"].payload
