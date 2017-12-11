# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


from ...asdftypes import AsdfType


class Constant(object):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class ConstantType(AsdfType):
    name = 'core/constant'
    types = [Constant]

    @classmethod
    def from_tree(self, node, ctx):
        return Constant(node)

    @classmethod
    def to_tree(self, data, ctx):
        return data.value
