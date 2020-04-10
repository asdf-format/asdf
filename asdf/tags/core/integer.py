# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from numbers import Integral

import numpy as np

from ...types import AsdfType


class IntegerType(AsdfType):
    """
    Enables the storage of arbitrarily large integer values

    The ASDF Standard mandates that integer literals in the tree can be no
    larger than 52 bits. Use of this class enables the storage of arbitrarily
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

    name = 'core/integer'
    version = '1.0.0'

    _value_cache = dict()

    def __init__(self, value, storage_type='internal'):
        assert storage_type in ['internal', 'inline'], "Invalid storage type given"
        self._value = value
        self._sign = '-' if value < 0 else '+'
        self._storage = storage_type

    @classmethod
    def to_tree(cls, node, ctx):

        if ctx not in cls._value_cache:
            cls._value_cache[ctx] = dict()

        abs_value = int(np.abs(node._value))

        # If the same value has already been stored, reuse the array
        if abs_value in cls._value_cache[ctx]:
            array = cls._value_cache[ctx][abs_value]
        else:
            # pack integer value into 32-bit words
            words = []
            value = abs_value
            while value > 0:
                words.append(value & 0xffffffff)
                value >>= 32

            array = np.array(words, dtype=np.uint32)
            if node._storage == 'internal':
                cls._value_cache[ctx][abs_value] = array

        tree = dict()
        ctx.set_array_storage(array, node._storage)
        tree['words'] = array
        tree['sign'] = node._sign
        tree['string'] = str(int(node._value))

        return tree

    @classmethod
    def from_tree(cls, tree, ctx):

        value = 0
        for x in tree['words'][::-1]:
            value <<= 32
            value |= int(x)

        if tree['sign'] == '-':
            value = -value

        return IntegerType(value)

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __eq__(self, other):
        if isinstance(other, Integral):
            return self._value == other
        elif isinstance(other, IntegerType):
            return self._value == other._value
        else:
            raise ValueError(
                "Can't compare IntegralType to unknown type: {}".format(
                    type(other)))

    def __repr__(self):
        return "IntegerType({})".format(self._value)
