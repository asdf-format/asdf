# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True
    from astropy.modeling import mappings
    from astropy.utils import minversion
    ASTROPY_12 = minversion(astropy, "1.2")

from ...asdftypes import AsdfType
from ... import tagged
from ... import yamlutil

__all__ = ['TransformType', 'IdentityType', 'ConstantType',
           'DomainType']


class TransformType(AsdfType):
    requires = ['astropy']

    @classmethod
    def _from_tree_base_transform_members(cls, model, node, ctx):
        if 'inverse' in node:
            model.inverse = yamlutil.tagged_tree_to_custom_tree(
                node['inverse'], ctx)

        if 'name' in node:
            model = model.rename(node['name'])

        # TODO: When astropy.modeling has built-in support for
        # domains, save this somewhere else.
        if 'domain' in node:
            model.meta['domain'] = node['domain']

        return model

    @classmethod
    def from_tree_transform(cls, node, ctx):
        raise NotImplementedError(
            "Must be implemented in TransformType subclasses")

    @classmethod
    def from_tree(cls, node, ctx):
        model = cls.from_tree_transform(node, ctx)
        model = cls._from_tree_base_transform_members(model, node, ctx)
        return model

    @classmethod
    def _to_tree_base_transform_members(cls, model, node, ctx):
        if ASTROPY_12:
            if getattr(model, '_user_inverse', None) is not None:
                node['inverse'] = yamlutil.custom_tree_to_tagged_tree(
                model._user_inverse, ctx)
        else:
            if getattr(model, '_custom_inverse', None) is not None:
                node['inverse'] = yamlutil.custom_tree_to_tagged_tree(
                model._custom_inverse, ctx)

        if model.name is not None:
            node['name'] = model.name

        # TODO: When astropy.modeling has built-in support for
        # domains, get this from somewhere else.
        domain = model.meta.get('domain')
        if domain:
            domain = [tagged.tag_object(DomainType.yaml_tag, x, ctx=ctx)
                      for x in domain]
            node['domain'] = domain

    @classmethod
    def to_tree_transform(cls, model, ctx):
        raise NotImplementedError("Must be implemented in TransformType subclasses")

    @classmethod
    def to_tree(cls, model, ctx):
        node = cls.to_tree_transform(model, ctx)
        cls._to_tree_base_transform_members(model, node, ctx)
        return node

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        from ...tests.helpers import assert_tree_match
        assert a.name == b.name
        # TODO: Assert inverses are the same


class IdentityType(TransformType):
    name = "transform/identity"
    types = ['astropy.modeling.mappings.Identity']

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
        from astropy.modeling import mappings
        # TODO: If models become comparable themselves, remove this.
        TransformType.assert_equal(a, b)
        assert (isinstance(a, mappings.Identity) and
                isinstance(b, mappings.Identity) and
                a.n_inputs == b.n_inputs)


class ConstantType(TransformType):
    name = "transform/constant"
    types = ['astropy.modeling.functional_models.Const1D']

    @classmethod
    def from_tree_transform(cls, node, ctx):
        from astropy.modeling import functional_models

        return functional_models.Const1D(node['value'])

    @classmethod
    def to_tree_transform(cls, data, ctx):
        return {
            'value': data.amplitude.value
        }


class DomainType(AsdfType):
    name = "transform/domain"

    @classmethod
    def from_tree(cls, node, ctx):
        return node

    @classmethod
    def to_tree(cls, data, ctx):
        return data


# TODO: This is just here for bootstrapping and will go away eventually
if HAS_ASTROPY:
    class GenericModel(mappings.Mapping):
        def __init__(self, n_inputs, n_outputs):
            mapping = tuple(range(n_inputs))
            super(GenericModel, self).__init__(mapping)
            self._outputs = tuple('x' + str(idx) for idx in range(self.n_outputs + 1))


class GenericType(TransformType):
    name = "transform/generic"
    if HAS_ASTROPY:
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
