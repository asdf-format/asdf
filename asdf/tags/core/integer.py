from numbers import Integral


class IntegerType:
    """
    Enables the storage of arbitrarily large integer values

    The ASDF Standard mandates that integer literals in the tree can be no
    larger than 64 bits. Use of this class enables the storage of arbitrarily
    large integer values.

    When reading files that contain arbitrarily large integers, the values that
    are restored in the tree will be raw Python `int` instances.

    Parameters
    ----------

    value: `numbers.Integral`
        A Python integral value (e.g. `int` or `numpy.integer`)

    storage_type: `str`, optional
        Optionally overrides the storage type of the array used to represent
        the integer value. Valid values are "internal" (the default) and
        "inline"

    Examples
    --------

    >>> import asdf
    >>> import random
    >>> # Create a large integer value
    >>> largeval = random.getrandbits(100)
    >>> # Store the large integer value to the tree using asdf.IntegerType
    >>> tree = dict(largeval=asdf.IntegerType(largeval))
    >>> with asdf.AsdfFile(tree) as af:
    ...     af.write_to('largeval.asdf')
    >>> with asdf.open('largeval.asdf') as aa:
    ...     assert aa['largeval'] == largeval
    """

    def __init__(self, value, storage_type="internal"):
        if storage_type not in ["internal", "inline"]:
            msg = f"storage_type '{storage_type}' is not a recognized storage type"
            raise ValueError(msg)
        self._value = value
        self._sign = "-" if value < 0 else "+"
        self._storage = storage_type

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        if isinstance(other, Integral):
            return self._value == other

        if isinstance(other, IntegerType):
            return self._value == other._value

        msg = f"Can't compare IntegralType to unknown type: {type(other)}"
        raise ValueError(msg)

    def __repr__(self):
        return f"IntegerType({self._value})"
