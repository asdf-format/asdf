# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import six

from ...yamlutil import custom_tree_to_tagged_tree
from ...asdftypes import AsdfType
from . import UnitType
from ..core import NDArrayType


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
            node['value'] = custom_tree_to_tagged_tree(quantity.value, ctx)
            node['unit'] = custom_tree_to_tagged_tree(quantity.unit, ctx)
            return node
        raise TypeError("'{0}' is not a valid Quantity".format(quantity))

    @classmethod
    def from_tree(cls, node, ctx):
        from astropy.units import Quantity

        if isinstance(node, Quantity):
            return node

        unit = UnitType.from_tree(node['unit'], ctx)
        value = node['value']
        if isinstance(value, NDArrayType):
            value = value._make_array()
        return Quantity(value, unit=unit)
