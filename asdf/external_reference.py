from __future__ import absolute_import, division, unicode_literals, print_function

from .asdftypes import AsdfType


class ExternalArrayReference(AsdfType):
    """
    Store a reference to an array in an external File.

    Parameters
    ----------

    filepath: `str`
        The path to the path to be referenced. Can be relative to the file
        containing the reference.

    target: `object`
        Some internal target to the data in the file. Examples may include a HDU
        index, a HDF path or an asdf fragment.

    dtype: `str`
        The (numpy) dtype of the contained array.

    shape: `tuple`
        The shape of the array to be loaded.
    """
    name = "core/externalarray"

    def __init__(self, filepath, target, dtype, shape):
        self.filepath = str(filepath)
        self.target = target
        self.dtype = dtype
        self.shape = tuple(shape)

    def __repr__(self):
        return "<External array reference in {0} at {1} shape: {2} dtype: {3}>".format(
            self.filepath, self.target, self.shape, self.dtype)

    def __str__(self):
        return repr(self)

    @classmethod
    def to_tree(self, data, ctx):
        node = {}
        node['filepath'] = data.filepath
        node['target'] = data.target
        node['datatype'] = data.dtype
        node['shape'] = data.shape

        return node

    @classmethod
    def from_tree(cls, tree, ctx):
        return cls(tree['filepath'], tree['target'], tree['datatype'], tree['shape'])
