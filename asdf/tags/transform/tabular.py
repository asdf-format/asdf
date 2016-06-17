# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np
from numpy.testing import assert_array_equal
from ... import yamlutil

from .basic import TransformType

__all__ = ['TabularType']


class TabularType(TransformType):
    import astropy
    name = "transform/tabular"
    types = [astropy.modeling.tabular.Tabular2D,
             astropy.modeling.tabular.Tabular1D,
             astropy.modeling.tabular._Tabular
             ]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        from astropy.modeling import models

        lookup_table = node.pop("lookup_table")
        dim = lookup_table.ndim
        name = node.get('name', None)
        tabular_class = models.tabular_model(dim, name)
        fill_value = node.pop("fill_value", None)
        points = np.asarray(node['points'])
        model = tabular_class(points=points, lookup_table=lookup_table,
                              method=node['method'], bounds_error=node['bounds_error'],
                              fill_value=fill_value)

        return model

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {}
        node["fill_value"] = model.fill_value
        node["lookup_table"] = model.lookup_table
        node["points"] = model.points
        node["method"] = str(model.method)
        node["bounds_error"] = model.bounds_error
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)

    @classmethod
    def assert_equal(cls, a, b):
        assert_array_equal(a.lookup_table, b.lookup_table)
        assert_array_equal(a.points, b.points)
        assert (a.method == b.method)
        if a.fill_value is None:
            assert (b.fill_value is None)
        else:
            assert(a.fill_value == b.fill_value)
        assert(a.bounds_error == b.bounds_error)
