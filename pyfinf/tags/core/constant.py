# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from ...finftypes import FinfType


class Constant(object):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class ConstantType(FinfType):
    name = 'core/constant'
    types = [Constant]

    @classmethod
    def from_tree(self, node, ctx):
        return Constant(node)

    @classmethod
    def to_tree(self, data, ctx):
        return data.value
