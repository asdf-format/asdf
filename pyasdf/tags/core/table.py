# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy import table

from ...asdftypes import AsdfType
from ... import yamlutil


class TableType(AsdfType):
    name = 'core/table'
    types = [table.Table]

    @classmethod
    def from_tree(cls, node, ctx):
        columns = [
            yamlutil.tagged_tree_to_custom_tree(c, ctx)
            for c in node['columns']
        ]

        return table.Table(columns, meta=node.get('meta', {}))

    @classmethod
    def to_tree(cls, data, ctx):
        columns = []
        for name in data.colnames:
            column = yamlutil.custom_tree_to_tagged_tree(
                data.columns[name], ctx)
            columns.append(column)

        node = {'columns': columns}
        if data.meta:
            node['meta'] = data.meta

        return node

    @classmethod
    def assert_equal(cls, old, new):
        from .ndarray import NDArrayType

        assert old.meta == new.meta
        NDArrayType.assert_equal(np.array(old), np.array(new))


class ColumnType(AsdfType):
    name = 'core/column'
    types = [table.Column, table.MaskedColumn]

    @classmethod
    def from_tree(cls, node, ctx):
        data = yamlutil.tagged_tree_to_custom_tree(
            node['data'], ctx)
        name = node['name']
        description = node.get('description')
        unit = node.get('unit')
        meta = node.get('meta', None)

        return table.Column(
            data=data, name=name, description=description, unit=unit,
            meta=meta)

    @classmethod
    def to_tree(cls, data, ctx):
        node = {
            'data': yamlutil.custom_tree_to_tagged_tree(
                data.data, ctx),
            'name': data.name
        }
        if data.description:
            node['description'] = data.description
        if data.unit:
            node['unit'] = yamlutil.custom_tree_to_tagged_tree(
                data.unit, ctx)
        if data.meta:
            node['meta'] = data.meta

        return node

    @classmethod
    def assert_equal(cls, old, new):
        from .ndarray import NDArrayType

        assert old.meta == new.meta
        assert old.description == new.description
        assert old.unit == new.unit

        NDArrayType.assert_equal(np.array(old), np.array(new))
