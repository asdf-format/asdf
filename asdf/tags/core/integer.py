import warnings
from numbers import Integral

from asdf.exceptions import AsdfDeprecationWarning


class IntegerType:
    """
    Enables the storage of arbitrarily large integer values

    The ASDF Standard mandates that integer literals in the tree can be no
    larger than 64 bits. Use of this class enables the storage of arbitrarily
    large integer values.

    When reading files that contain arbitrarily large integers, the values that
    are restored in the tree will be raw Python `int` instances.

    DEPRECATED.  Large integer values are now handled automatically and need
    no special wrapper class.  Use asdf.get_config().array_inline_threshold
    to customize the array storage type.

    Parameters
    ----------

    value: `numbers.Integral`
        A Python integral value (e.g. `int` or `numpy.integer`)

    storage_type: `str`, optional
        This argument is now ignored.  Use asdf.get_config().array_inline_threshold
        to customize the array storage type.
    """

    def __init__(self, value, storage_type=None):
        warnings.warn(
            "IntegerType is deprecated.  Large integer values are now handled automatically "
            "and need no special wrapper class.  Use asdf.get_config().array_inline_threshold "
            "to customize the array storage type.",
            AsdfDeprecationWarning,
        )

        if storage_type is not None:
            warnings.warn(
                "The storage_type argument to IntegerType is now ignored.  Use "
                "asdf.get_config().array_inline_threshold to customize the array "
                "storage type.",
                AsdfDeprecationWarning,
            )

        self._value = value

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        if isinstance(other, Integral):
            return self._value == other

        if isinstance(other, IntegerType):
            return self._value == other._value

        msg = f"Can't compare IntegerType to unknown type: {type(other)}"
        raise ValueError(msg)

    def __repr__(self):
        return f"IntegerType({self._value})"
