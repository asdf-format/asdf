# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import sys

import numpy as np
from numpy import ma

from jsonschema import ValidationError

from ...asdftypes import AsdfType
from ... import schema
from ... import util
from ... import yamlutil


_datatype_names = {
    'int8'       : 'i1',
    'int16'      : 'i2',
    'int32'      : 'i4',
    'int64'      : 'i8',
    'uint8'      : 'u1',
    'uint16'     : 'u2',
    'uint32'     : 'u4',
    'uint64'     : 'u8',
    'float32'    : 'f4',
    'float64'    : 'f8',
    'complex64'  : 'c8',
    'complex128' : 'c16',
    'bool8'      : 'b1'
}


_string_datatype_names = {
    'ascii' : 'S',
    'ucs4'  : 'U'
}


def asdf_byteorder_to_numpy_byteorder(byteorder):
    if byteorder == 'big':
        return '>'
    elif byteorder == 'little':
        return '<'
    raise ValueError("Invalid ASDF byteorder '{0}'".format(byteorder))


def asdf_datatype_to_numpy_dtype(datatype, byteorder=None):
    if byteorder is None:
        byteorder = sys.byteorder
    if isinstance(datatype, str) and datatype in _datatype_names:
        datatype = _datatype_names[datatype]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        return np.dtype(str(byteorder + datatype))
    elif (isinstance(datatype, list) and
          len(datatype) == 2 and
          isinstance(datatype[0], str) and
          isinstance(datatype[1], int) and
          datatype[0] in _string_datatype_names):
        length = datatype[1]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        datatype = str(byteorder) + str(_string_datatype_names[datatype[0]]) + str(length)
        return np.dtype(datatype)
    elif isinstance(datatype, dict):
        if 'datatype' not in datatype:
            raise ValueError("Field entry has no datatype: '{0}'".format(datatype))
        name = datatype.get('name', '')
        byteorder = datatype.get('byteorder', byteorder)
        shape = datatype.get('shape')
        datatype = asdf_datatype_to_numpy_dtype(datatype['datatype'], byteorder)
        if shape is None:
            return (str(name), datatype)
        else:
            return (str(name), datatype, tuple(shape))
    elif isinstance(datatype, list):
        datatype_list = []
        for i, subdatatype in enumerate(datatype):
            np_dtype = asdf_datatype_to_numpy_dtype(subdatatype, byteorder)
            if isinstance(np_dtype, tuple):
                datatype_list.append(np_dtype)
            elif isinstance(np_dtype, np.dtype):
                datatype_list.append((str(''), np_dtype))
            else:
                raise RuntimeError("Error parsing asdf datatype")
        return np.dtype(datatype_list)
    raise ValueError("Unknown datatype {0}".format(datatype))


def numpy_byteorder_to_asdf_byteorder(byteorder):
    if byteorder == '=':
        return sys.byteorder
    elif byteorder == '<':
        return 'little'
    else:
        return 'big'


def numpy_dtype_to_asdf_datatype(dtype, include_byteorder=True):
    dtype = np.dtype(dtype)
    if dtype.names is not None:
        fields = []
        for name in dtype.names:
            field = dtype.fields[name][0]
            d = {}
            d['name'] = name
            field_dtype, byteorder = numpy_dtype_to_asdf_datatype(field)
            d['datatype'] = field_dtype
            if include_byteorder:
                d['byteorder'] = byteorder
            if field.shape:
                d['shape'] = list(field.shape)
            fields.append(d)
        return fields, numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.subdtype is not None:
        return numpy_dtype_to_asdf_datatype(dtype.subdtype[0])

    elif dtype.name in _datatype_names:
        return dtype.name, numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.name == 'bool':
        return 'bool8', numpy_byteorder_to_asdf_byteorder(dtype.byteorder)

    elif dtype.name.startswith('string') or dtype.name.startswith('bytes'):
        return ['ascii', dtype.itemsize], 'big'

    elif dtype.name.startswith('unicode') or dtype.name.startswith('str'):
        return (['ucs4', int(dtype.itemsize / 4)],
                numpy_byteorder_to_asdf_byteorder(dtype.byteorder))

    raise ValueError("Unknown dtype {0}".format(dtype))


def inline_data_asarray(inline, dtype=None):
    # np.asarray doesn't handle structured arrays unless the innermost
    # elements are tuples.  To do that, we drill down the first
    # element of each level until we find a single item that
    # successfully converts to a scalar of the expected structured
    # dtype.  Then we go through and convert everything at that level
    # to a tuple.  This probably breaks for nested structured dtypes,
    # but it's probably good enough for now.  It also won't work with
    # object dtypes, but ASDF explicitly excludes those, so we're ok
    # there.
    if dtype is not None and dtype.fields is not None:
        def find_innermost_match(l, depth=0):
            if not isinstance(l, list) or not len(l):
                raise ValueError(
                    "data can not be converted to structured array")
            try:
                np.asarray(tuple(l), dtype=dtype)
            except ValueError:
                return find_innermost_match(l[0], depth + 1)
            else:
                return depth
        depth = find_innermost_match(inline)

        def convert_to_tuples(l, data_depth, depth=0):
            if data_depth == depth:
                return tuple(l)
            else:
                return [convert_to_tuples(x, data_depth, depth+1) for x in l]
        inline = convert_to_tuples(inline, depth)

        return np.asarray(inline, dtype=dtype)
    else:
        def handle_mask(inline):
            if isinstance(inline, list):
                if None in inline:
                    inline_array = np.asarray(inline)
                    nones = np.equal(inline_array, None)
                    return np.ma.array(np.where(nones, 0, inline),
                                       mask=nones)
                else:
                    return [handle_mask(x) for x in inline]
            return inline
        inline = handle_mask(inline)

        inline = np.ma.asarray(inline, dtype=dtype)
        if not ma.is_masked(inline):
            return inline.data
        else:
            return inline


def numpy_array_to_list(array):
    def tolist(x):
        if isinstance(x, (np.ndarray, NDArrayType)):
            if x.dtype.char == 'S':
                x = x.astype('U').tolist()
            else:
                x = x.tolist()

        if isinstance(x, (list, tuple)):
            return [tolist(y) for y in x]
        else:
            return x

    def ascii_to_unicode(x):
        # Convert byte string arrays to unicode string arrays, since YAML
        # doesn't handle the former.
        if isinstance(x, list):
            return [ascii_to_unicode(y) for y in x]
        elif isinstance(x, bytes):
            return x.decode('ascii')
        else:
            return x

    result = ascii_to_unicode(tolist(array))

    schema.validate_large_literals(result)

    return result


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

        if isinstance(source, list):
            self._array = inline_data_asarray(source, dtype)
            self._array = self._apply_mask(self._array, self._mask)
            self._block = asdffile.blocks.add_inline(self._array)
            if shape is not None:
                if ((shape[0] == '*' and
                     self._array.shape[1:] != tuple(shape[1:])) or
                    (self._array.shape != tuple(shape))):
                    raise ValueError(
                        "inline data doesn't match the given shape")

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
            # Use "mask.view()" here so the underlying possibly
            # memmapped mask array is freed properly when the masked
            # array goes away.
            array = ma.array(array, mask=mask.view())
            # assert util.get_array_base(array.mask) is util.get_array_base(mask)
            return array
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
            return "<{0} (unloaded) shape: {1} dtype: {2}>".format(
                'array' if self._mask is None else 'masked array',
                self._shape, self._dtype)
        return repr(self._array)

    def __str__(self):
        # str alone should not force loading of the data
        if self._array is None:
            return "<{0} (unloaded) shape: {1} dtype: {2}>".format(
                'array' if self._mask is None else 'masked array',
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
        if self._shape is None:
            return self.__array__().shape
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

    @classmethod
    def from_tree(cls, node, ctx):
        if isinstance(node, list):
            return cls(node, None, None, None, None, None, None, ctx)

        elif isinstance(node, dict):
            source = node.get('source')
            data = node.get('data')
            if source and data:
                raise ValueError(
                    "Both source and data may not be provided "
                    "at the same time")
            if data:
                source = data
            shape = node.get('shape', None)
            if data is not None:
                byteorder = sys.byteorder
            else:
                byteorder = node['byteorder']
            if 'datatype' in node:
                dtype = asdf_datatype_to_numpy_dtype(
                    node['datatype'], byteorder)
            else:
                dtype = None
            offset = node.get('offset', 0)
            strides = node.get('strides', None)
            mask = node.get('mask', None)

            return cls(source, shape, dtype, offset, strides, 'C', mask, ctx)

        raise TypeError("Invalid ndarray description.")

    @classmethod
    def reserve_blocks(cls, data, ctx):
        # Find all of the used data buffers so we can add or rearrange
        # them if necessary
        if isinstance(data, np.ndarray):
            yield ctx.blocks.find_or_create_block_for_array(data, ctx)
        elif isinstance(data, NDArrayType):
            yield data.block

    @classmethod
    def to_tree(cls, data, ctx):
        base = util.get_array_base(data)
        shape = data.shape
        dtype = data.dtype
        offset = data.ctypes.data - base.ctypes.data
        strides = None

        if not data.flags.c_contiguous:
            # We do not want to encode strides for broadcasted arrays
            if not all(data.strides):
                data = np.ascontiguousarray(data)
            else:
                strides = data.strides

        block = ctx.blocks.find_or_create_block_for_array(data, ctx)

        result = {}

        result['shape'] = list(shape)
        if block.array_storage == 'streamed':
            result['shape'][0] = '*'

        dtype, byteorder = numpy_dtype_to_asdf_datatype(
            dtype, include_byteorder=(block.array_storage != 'inline'))

        byteorder = block.override_byteorder(byteorder)

        if block.array_storage == 'inline':
            listdata = numpy_array_to_list(data)
            result['data'] = yamlutil.custom_tree_to_tagged_tree(
                listdata, ctx)
            result['datatype'] = dtype
        else:
            result['shape'] = list(shape)
            if block.array_storage == 'streamed':
                result['shape'][0] = '*'

            result['source'] = ctx.blocks.get_source(block)
            result['datatype'] = dtype
            result['byteorder'] = byteorder

            if offset > 0:
                result['offset'] = offset

            if strides is not None:
                result['strides'] = list(strides)

        if isinstance(data, ma.MaskedArray):
            if np.any(data.mask):
                if block.array_storage == 'inline':
                    ctx.blocks.set_array_storage(ctx.blocks[data.mask], 'inline')
                result['mask'] = yamlutil.custom_tree_to_tagged_tree(
                    data.mask, ctx)

        return result

    @classmethod
    def _assert_equality(cls, old, new, func):
        if old.dtype.fields:
            if not new.dtype.fields:
                assert False, "arrays not equal"
            for a, b in zip(old, new):
                cls._assert_equality(a, b, func)
        else:
            old = old.__array__()
            new = new.__array__()
            if old.dtype.char in 'SU':
                if old.dtype.char == 'S':
                    old = old.astype('U')
                if new.dtype.char == 'S':
                    new = new.astype('U')
                old = old.tolist()
                new = new.tolist()
                assert old == new
            else:
                func(old, new)

    @classmethod
    def assert_equal(cls, old, new):
        from numpy.testing import assert_array_equal

        cls._assert_equality(old, new, assert_array_equal)

    @classmethod
    def assert_allclose(cls, old, new):
        from numpy.testing import assert_allclose, assert_array_equal

        if (old.dtype.kind in 'iu' and
            new.dtype.kind in 'iu'):
            cls._assert_equality(old, new, assert_array_equal)
        else:
            cls._assert_equality(old, new, assert_allclose)

    @classmethod
    def copy_to_new_asdf(cls, node, asdffile):
        if isinstance(node, NDArrayType):
            array = node._make_array()
            asdffile.blocks.set_array_storage(asdffile.blocks[array],
                                              node.block.array_storage)
            return node._make_array()
        return node


def _make_operation(name):
    def __operation__(self, *args):
        return getattr(self._make_array(), name)(*args)
    return __operation__


for op in [
        '__neg__', '__pos__', '__abs__', '__invert__', '__complex__',
        '__int__', '__long__', '__float__', '__oct__', '__hex__',
        '__lt__', '__le__', '__eq__', '__ne__', '__gt__', '__ge__',
        '__cmp__', '__rcmp__', '__add__', '__sub__', '__mul__',
        '__floordiv__', '__mod__', '__divmod__', '__pow__',
        '__lshift__', '__rshift__', '__and__', '__xor__', '__or__',
        '__div__', '__truediv__', '__radd__', '__rsub__', '__rmul__',
        '__rdiv__', '__rtruediv__', '__rfloordiv__', '__rmod__',
        '__rdivmod__', '__rpow__', '__rlshift__', '__rrshift__',
        '__rand__', '__rxor__', '__ror__', '__iadd__', '__isub__',
        '__imul__', '__idiv__', '__itruediv__', '__ifloordiv__',
        '__imod__', '__ipow__', '__ilshift__', '__irshift__',
        '__iand__', '__ixor__', '__ior__', '__getitem__',
        '__delitem__', '__contains__', '__setitem__']:
    setattr(NDArrayType, op, _make_operation(op))


def _get_ndim(instance):
    if isinstance(instance, list):
        array = inline_data_asarray(instance)
        return array.ndim
    elif isinstance(instance, dict):
        if 'shape' in instance:
            return len(instance['shape'])
        elif 'data' in instance:
            array = inline_data_asarray(instance['data'])
            return array.ndim
    elif isinstance(instance, (np.ndarray, NDArrayType)):
        return len(instance.shape)


def validate_ndim(validator, ndim, instance, schema):
    in_ndim = _get_ndim(instance)

    if in_ndim != ndim:
        yield ValidationError(
            "Wrong number of dimensions: Expected {0}, got {1}".format(
                ndim, in_ndim), instance=repr(instance))


def validate_max_ndim(validator, max_ndim, instance, schema):
    in_ndim = _get_ndim(instance)

    if in_ndim > max_ndim:
        yield ValidationError(
            "Wrong number of dimensions: Expected max of {0}, got {1}".format(
                max_ndim, in_ndim), instance=repr(instance))


def validate_datatype(validator, datatype, instance, schema):
    if isinstance(instance, list):
        array = inline_data_asarray(instance)
        in_datatype, _ = numpy_dtype_to_asdf_datatype(array.dtype)
    elif isinstance(instance, dict):
        if 'datatype' in instance:
            in_datatype = instance['datatype']
        elif 'data' in instance:
            array = inline_data_asarray(instance['data'])
            in_datatype, _ = numpy_dtype_to_asdf_datatype(array.dtype)
        else:
            raise ValidationError("Not an array")
    elif isinstance(instance, (np.ndarray, NDArrayType)):
        in_datatype, _ = numpy_dtype_to_asdf_datatype(instance.dtype)
    else:
        raise ValidationError("Not an array")

    if datatype == in_datatype:
        return

    if schema.get('exact_datatype', False):
        yield ValidationError(
            "Expected datatype '{0}', got '{1}'".format(
                datatype, in_datatype))

    np_datatype = asdf_datatype_to_numpy_dtype(datatype)
    np_in_datatype = asdf_datatype_to_numpy_dtype(in_datatype)

    if not np_datatype.fields:
        if np_in_datatype.fields:
            yield ValidationError(
                "Expected scalar datatype '{0}', got '{1}'".format(
                    datatype, in_datatype))

        if not np.can_cast(np_in_datatype, np_datatype, 'safe'):
            yield ValidationError(
                "Can not safely cast from '{0}' to '{1}' ".format(
                    in_datatype, datatype))

    else:
        if not np_in_datatype.fields:
            yield ValidationError(
                "Expected structured datatype '{0}', got '{1}'".format(
                    datatype, in_datatype))

        if len(np_in_datatype.fields) != len(np_datatype.fields):
            yield ValidationError(
                "Mismatch in number of columns: "
                "Expected {0}, got {1}".format(
                    len(datatype), len(in_datatype)))

        for i in range(len(np_datatype.fields)):
            in_type = np_in_datatype[i]
            out_type = np_datatype[i]
            if not np.can_cast(in_type, out_type, 'safe'):
                yield ValidationError(
                    "Can not safely cast to expected datatype: "
                    "Expected {0}, got {1}".format(
                        numpy_dtype_to_asdf_datatype(out_type)[0],
                        numpy_dtype_to_asdf_datatype(in_type)[0]))


NDArrayType.validators = {
    'ndim': validate_ndim,
    'max_ndim': validate_max_ndim,
    'datatype': validate_datatype
}
