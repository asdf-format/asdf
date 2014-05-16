# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from .tags.core import ndarray


class Stream(ndarray.NDArrayType):
    """
    Used to put a streamed array into the tree.

    Examples
    --------
    Save a double-precision array with 1024 columns, one row at a
    time::

         >>> from pyfinf import FinfFile, Stream
         >>> import numpy as np
         >>> ff = FinfFile()
         >>> ff.tree['streamed'] = Stream([1024], np.float64)
         >>> with ff.write_to('test.finf') as ff:
         ...     for i in range(200):
         ...         ff.write_to_stream(np.array([i] * 1024, np.float64).tostring())
    """

    types = []

    def __init__(self, shape, dtype, strides=None):
        self._shape = shape
        self._dtype, self._byteorder = ndarray.numpy_dtype_to_finf_dtype(dtype)
        self._strides = strides
        self._array = None

    def _make_array(self):
        self._array = None

    @classmethod
    def pre_write(cls, data, ctx):
        if isinstance(data, Stream):
            ctx.finffile.blocks.get_streamed_block()

    @classmethod
    def from_tree(cls, data, ctx):
        return ndarray.NDArrayType.from_tree(data, ctx)

    @classmethod
    def to_tree(cls, data, ctx):
        ctx.finffile.blocks.get_streamed_block()

        result = {}
        result['source'] = -1
        result['shape'] = ['*'] + data._shape
        result['dtype'] = data._dtype
        if data._byteorder != 'big':
            result['byteorder'] = data._byteorder
        if data._strides is not None:
            result['strides'] = data._strides
        return result
