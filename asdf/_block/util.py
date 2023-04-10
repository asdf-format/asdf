from collections import namedtuple

from asdf import util


def calculate_updated_layout(blocks, tree_size, pad_blocks, block_size):
    """
    Calculates a block layout that will try to use as many blocks as
    possible in their original locations, though at this point the
    algorithm is fairly naive.  The result will be stored in the
    offsets of the blocks.

    Parameters
    ----------
    blocks : Blocks instance

    tree_size : int
        The amount of space to reserve for the tree at the beginning.

    Returns
    -------
    Returns `False` if no good layout can be found and one is best off
    rewriting the file serially, otherwise, returns `True`.
    """

    def unfix_block(i):
        # If this algorithm gets more sophisticated we could carefully
        # move memmapped blocks around without clobbering other ones.

        # TODO: Copy to a tmpfile on disk and memmap it from there.
        entry = fixed[i]
        copy = entry.block.data.copy()
        entry.block.close()
        entry.block._data = copy
        del fixed[i]
        free.append(entry.block)

    def fix_block(block, offset):
        block.offset = offset
        fixed.append(Entry(block.offset, block.offset + block.size, block))
        fixed.sort()

    Entry = namedtuple("Entry", ["start", "end", "block"])

    fixed = []
    free = []
    for block in blocks._internal_blocks:
        if block.offset is not None:
            block.update_size()
            fixed.append(Entry(block.offset, block.offset + block.size, block))
        else:
            free.append(block)

    if not len(fixed):
        return False

    fixed.sort()

    # Make enough room at the beginning for the tree, by popping off
    # blocks at the beginning
    while len(fixed) and fixed[0].start < tree_size:
        unfix_block(0)

    if not len(fixed):
        return False

    # This algorithm is pretty basic at this point -- it just looks
    # for the first open spot big enough for the free block to fit.
    while len(free):
        block = free.pop()
        last_end = tree_size
        for entry in fixed:
            if entry.start - last_end >= block.size:
                fix_block(block, last_end)
                break
            last_end = entry.end
        else:
            padding = util.calculate_padding(entry.block.size, pad_blocks, block_size)
            fix_block(block, last_end + padding)

    if blocks.streamed_block is not None:
        padding = util.calculate_padding(fixed[-1].block.size, pad_blocks, block_size)
        blocks.streamed_block.offset = fixed[-1].end + padding

    blocks._sort_blocks_by_offset()

    return True
