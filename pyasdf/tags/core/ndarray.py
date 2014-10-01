# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import sys

import numpy as np
from numpy import ma

from astropy.extern import six

from ...asdftypes import AsdfType
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
    'complex64': 'c8',
    'complex128': 'c16',
    'bool8': 'b1'
}


_string_dtype_names = {
    'ascii': 'S',
    'ucs4': 'U'
}


def asdf_byteorder_to_numpy_byteorder(byteorder):
    if byteorder == 'big':
        return '>'
    elif byteorder == 'little':
        return '<'
    raise ValueError("Invalid ASDF byteorder '{0}'".format(byteorder))


def asdf_dtype_to_numpy_dtype(dtype, byteorder):
    if isinstance(dtype, six.text_type) and dtype in _dtype_names:
        dtype = _dtype_names[dtype]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        return np.dtype(str(byteorder + dtype))
    elif (isinstance(dtype, list) and
          len(dtype) == 2 and
          isinstance(dtype[0], six.text_type) and
          isinstance(dtype[1], int) and
          dtype[0] in _string_dtype_names):
        length = dtype[1]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        dtype = str(byteorder) + str(_string_dtype_names[dtype[0]]) + str(length)
        return np.dtype(dtype)
    elif isinstance(dtype, dict):
        if not 'dtype' in dtype:
            raise ValueError("Field entry has no dtype: '{0}'".format(dtype))
        name = dtype.get('name', '')
        byteorder = dtype.get('byteorder', byteorder)
        shape = dtype.get('shape')
        dtype = asdf_dtype_to_numpy_dtype(dtype['dtype'], byteorder)
        if shape is None:
            return (str(name), dtype)
        else:
            return (str(name), dtype, tuple(shape))
    elif isinstance(dtype, list):
        super_dtype = []
        for x in dtype:
            x = asdf_dtype_to_numpy_dtype(x, byteorder)
            if isinstance(x, np.dtype):
                super_dtype.append((str(''), x))
            else:
                super_dtype.append(x)
        return np.dtype(super_dtype)
    raise ValueError("Unknown dtype {0}".format(dtype))


def numpy_byteorder_to_asdf_byteorder(byteorder):
    if byteorder == '=':
        return sys.byteorder
    elif byteorder == '<':
        return 'little'
    else:
        return 'big'


def numpy_dtype_to_asdf_dtype(dtype):
    dtype = np.dtype(dtype)
    if dtype.names is not None:
        fields = []
        for name in dtype.names:
            field = dtype.fields[name][0]
            d = {}
            d['name'] = name
            field_dtype, byteorder = numpy_dtype_to_asdf_dtype(field)
            d['dtype'] = field_dtype
            if byteorder != 'big':
                d['byteorder'] = byteorder
            if field.shape:
                d['shape'] = list(field.shape)
            fields.append(d)
        return fields, numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.subdtype is not None:
        return numpy_dtype_to_asdf_dtype(dtype.subdtype[0])

    elif dtype.name in _dtype_names:
        return dtype.name, numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.name == 'bool':
        return 'bool8', numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.name.startswith('string') or dtype.name.startswith('bytes'):
        return ['ascii', dtype.itemsize], 'big'

    elif dtype.name.startswith('unicode') or dtype.name.startswith('str'):
        return (['ucs4', int(dtype.itemsize / 4)],
                numpy_byteorder_to_asdf_byteorder(dtype.byteorder))

    raise ValueError("Unknown dtype {0}".format(dtype))


class NDArrayType(AsdfType):
    name = 'core/ndarray'
    types = [np.ndarray, ma.MaskedArray]

    def __init__(self, source, shape, dtype, offset, strides,
                 order, mask, asdffile):
        self._asdffile = asdffile
        self._source = source
        self._block = None
        self._array = None
        self._mask = mask
        if isinstance(source, int):
            try:
                self._block = asdffile.blocks.get_block(source)
            except ValueError:
                pass
        elif isinstance(source, list):
            self._array = np.array(source)
            self._array = self._apply_mask(self._array, self._mask)
            self._block = asdffile.blocks.add_inline(self._array)
        self._shape = shape
        self._dtype = dtype
        self._offset = offset
        self._strides = strides
        self._order = order

    def _make_array(self):
        if self._array is None:
            block = self.block
            shape = self.get_actual_shape(
                self._shape, self._strides, self._dtype, len(block))
            self._array = np.ndarray(
                shape, self._dtype, block.data,
                self._offset, self._strides, self._order)
            self._array = self._apply_mask(self._array, self._mask)
        return self._array

    def _apply_mask(self, array, mask):
        if isinstance(mask, (np.ndarray, NDArrayType)):
            return ma.array(array, mask=mask)
        elif np.isscalar(mask):
            if np.isnan(mask):
                return ma.array(array, mask=np.isnan(array))
            else:
                return ma.masked_values(array, mask)
        return array

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
            self._block = self._asdffile.blocks.get_block(self._source)
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
        # We need to ignore __array_struct__, or unicode arrays end up
        # getting "double casted" and upsized.  This also reduces the
        # number of array creations in the general case.
        if attr == '__array_struct__':
            raise AttributeError()
        return getattr(self._make_array(), attr)

    def __getitem__(self, item):
        return self._make_array()[item]

    def __setitem__(self, item, val):
        self._make_array()[item] = val

    @classmethod
    def from_tree(cls, node, ctx):
        if isinstance(node, list):
            return cls(node, None, None, None, None, None, None, ctx.asdffile)

        elif isinstance(node, dict):
            shape = node.get('shape', None)
            dtype = asdf_dtype_to_numpy_dtype(
                node.get('dtype', 'uint8'), node.get('byteorder', 'big'))
            source = node.get('source')
            data = node.get('data')
            if source and data:
                raise ValueError("Both source and data my not be provided.")
            if data:
                source = data
            offset = node.get('offset', 0)
            strides = node.get('strides', None)
            mask = node.get('mask', None)

            return cls(source, shape, dtype, offset, strides, 'C', mask, ctx.asdffile)

        raise TypeError("Invalid ndarray description.")

    @classmethod
    def pre_write(cls, data, ctx):
        # Find all of the used data buffers so we can add or rearrange
        # them if necessary
        if isinstance(data, np.ndarray):
            ctx.asdffile.blocks.find_or_create_block_for_array(data)

    @classmethod
    def to_tree(cls, data, ctx):
        base = util.get_array_base(data)
        block = ctx.asdffile.blocks.find_or_create_block_for_array(data)
        shape = data.shape
        dtype = data.dtype
        offset = data.ctypes.data - base.ctypes.data
        if data.flags[b'C_CONTIGUOUS']:
            strides = None
        else:
            strides = data.strides

        result = {}
        result['shape'] = list(shape)
        if block.block_type == 'streamed':
            result['shape'][0] = '*'

        dtype, byteorder = numpy_dtype_to_asdf_dtype(dtype)

        if block.block_type == 'inline':
            result['data'] = data.tolist()
            result['dtype'] = dtype
        else:
            result['source'] = ctx.asdffile.blocks.get_source(block)
            result['dtype'] = dtype
            if byteorder != 'big':
                result['byteorder'] = byteorder

            if offset > 0:
                result['offset'] = offset

            if strides is not None:
                result['strides'] = list(strides)

        if isinstance(data, ma.MaskedArray):
            if np.any(data.mask):
                result['mask'] = ctx.to_tree(data.mask)

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
