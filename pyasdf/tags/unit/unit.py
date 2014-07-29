# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from astropy.extern import six
from astropy import units as u

from ...asdftypes import AsdfType


class UnitType(AsdfType):
    name = 'unit/unit'
    types = [u.UnitBase]

    @classmethod
    def to_tree(cls, node, ctx):
        if isinstance(node, six.string_types):
            node = u.Unit(node, format='vounit', parse_strict='warn')
        if isinstance(node, u.UnitBase):
            return node.to_string(format='vounit')
        raise TypeError("'{0}' is not a valid unit".format(node))

    @classmethod
    def from_tree(cls, node, ctx):
        return u.Unit(node, format='vounit', parse_strict='silent')
