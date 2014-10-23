# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import modeling
from astropy.modeling.core import _CompoundModel, _CompoundModelMeta

from ... import tagged
from ... import yamlutil

from .basic import TransformType


__all__ = ['CompoundType']


_operator_to_tag_mapping = {
    '+': 'add',
    '-': 'subtract',
    '*': 'multiply',
    '/': 'divide',
    '**': 'power',
    '|': 'concatenate',
    '&': 'join'
}


_tag_to_operator_mapping = dict(
    (v, k) for (k, v) in _operator_to_tag_mapping.items())


class CompoundType(TransformType):
    name = ['transform/add',
            'transform/subtract',
            'transform/multiply',
            'transform/divide',
            'transform/power',
            'transform/concatenate',
            'transform/join']
    types = [_CompoundModel]

    @classmethod
    def from_tree_tagged(cls, node, ctx):
        tag = node.tag[node.tag.rfind('/')+1:]

        oper = _tag_to_operator_mapping[tag]
        left = yamlutil.tagged_tree_to_custom_tree(
            node['forward'][0], ctx)
        if not isinstance(left, modeling.Model):
            raise TypeError("Unknown model type '{0}'".format(
                node['forward'][0].tag))
        right = yamlutil.tagged_tree_to_custom_tree(
            node['forward'][1], ctx)
        if not isinstance(right, modeling.Model):
            raise TypeError("Unknown model type '{0}'".format(
                node['forward'][1].tag))
        model = _CompoundModelMeta._from_operator(oper, left, right)

        cls._assign_inverse(model, node, ctx)
        return model

    @classmethod
    def to_tree_tagged(cls, model, ctx):
        node = {
            'forward': [
                yamlutil.custom_tree_to_tagged_tree(model._tree.left),
                yamlutil.custom_tree_to_tagged_tree(model._tree.right)
                ]
            }

        try:
            tag_name = _operator_to_tag_mapping[model._tree.value]
        except KeyError:
            raise ValueError("Unknown operator '{0}'".format(model._tree.value))

        cls._get_inverse(model, node, ctx)

        node = tagged.tag_object(node, cls.make_yaml_tag(tag_name))
        return node
