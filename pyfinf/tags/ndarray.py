# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import sys

import numpy as np

from ..finftypes import FinfType
from .. import util


_dtype_names = {
    'int8': 'i1',
    'int16': 'i2',
    'int32': 'i4',
    'int64': 'i8',
    'uint8': 'u1',
    'uint16': 'u2',
    'uint32': 'u4',
    'uint64': 'u8',
    'float32': 'f4',
    'float64': 'f8',
    'float128': 'f16',
    'complex64': 'c8',
    'complex128': 'c16',
    'complex256': 'c32'
}


def finf_dtype_to_numpy_dtype(dtype, byteorder):
    if dtype in _dtype_names:
        dtype = _dtype_names[dtype]
        if byteorder == 'big':
            return '>' + dtype
        elif byteorder == 'little':
            return '<' + dtype
    raise ValueError("Unknown dtype {0}".format(dtype))


def numpy_dtype_to_finf_dtype(dtype):
    if dtype.name in _dtype_names:
        if dtype.byteorder == '=':
            byteorder = sys.byteorder
        elif dtype.byteorder == '<':
            byteorder = 'little'
        else:
            byteorder = 'big'
        return dtype.name, byteorder
    raise ValueError("Unknown dtype {0}".format(dtype))


class NDArrayType(FinfType):
    name = 'ndarray'
    types = [np.ndarray]

    def __init__(self, source, shape, dtype, offset, strides,
                 order, finffile):
        self._source = source
        self._shape = shape
        self._dtype = dtype
        self._offset = offset
        self._strides = strides
        self._order = order
        self._buffer = None
        if self._source >= len(finffile._blocks):
            raise ValueError("Block {0} not found".format(self._source))
        self._buffer = finffile._blocks[self._source]
        self._array = None

    def _make_array(self):
        if self._array is None:
            self._array = np.ndarray(
                self._shape, self._dtype, self._buffer.data,
                self._offset, self._strides, self._order)
        return self._array

    def __array__(self):
        return self._make_array()

    def __repr__(self):
        # repr alone should not force loading of the data
        if self._array is None:
            return "<array (unloaded) '{0}' '{1}'>".format(
                self._shape, self._dtype)
        return repr(self._array)

    def __str__(self):
        # str alone should not force loading of the data
        if self._array is None:
            return "<array (unloaded) '{0}' '{1}'>".format(
                self._shape, self._dtype)
        return str(self._array)

    def __getattr__(self, attr):
        return getattr(self._make_array(), attr)

    def __getitem__(self, item):
        return self._make_array()[item]

    def __setitem__(self, item, val):
        self._make_array()[item] = val

    @classmethod
    def from_tree(cls, node, ctx):
        shape = node['shape']
        dtype = finf_dtype_to_numpy_dtype(
            node.get('dtype', 'uint8'), node.get('byteorder', 'big'))
        source = node['source']
        if not isinstance(source, int):
            raise NotImplementedError("source URIs not yet implemented")
        offset = node.get('offset', 0)
        strides = node.get('strides', None)

        return cls(source, shape, dtype, offset, strides, 'C', ctx.finffile)

    @classmethod
    def pre_write(cls, data, ctx):
        # Find all of the used data buffers so we can add or rearrange
        # them if necessary
        if isinstance(data, np.ndarray):
            ctx.finffile.blocks.find_or_create_block_for_array(data)

    @classmethod
    def to_tree(cls, data, ctx):
        if isinstance(data, np.ndarray):
            base = util.get_array_base(data)
            block, source = ctx.finffile.blocks.find_or_create_block_for_array(base)
            shape = data.shape
            dtype = data.dtype
            offset = data.ctypes.data - base.ctypes.data
            if data.flags['C_CONTIGUOUS']:
                strides = None
            else:
                strides = data.strides
        elif isinstance(data, NDArrayType):
            source = data._source
            shape = data._shape
            dtype = data._dtype
            offset = data._offset
            strides = data._strides

        result = {}
        result['shape'] = list(shape)
        result['source'] = source

        dtype, byteorder = numpy_dtype_to_finf_dtype(dtype)
        result['dtype'] = dtype
        if byteorder != 'big':
            result['byteorder'] = byteorder

        if offset > 0:
            result['offset'] = offset

        if strides is not None:
            result['strides'] = list(strides)

        return result

    @classmethod
    def assert_equal(cls, old, new):
        from numpy.testing import assert_array_equal

        assert_array_equal(old, new)
