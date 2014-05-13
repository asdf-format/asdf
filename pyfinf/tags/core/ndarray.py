# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import sys

import numpy as np

from astropy.extern import six

from ...finftypes import FinfType
from ... import util


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


def finf_byteorder_to_numpy_byteorder(byteorder):
    if byteorder == 'big':
        return '>'
    elif byteorder == 'little':
        return '<'
    raise ValueError("Invalid FINF byteorder '{0}'".format(byteorder))


def finf_dtype_to_numpy_dtype(dtype, byteorder):
    if isinstance(dtype, six.text_type) and dtype in _dtype_names:
        dtype = _dtype_names[dtype]
        byteorder = finf_byteorder_to_numpy_byteorder(byteorder)
        return np.dtype(str(byteorder + dtype))
    elif isinstance(dtype, dict):
        if not 'dtype' in dtype:
            raise ValueError("Field entry has no dtype: '{0}'".format(dtype))
        name = dtype.get('name', '')
        byteorder = dtype.get('byteorder', byteorder)
        shape = dtype.get('shape')
        dtype = finf_dtype_to_numpy_dtype(dtype['dtype'], byteorder)
        if shape is None:
            return (str(name), dtype)
        else:
            return (str(name), dtype, tuple(shape))
    elif isinstance(dtype, list):
        return np.dtype(
            [finf_dtype_to_numpy_dtype(x, byteorder) for x in dtype])
    raise ValueError("Unknown dtype {0}".format(dtype))


def numpy_byteorder_to_finf_byteorder(byteorder):
    if byteorder == '=':
        return sys.byteorder
    elif byteorder == '<':
        return 'little'
    else:
        return 'big'


def numpy_dtype_to_finf_dtype(dtype):
    dtype = np.dtype(dtype)
    if dtype.names is not None:
        fields = []
        for name in dtype.names:
            field = dtype.fields[name][0]
            d = {}
            d['name'] = name
            field_dtype, byteorder = numpy_dtype_to_finf_dtype(field)
            d['dtype'] = field_dtype
            if byteorder != 'big':
                d['byteorder'] = byteorder
            if field.shape:
                d['shape'] = list(field.shape)
            fields.append(d)
        return fields, numpy_byteorder_to_finf_byteorder(dtype.byteorder)

    elif dtype.subdtype is not None:
        return numpy_dtype_to_finf_dtype(dtype.subdtype[0])

    elif dtype.name in _dtype_names:
        return dtype.name, numpy_byteorder_to_finf_byteorder(dtype.byteorder)
    raise ValueError("Unknown dtype {0}".format(dtype))


class NDArrayType(FinfType):
    name = 'core/ndarray'
    types = [np.ndarray]

    def __init__(self, source, shape, dtype, offset, strides,
                 order, finffile):
        self._finffile = finffile
        self._source = source
        self._block = None
        if isinstance(source, int):
            try:
                self._block = finffile.blocks.get_block(source)
            except ValueError:
                pass
        self._shape = shape
        self._dtype = dtype
        self._offset = offset
        self._strides = strides
        self._order = order
        self._array = None

    def _make_array(self):
        if self._array is None:
            block = self.block
            shape = self.get_actual_shape(
                self._shape, self._strides, self._dtype, len(block))
            self._array = np.ndarray(
                shape, self._dtype, block.data,
                self._offset, self._strides, self._order)
        return self._array

    def __array__(self):
        return self._make_array()

    def __repr__(self):
        # repr alone should not force loading of the data
        if self._array is None:
            return "<array (unloaded) shape: {0} dtype: {1}>".format(
                self._shape, self._dtype)
        return repr(self._array)

    def __str__(self):
        # str alone should not force loading of the data
        if self._array is None:
            return "<array (unloaded) shape: {0} dtype: {1}>".format(
                self._shape, self._dtype)
        return str(self._array)

    def get_actual_shape(self, shape, strides, dtype, block_size):
        """
        Get the actual shape of an array, by computing it against the
        block_size if it contains a ``*``.
        """
        num_stars = shape.count('*')
        if num_stars == 0:
            return shape
        elif num_stars == 1:
            if shape[0] != '*':
                raise ValueError("'*' may only be in first entry of shape")
            if strides is not None:
                stride = strides[0]
            else:
                stride = np.product(shape[1:]) * dtype.itemsize
            missing = int(block_size / stride)
            return [missing] + shape[1:]
        raise ValueError("Invalid shape '{0}'".format(shape))

    @property
    def block(self):
        if self._block is None:
            self._block = self._finffile.blocks.get_block(self._source)
        return self._block

    @property
    def shape(self):
        if '*' in self._shape:
            return tuple(self.get_actual_shape(
                self._shape, self._strides, self._dtype, len(self.block)))
        return tuple(self._shape)

    @property
    def dtype(self):
        if self._array is None:
            return self._dtype
        else:
            return self._array.dtype

    @property
    def __len__(self):
        if self._array is None:
            return self._shape[0]
        else:
            return len(self._array)

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
        base = util.get_array_base(data)
        block = ctx.finffile.blocks.find_or_create_block_for_array(data)
        shape = data.shape
        dtype = data.dtype
        offset = data.ctypes.data - base.ctypes.data
        if data.flags[b'C_CONTIGUOUS']:
            strides = None
        else:
            strides = data.strides

        result = {}
        result['shape'] = list(shape)
        result['source'] = ctx.finffile.blocks.get_source(block)

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

        if old.dtype.fields:
            if not new.dtype.fields:
                assert False, "arrays not equal"
            for a, b in zip(old, new):
                assert_array_equal(a, b)
        else:
            assert_array_equal(old, new)
