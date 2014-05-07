# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six

from ...finftypes import FinfType


class ComplexType(FinfType):
    name = 'core/complex'
    types = [complex]

    @classmethod
    def to_tree(cls, node, ctx):
        return six.text_type(node)

    @classmethod
    def from_tree(cls, tree, ctx):
        tree = tree.replace('i', 'j').replace('I', 'J')
        return complex(tree)
