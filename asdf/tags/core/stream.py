from .ndarray import numpy_dtype_to_asdf_datatype


class Stream:
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
         ...                      np.array([i] * 1024, np.float64).tobytes())
    """

    def __init__(self, shape, dtype, strides=None):
        self._shape = shape
        self._datatype, self._byteorder = numpy_dtype_to_asdf_datatype(dtype)
        self._strides = strides
        self._array = None

    def _make_array(self):
        self._array = None

    def __repr__(self):
        return f"Stream({self._shape}, {self._datatype}, strides={self._strides})"

    def __str__(self):
        return str(self.__repr__())
