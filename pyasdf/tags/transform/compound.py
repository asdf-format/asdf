# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import modeling
from astropy.modeling.core import _CompoundModel, _CompoundModelMeta

from ... import tagged
from ... import yamlutil
from ...tests.helpers import assert_tree_match

from .basic import TransformType


__all__ = ['CompoundType']


_operator_to_tag_mapping = {
    '+'  : 'add',
    '-'  : 'subtract',
    '*'  : 'multiply',
    '/'  : 'divide',
    '**' : 'power',
    '|'  : 'concatenate',
    '&'  : 'join'
}


_tag_to_method_mapping = {
    'add'         : '__add__',
    'subtract'    : '__sub__',
    'multiply'    : '__mul__',
    'divide'      : '__truediv__',
    'power'       : '__pow__',
    'concatenate' : '__or__',
    'join'        : '__and__'
}


class CompoundType(TransformType):
    name = ['transform/' + x for x in _tag_to_method_mapping.keys()]
    types = [_CompoundModel]

    @classmethod
    def from_tree_tagged(cls, node, ctx):
        tag = node.tag[node.tag.rfind('/')+1:]

        oper = _tag_to_method_mapping[tag]
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
        model = getattr(left, oper)(right)

        cls._assign_inverse(model, node, ctx)
        return model

    @classmethod
    def _to_tree_from_model_tree(cls, tree, ctx):
        if tree.left.isleaf:
            left = yamlutil.custom_tree_to_tagged_tree(
                tree.left.value, ctx)
        else:
            left = cls._to_tree_from_model_tree(tree.left, ctx)

        if tree.right.isleaf:
            right = yamlutil.custom_tree_to_tagged_tree(
                tree.right.value, ctx)
        else:
            right = cls._to_tree_from_model_tree(tree.right, ctx)

        node = {
            'forward': [left, right]
        }

        try:
            tag_name = 'transform/' + _operator_to_tag_mapping[tree.value]
        except KeyError:
            raise ValueError("Unknown operator '{0}'".format(tree.value))

        # TODO: Correctly handle inverse transforms

        node = tagged.tag_object(cls.make_yaml_tag(tag_name), node)
        return node

    @classmethod
    def to_tree_tagged(cls, model, ctx):
        return cls._to_tree_from_model_tree(model._tree, ctx)

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert_tree_match(a._tree.left.value, b._tree.left.value)
        assert_tree_match(a._tree.right.value, b._tree.right.value)
        assert a._tree.value == b._tree.value
