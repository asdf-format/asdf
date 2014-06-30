# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from ...finftypes import FinfType
from ..core.constant import Constant

from astropy import modeling


__all__ = ['RemapAxes', 'RemapAxesType', 'SeriesType']


def _all_none(s):
    for x in s:
        if x is not None:
            return False
    return True


# TODO: RemapAxes belongs in astropy.modeling
class RemapAxes(modeling.Model):
    def __init__(self, mapping, n_inputs=None):
        for x in mapping:
            if not isinstance(x, (int, Constant)):
                raise TypeError(
                    "Invalid value in mapping: {0}".format(x))
        self._mapping = mapping
        if n_inputs is None:
            self.n_inputs = self._calculate_n_inputs(mapping)
        else:
            self.n_inputs = n_inputs
        self.n_outputs = len(mapping)

        super(RemapAxes, self).__init__()

    @staticmethod
    def _calculate_n_inputs(mapping):
        max_axis = -1
        for x in mapping:
            if isinstance(x, int):
                max_axis = max(max_axis, x)
        return max_axis + 1

    @property
    def mapping(self):
        return self._mapping

    def __call__(self, *data):
        shuffled = []
        for i, x in enumerate(self._mapping):
            if isinstance(x, int):
                shuffled.append(data[x])
            elif isinstance(x, Constant):
                shuffled.append(x.value)
        return shuffled


class RemapAxesType(FinfType):
    name = 'transform/remap_axes'
    types = [RemapAxes]

    @classmethod
    def from_tree(cls, node, ctx):
        if isinstance(node, dict):
            return RemapAxes(node['mapping'], node.get('n_inputs'))
        elif isinstance(node, list):
            return RemapAxes(node)

    @classmethod
    def to_tree(cls, data, ctx):
        mapping = [ctx.to_tree(x) for x in data.mapping]
        if data.n_inputs != data._calculate_n_inputs(data.mapping):
            return {'mapping': mapping, 'n_inputs': data.n_inputs}
        else:
            return mapping


# TODO: SeparableModel belongs in astropy.modeling
class SeparableModel(modeling.Model):
    def __init__(self, transforms):
        super(SeparableModel, self).__init__()
        self._transforms = transforms
        self.n_inputs = sum(x.n_inputs for x in transforms)
        self.n_outputs = sum(x.n_outputs for x in transforms)

    @property
    def transforms(self):
        return self._transforms

    def __call__(self, *data):
        outputs = []
        offset = 0
        for tr in self._transforms:
            outputs.extend(tr(*data[offset:offset+tr.n_inputs]))
            offset += tr.n_inputs
        return outputs


class SeparableType(FinfType):
    name = 'transform/separable'
    types = [SeparableModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return SeparableModel(node)

    @classmethod
    def to_tree(cls, data, ctx):
        return [ctx.to_tree(x) for x in data._transforms]


class SeriesType(FinfType):
    name = 'transform/series'
    types = [modeling.SerialCompositeModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return modeling.SerialCompositeModel(node)

    @classmethod
    def to_tree(cls, data, ctx):
        if not (_all_none(data._inmap) and _all_none(data._outmap)):
            raise ValueError(
                "WCS can not serialize a SerialCompositeModel with in_map "
                "or out_map")
        return [ctx.to_tree(x) for x in data._transforms]


class SummedType(FinfType):
    name = 'transform/summed'
    types = [modeling.SummedCompositeModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return modeling.SummedCompositeModel(node)

    @classmethod
    def to_tree(cls, data, ctx):
        if not (_all_none(data._inmap) and _all_none(data._outmap)):
            raise ValueError(
                "WCS can not serialize a SummedCompositeModel with in_map "
                "or out_map")
        return [ctx.to_tree(x) for x in data._transforms]


# TODO: IdentityModel belongs in astropy.modeling
class IdentityModel(modeling.Model):
    def __init__(self, n_dims=1):
        self.n_inputs = self.n_outputs = n_dims

    def __call__(self, *data):
        outputs = [x.copy() for x in data]
        if len(outputs) == 1:
            return outputs[0]
        return outputs


class IdentityType(FinfType):
    name = 'transform/identity'
    types = [IdentityModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return IdentityModel(node.get('n_dims', 1))

    @classmethod
    def to_tree(cls, data, ctx):
        if data.n_inputs != 1:
            return {'n_dims': data.n_inputs}
        return {}


class GenericModel(modeling.Model):
    def __init__(self, n_inputs, n_outputs):
        self.n_inputs = n_inputs
        self.n_outputs = n_inputs

    def __call__(self, *data):
        pass


class GenericType(FinfType):
    name = 'transform/generic'
    types = [GenericModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return GenericModel(node['n_inputs'], node['n_outputs'])

    @classmethod
    def to_tree(cls, data, ctx):
        return {'n_inputs': data.n_inputs,
                'n_outputs': data.n_outputs}
