import mmap
import sys

import numpy as np
from numpy import ma

from asdf import util
from asdf._jsonschema import ValidationError

_STRUCTURED_DATATYPE_KEYS = {"name", "datatype", "byteorder", "shape"}

_datatype_names = {
    "int8": "i1",
    "int16": "i2",
    "int32": "i4",
    "int64": "i8",
    "uint8": "u1",
    "uint16": "u2",
    "uint32": "u4",
    "uint64": "u8",
    "float16": "f2",
    "float32": "f4",
    "float64": "f8",
    "complex64": "c8",
    "complex128": "c16",
    "bool8": "b1",
}


_string_datatype_names = {"ascii": "S", "ucs4": "U"}


def asdf_byteorder_to_numpy_byteorder(byteorder):
    if byteorder == "big":
        return ">"

    if byteorder == "little":
        return "<"

    msg = f"Invalid ASDF byteorder '{byteorder}'"
    raise ValueError(msg)


def asdf_datatype_to_numpy_dtype(datatype, byteorder=None):
    if byteorder is None:
        byteorder = sys.byteorder

    if isinstance(datatype, str) and datatype in _datatype_names:
        datatype = _datatype_names[datatype]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        return np.dtype(str(byteorder + datatype))

    if (
        isinstance(datatype, list)
        and len(datatype) == 2
        and isinstance(datatype[0], str)
        and isinstance(datatype[1], int)
        and datatype[0] in _string_datatype_names
    ):
        length = datatype[1]
        byteorder = asdf_byteorder_to_numpy_byteorder(byteorder)
        datatype = str(byteorder) + str(_string_datatype_names[datatype[0]]) + str(length)

        return np.dtype(datatype)

    if isinstance(datatype, dict):
        if "datatype" not in datatype:
            msg = f"Field entry has no datatype: '{datatype}'"
            raise ValueError(msg)

        name = datatype.get("name", "")
        byteorder = datatype.get("byteorder", byteorder)
        shape = datatype.get("shape")
        datatype = asdf_datatype_to_numpy_dtype(datatype["datatype"], byteorder)

        if shape is None:
            return (str(name), datatype)

        return (str(name), datatype, tuple(shape))

    if isinstance(datatype, list):
        datatype_list = []
        for subdatatype in datatype:
            np_dtype = asdf_datatype_to_numpy_dtype(subdatatype, byteorder)
            if isinstance(np_dtype, tuple):
                datatype_list.append(np_dtype)

            elif isinstance(np_dtype, np.dtype):
                datatype_list.append(("", np_dtype))

            else:
                msg = "Error parsing asdf datatype"
                raise RuntimeError(msg)

        return np.dtype(datatype_list)

    msg = f"Unknown datatype {datatype}"
    raise ValueError(msg)


def numpy_byteorder_to_asdf_byteorder(byteorder, override=None):
    if override is not None:
        return override

    if byteorder == "=":
        return sys.byteorder

    if byteorder == "<":
        return "little"

    return "big"


def numpy_dtype_to_asdf_datatype(dtype, include_byteorder=True, override_byteorder=None):
    dtype = np.dtype(dtype)
    if dtype.names is not None:
        fields = []
        for name in dtype.names:
            field = dtype.fields[name][0]
            d = {}
            d["name"] = name
            field_dtype, byteorder = numpy_dtype_to_asdf_datatype(field, override_byteorder=override_byteorder)
            d["datatype"] = field_dtype
            if include_byteorder:
                d["byteorder"] = byteorder
            if field.shape:
                d["shape"] = list(field.shape)
            fields.append(d)
        return fields, numpy_byteorder_to_asdf_byteorder(dtype.byteorder, override=override_byteorder)

    if dtype.subdtype is not None:
        return numpy_dtype_to_asdf_datatype(dtype.subdtype[0], override_byteorder=override_byteorder)

    if dtype.name in _datatype_names:
        return dtype.name, numpy_byteorder_to_asdf_byteorder(dtype.byteorder, override=override_byteorder)

    if dtype.name == "bool":
        return "bool8", numpy_byteorder_to_asdf_byteorder(dtype.byteorder, override=override_byteorder)

    if dtype.name.startswith("string") or dtype.name.startswith("bytes"):
        return ["ascii", dtype.itemsize], "big"

    if dtype.name.startswith("unicode") or dtype.name.startswith("str"):
        return (
            ["ucs4", int(dtype.itemsize / 4)],
            numpy_byteorder_to_asdf_byteorder(dtype.byteorder, override=override_byteorder),
        )

    msg = f"Unknown dtype {dtype}"
    raise ValueError(msg)


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

        def find_innermost_match(line, depth=0):
            if not isinstance(line, list) or not len(line):
                msg = "data can not be converted to structured array"
                raise ValueError(msg)
            try:
                np.asarray(tuple(line), dtype=dtype)
            except ValueError:
                return find_innermost_match(line[0], depth + 1)
            else:
                return depth

        depth = find_innermost_match(inline)

        def convert_to_tuples(line, data_depth, depth=0):
            if data_depth == depth:
                return tuple(line)

            return [convert_to_tuples(x, data_depth, depth + 1) for x in line]

        inline = convert_to_tuples(inline, depth)

        return np.asarray(inline, dtype=dtype)

    def handle_mask(inline):
        if isinstance(inline, list):
            if None in inline:
                inline_array = np.asarray(inline)
                nones = np.equal(inline_array, None)
                return np.ma.array(np.where(nones, 0, inline), mask=nones)

            return [handle_mask(x) for x in inline]

        return inline

    inline = handle_mask(inline)

    inline = np.ma.asarray(inline, dtype=dtype)
    if not ma.is_masked(inline):
        return inline.data

    return inline


def numpy_array_to_list(array):
    def tolist(x):
        if isinstance(x, (np.ndarray, NDArrayType)):
            x = x.astype("U").tolist() if x.dtype.char == "S" else x.tolist()

        if isinstance(x, (list, tuple)):
            return [tolist(y) for y in x]

        return x

    def ascii_to_unicode(x):
        # Convert byte string arrays to unicode string arrays, since YAML
        # doesn't handle the former.
        if isinstance(x, list):
            return [ascii_to_unicode(y) for y in x]

        if isinstance(x, bytes):
            return x.decode("ascii")

        return x

    return ascii_to_unicode(tolist(array))


class NDArrayType:
    def __init__(self, source, shape, dtype, offset, strides, order, mask, data_callback=None):
        self._source = source
        self._data_callback = data_callback
        self._array = None
        self._mask = mask

        if isinstance(source, list):
            self._array = inline_data_asarray(source, dtype)
            self._array = self._apply_mask(self._array, self._mask)
            # single element structured arrays can have shape == ()
            # https://github.com/asdf-format/asdf/issues/1540
            if shape is not None and (
                self._array.shape != tuple(shape)
                or (len(shape) and shape[0] == "*" and self._array.shape[1:] != tuple(shape[1:]))
            ):
                msg = "inline data doesn't match the given shape"
                raise ValueError(msg)

        self._shape = shape
        self._dtype = dtype
        self._offset = offset
        self._strides = strides
        self._order = order

    def _make_array(self):
        # If the ASDF file has been updated in-place, then there's
        # a chance that the block's original data object has been
        # closed and replaced.  We need to check here and re-generate
        # the array if necessary, otherwise we risk segfaults when
        # memory mapping.
        if self._array is not None:
            base = util.get_array_base(self._array)
            if isinstance(base, np.memmap) and isinstance(base.base, mmap.mmap):
                # check if the underlying mmap matches the one generated by generic_io
                try:
                    fd = self._data_callback(_attr="_fd")()
                except AttributeError:
                    # external blocks do not have a '_fd' and don't need to be updated
                    fd = None
                if fd is not None:
                    if getattr(fd, "_mmap", None) is not base.base:
                        self._array = None
                    del fd

        if self._array is None:
            if isinstance(self._source, str):
                # we need to keep _source as a str to allow stdatamodels to
                # support AsdfInFits
                data = self._data_callback()
            else:
                # cached data is used here so that multiple NDArrayTypes will all use
                # the same base array
                data = self._data_callback(_attr="cached_data")

            if hasattr(data, "base") and isinstance(data.base, mmap.mmap) and data.base.closed:
                msg = "ASDF file has already been closed. Can not get the data."
                raise OSError(msg)

            # compute shape (streaming blocks have '0' data size in the block header)
            shape = self.get_actual_shape(
                self._shape,
                self._strides,
                self._dtype,
                data.size,
            )
            self._array = np.ndarray(shape, self._dtype, data, self._offset, self._strides, self._order)
            self._array = self._apply_mask(self._array, self._mask)
        return self._array

    def _apply_mask(self, array, mask):
        if isinstance(mask, (np.ndarray, NDArrayType)):
            # Use "mask.view()" here so the underlying possibly
            # memmapped mask array is freed properly when the masked
            # array goes away.
            array = ma.array(array, mask=mask.view())
            return array

        if np.isscalar(mask):
            if np.isnan(mask):
                return ma.array(array, mask=np.isnan(array))

            return ma.masked_values(array, mask)

        return array

    def __array__(self):
        return self._make_array()

    def __repr__(self):
        # repr alone should not force loading of the data
        if self._array is None:
            return (
                f"<{'array' if self._mask is None else 'masked array'} "
                f"(unloaded) shape: {self._shape} dtype: {self._dtype}>"
            )
        return repr(self._make_array())

    def __str__(self):
        # str alone should not force loading of the data
        if self._array is None:
            return (
                f"<{'array' if self._mask is None else 'masked array'} "
                f"(unloaded) shape: {self._shape} dtype: {self._dtype}>"
            )
        return str(self._make_array())

    def get_actual_shape(self, shape, strides, dtype, block_size):
        """
        Get the actual shape of an array, by computing it against the
        block_size if it contains a ``*``.
        """
        num_stars = shape.count("*")
        if num_stars == 0:
            return shape

        if num_stars == 1:
            if shape[0] != "*":
                msg = "'*' may only be in first entry of shape"
                raise ValueError(msg)

            stride = strides[0] if strides is not None else np.prod(shape[1:]) * dtype.itemsize

            missing = int(block_size / stride)
            return [missing] + shape[1:]

        msg = f"Invalid shape '{shape}'"
        raise ValueError(msg)

    @property
    def shape(self):
        if self._shape is None or self._array is not None or "*" in self._shape:
            # streamed blocks have a '0' data_size in the header so we
            # need to make the array to get the shape
            return self.__array__().shape
        return tuple(self._shape)

    @property
    def dtype(self):
        if self._array is None:
            return self._dtype

        return self._make_array().dtype

    def __len__(self):
        if self._array is None:
            return self._shape[0]

        return len(self._make_array())

    def __getattr__(self, attr):
        # We need to ignore __array_struct__, or unicode arrays end up
        # getting "double casted" and upsized.  This also reduces the
        # number of array creations in the general case.
        if attr == "__array_struct__":
            raise AttributeError
        # AsdfFile.info will call hasattr(obj, "__asdf_traverse__") which
        # will trigger this method, making the array, and loading the array
        # data. Intercept this and raise AttributeError as this class does
        # not support that method
        # see: https://github.com/asdf-format/asdf/issues/1553
        if attr == "__asdf_traverse__":
            raise AttributeError
        return getattr(self._make_array(), attr)

    def __setitem__(self, *args):
        # This workaround appears to be necessary in order to avoid a segfault
        # in the case that array assignment causes an exception. The segfault
        # originates from the call to __repr__ inside the traceback report.
        try:
            self._make_array().__setitem__(*args)
        except Exception:
            self._array = None

            raise


def _make_operation(name):
    def operation(self, *args):
        return getattr(self._make_array(), name)(*args)

    return operation


for op in [
    "__neg__",
    "__pos__",
    "__abs__",
    "__invert__",
    "__complex__",
    "__int__",
    "__long__",
    "__float__",
    "__oct__",
    "__hex__",
    "__lt__",
    "__le__",
    "__eq__",
    "__ne__",
    "__gt__",
    "__ge__",
    "__cmp__",
    "__rcmp__",
    "__add__",
    "__sub__",
    "__mul__",
    "__floordiv__",
    "__mod__",
    "__divmod__",
    "__pow__",
    "__lshift__",
    "__rshift__",
    "__and__",
    "__xor__",
    "__or__",
    "__div__",
    "__truediv__",
    "__radd__",
    "__rsub__",
    "__rmul__",
    "__rdiv__",
    "__rtruediv__",
    "__rfloordiv__",
    "__rmod__",
    "__rdivmod__",
    "__rpow__",
    "__rlshift__",
    "__rrshift__",
    "__rand__",
    "__rxor__",
    "__ror__",
    "__iadd__",
    "__isub__",
    "__imul__",
    "__idiv__",
    "__itruediv__",
    "__ifloordiv__",
    "__imod__",
    "__ipow__",
    "__ilshift__",
    "__irshift__",
    "__iand__",
    "__ixor__",
    "__ior__",
    "__getitem__",
    "__delitem__",
    "__contains__",
]:
    setattr(NDArrayType, op, _make_operation(op))


def _get_ndim(instance):
    if isinstance(instance, list):
        array = inline_data_asarray(instance)
        return array.ndim

    if isinstance(instance, dict):
        if "shape" in instance:
            return len(instance["shape"])

        if "data" in instance:
            array = inline_data_asarray(instance["data"])
            return array.ndim

    if isinstance(instance, (np.ndarray, NDArrayType)):
        return len(instance.shape)

    return None


def validate_ndim(validator, ndim, instance, schema):
    in_ndim = _get_ndim(instance)

    if in_ndim != ndim:
        yield ValidationError(f"Wrong number of dimensions: Expected {ndim}, got {in_ndim}", instance=repr(instance))


def validate_max_ndim(validator, max_ndim, instance, schema):
    in_ndim = _get_ndim(instance)

    if in_ndim is None or in_ndim > max_ndim:
        yield ValidationError(
            f"Wrong number of dimensions: Expected max of {max_ndim}, got {in_ndim}",
            instance=repr(instance),
        )


def validate_datatype(validator, datatype, instance, schema):
    if isinstance(instance, list):
        array = inline_data_asarray(instance)
        in_datatype, _ = numpy_dtype_to_asdf_datatype(array.dtype)
    elif isinstance(instance, dict):
        if "datatype" in instance:
            in_datatype = instance["datatype"]
        elif "data" in instance:
            array = inline_data_asarray(instance["data"])
            in_datatype, _ = numpy_dtype_to_asdf_datatype(array.dtype)
        else:
            msg = "Not an array"
            yield ValidationError(msg)
            return
    elif isinstance(instance, (np.ndarray, NDArrayType)):
        in_datatype, _ = numpy_dtype_to_asdf_datatype(instance.dtype)
    else:
        msg = "Not an array"
        yield ValidationError(msg)
        return

    # We are only concerned with some fields from the datatype
    # object in the schema so if the schema datatype is structured
    # copy the datatype and drop the irrelevant fields
    # name datatype byteorder shape
    if isinstance(datatype, list) and len(datatype) and isinstance(datatype[0], dict):
        datatype = [{k: v for k, v in subitem.items() if k in _STRUCTURED_DATATYPE_KEYS} for subitem in datatype]

    if datatype == in_datatype:
        return

    if schema.get("exact_datatype", False):
        yield ValidationError(f"Expected datatype '{datatype}', got '{in_datatype}'")
        return

    np_datatype = asdf_datatype_to_numpy_dtype(datatype)
    np_in_datatype = asdf_datatype_to_numpy_dtype(in_datatype)

    if not np_datatype.fields:
        if np_in_datatype.fields:
            yield ValidationError(f"Expected scalar datatype '{datatype}', got '{in_datatype}'")
            return

        if not np.can_cast(np_in_datatype, np_datatype, "safe"):
            yield ValidationError(f"Can not safely cast from '{in_datatype}' to '{datatype}' ")
            return

    else:
        if not np_in_datatype.fields:
            yield ValidationError(f"Expected structured datatype '{datatype}', got '{in_datatype}'")
            return

        if len(np_in_datatype.fields) != len(np_datatype.fields):
            yield ValidationError(f"Mismatch in number of columns: Expected {len(datatype)}, got {len(in_datatype)}")
            return

        for i in range(len(np_datatype.fields)):
            in_type = np_in_datatype[i]
            out_type = np_datatype[i]
            if not np.can_cast(in_type, out_type, "safe"):
                yield ValidationError(
                    "Can not safely cast to expected datatype: "
                    f"Expected {numpy_dtype_to_asdf_datatype(out_type)[0]}, "
                    f"got {numpy_dtype_to_asdf_datatype(in_type)[0]}",
                )
                return
