# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import six

from ...asdftypes import AsdfType
from . import UnitType


class QuantityType(AsdfType):
    name = 'unit/quantity'
    types = ['astropy.units.Quantity']
    requires = ['astropy']
    version = '1.1.0'

    @classmethod
    def to_tree(cls, quantity, ctx):
        from numpy import isscalar
        from astropy.units import Quantity

        node = {}
        if isinstance(quantity, Quantity):
            value = quantity.value
            # We currently can't handle NDArrays directly, so convert to list
            node['value'] = value if isscalar(value) else list(value)
            node['unit'] = UnitType.to_tree(quantity.unit, ctx)
            return node
        raise TypeError("'{0}' is not a valid Quantity".format(quantity))

    @classmethod
    def from_tree(cls, node, ctx):
        from astropy.units import Quantity

        if isinstance(node, Quantity):
            return node

        unit = UnitType.from_tree(node['unit'], ctx)
        return Quantity(node['value'], unit=unit)
