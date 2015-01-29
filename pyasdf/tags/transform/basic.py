# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import modeling
from astropy.modeling import mappings
from astropy.modeling import functional_models

from ...asdftypes import AsdfType
from ... import yamlutil

__all__ = ['TransformType', 'IdentityType', 'ConstantType',
           'GenericModel', 'GenericType']


class TransformType(AsdfType):
    name = "transform/transform"

    @classmethod
    def _get_inverse(cls, model, node, ctx):
        if getattr(model, '_custom_inverse', None) is not None:
            node['inverse'] = model._custom_inverse

    @classmethod
    def _assign_inverse(cls, model, node, ctx):
        if 'inverse' in node:
            model.inverse = yamlutil.custom_tree_to_tagged_tree(
                node['inverse'], ctx)

    @classmethod
    def from_tree_transform(cls, node, ctx):
        raise NotImplementedError("Must be implemented in TransformType subclasses")

    @classmethod
    def from_tree(cls, node, ctx):
        model = cls.from_tree_transform(node, ctx)
        cls._assign_inverse(model, node, ctx)
        return model

    @classmethod
    def to_tree_transform(cls, model, ctx):
        raise NotImplementedError("Must be implemented in TransformType subclasses")

    @classmethod
    def to_tree(cls, model, ctx):
        node = cls.to_tree_transform(model, ctx)
        TransformType._get_inverse(model, node, ctx)
        return node


class IdentityType(TransformType):
    name = "transform/identity"
    types = [mappings.Identity]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        return mappings.Identity(node.get('n_dims', 1))

    @classmethod
    def to_tree_transform(cls, data, ctx):
        node = {}
        if data.n_inputs != 1:
            node['n_dims'] = data.n_inputs
        return node

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (isinstance(a, mappings.Identity) and
                isinstance(b, mappings.Identity) and
                a.n_inputs == b.n_inputs)


class ConstantType(TransformType):
    name = "transform/constant"
    types = [functional_models.Const1D]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        return functional_models.Const1D(node['value'])

    @classmethod
    def to_tree_transform(cls, data, ctx):
        return {
            'value': data.amplitude
        }


# TODO: This is just here for bootstrapping and will go away eventually
class GenericModel(mappings.Mapping):
    def __init__(self, n_inputs, n_outputs):
        mapping = tuple(range(n_inputs))
        super(GenericModel, self).__init__(mapping)
        self._outputs = tuple('x' + str(idx) for idx in range(self.n_outputs + 1))


class GenericType(TransformType):
    name = "transform/generic"
    types = [GenericModel]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        return GenericModel(
            node['n_inputs'], node['n_outputs'])

    @classmethod
    def to_tree_transform(cls, data, ctx):
        return {
            'n_inputs': data.n_inputs,
            'n_outputs': data.n_outputs
        }
