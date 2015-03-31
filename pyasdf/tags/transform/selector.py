# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np
from numpy.testing import assert_array_equal


from gwcs import selector

from ... import yamlutil

from .basic import TransformType


__all__ = ['SelectorMaskType', 'RegionsSelectorType']

class SelectorMaskType(TransformType):
    name = "transform/selector_mask"
    types = [gwcs.selector.SelectorMask]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        mask = node['mask']
        if matrix.shape != (2, 2):
            raise NotImplementedError(
                "GWCS currently only supports 2x2 masks ")

        return selector.SelectorMask(mask)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {'mask': model.mask.value}
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (a.__class__ == b.__class__)
        assert_array_equal(a.mask, b.mask)


class RegionsSelectorType(TransformType):
    name = "transform/selector_mask"
    types = [gwcs.selector.RegionsSelector]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        inputs = node['inputs']
        outputs = node['outputs']
        mask = node['mask']
        undefined_transform_value = node['undefined_transform_value:']
        selector = node['selector']

        return selector.RegionsSelector(inputs, outputs, selector, mask, undefined_transform_value)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {'inputs': model.inputs, 'outputs': model.outputs,
                'selector': model.selector, 'mask': model.mask,
                'undefined_transform_value': model.undefined_transform_value}
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (a.__class__ == b.__class__)
        assert_array_equal(a.mask, b.mask)
        assert_array_equal(a.inputs, b.inputs)
        assert_array_equal(a.outputs, b.outputs)
        assert_array_equal(a.selector, b.selector)
        assert_array_equal(a.undefined_transform_value, b.undefined_transform_value)




