# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six

from ...finftypes import FinfType

# TODO: Deal with the controlled vocabulary here somehow


class FrameType(six.text_type, FinfType):
    @classmethod
    def from_tree(cls, node, ctx):
        return cls(node)

    @classmethod
    def to_tree(cls, data, ctx):
        return six.text_type(data)
