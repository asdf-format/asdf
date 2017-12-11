# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


from .tags.core import ndarray


class Stream(ndarray.NDArrayType):
    """
    Used to put a streamed array into the tree.

    Examples
    --------
    Save a double-precision array with 1024 columns, one row at a
    time::

         >>> from asdf import AsdfFile, Stream
         >>> import numpy as np
         >>> ff = AsdfFile()
         >>> ff.tree['streamed'] = Stream([1024], np.float64)
         >>> with open('test.asdf', 'wb') as fd:
         ...     ff.write_to(fd)
         ...     for i in range(200):
         ...         nbytes = fd.write(
         ...                      np.array([i] * 1024, np.float64).tostring())
    """
    name = None
    types = []

    def __init__(self, shape, dtype, strides=None):
        self._shape = shape
        self._datatype, self._byteorder = ndarray.numpy_dtype_to_asdf_datatype(dtype)
        self._strides = strides
        self._array = None

    def _make_array(self):
        self._array = None

    @classmethod
    def reserve_blocks(cls, data, ctx):
        if isinstance(data, Stream):
            yield ctx.blocks.get_streamed_block()

    @classmethod
    def from_tree(cls, data, ctx):
        return ndarray.NDArrayType.from_tree(data, ctx)

    @classmethod
    def to_tree(cls, data, ctx):
        ctx.blocks.get_streamed_block()

        result = {}
        result['source'] = -1
        result['shape'] = ['*'] + data._shape
        result['datatype'] = data._datatype
        result['byteorder'] = data._byteorder
        if data._strides is not None:
            result['strides'] = data._strides
        return result

    def __repr__(self):
        return "Stream({}, {}, strides={})".format(
            self._shape, self._datatype, self._strides)

    def __str__(self):
        return str(self.__repr__())
