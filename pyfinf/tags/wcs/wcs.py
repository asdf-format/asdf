# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy import modeling
from astropy.modeling import functional_models
from astropy.modeling import projections

from ...finftypes import FinfType


class WcsType(dict, FinfType):
    name = "wcs/wcs"

    @property
    def pixel_to_world(self):
        if 'pixel_to_world' in self:
            return self['pixel_to_world']
        elif 'world_to_pixel' in self:
            return self['world_to_pixel'].inverse()
        else:
            raise AttributeError(
                "WCS does not have a transform in either direction")

    @property
    def world_to_pixel(self):
        if 'world_to_pixel' in self:
            return self['world_to_pixel']
        elif 'pixel_to_world' in self:
            return self['pixel_to_world'].inverse()
        else:
            raise AttributeError(
                "WCS does not have a transform in either direction")


class SeriesType(FinfType):
    name = "wcs/series"
    types = [modeling.SerialCompositeModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return modeling.SerialCompositeModel(node['transforms'])

    @classmethod
    def to_tree(cls, data, ctx):
        transforms = [
            ctx.to_tree(x) for x in data._transforms]
        return {'transforms': transforms}


class SummedType(FinfType):
    name = "wcs/summed"
    types = [modeling.SummedCompositeModel]

    @classmethod
    def from_tree(cls, node, ctx):
        return modeling.SummedCompositeModel(node['transforms'])

    @classmethod
    def to_tree(cls, data, ctx):
        transforms = [
            ctx.to_tree(x) for x in data._transforms]
        return {'transforms': transforms}


class ShiftType(FinfType):
    name = "wcs/shift"
    types = [functional_models.Shift]

    @classmethod
    def from_tree(cls, node, ctx):
        return functional_models.Shift(node['offsets'])

    @classmethod
    def to_tree(cls, data, ctx):
        return {'offsets': ctx.to_tree(data.offsets.value)}


class ScaleType(FinfType):
    name = "wcs/scale"
    types = [functional_models.Scale]

    @classmethod
    def from_tree(cls, node, ctx):
        return functional_models.Scale(node['factors'])

    @classmethod
    def to_tree(cls, data, ctx):
        return {'factors': ctx.to_tree(data.factors.value)}


class AffineType(FinfType):
    name = "wcs/affine"
    types = [projections.AffineTransformation2D]

    @classmethod
    def from_tree(cls, node, ctx):
        matrix = node['matrix']
        return projections.AffineTransformation2D(matrix[:2, :2], matrix[:2, 2])

    @classmethod
    def to_tree(cls, data, ctx):
        matrix = np.zeros((3, 3))
        matrix[:2, :2] = data.matrix.value
        matrix[:2, 2] = data.translation.value
        return {'matrix': ctx.to_tree(matrix)}


class TangentType(FinfType):
    name = "wcs/tangent"
    types = [projections.Pix2Sky_TAN, projections.Sky2Pix_TAN]

    @classmethod
    def from_tree(cls, node, ctx):
        if node['direction'] == 'forward':
            return projections.Pix2Sky_TAN()
        else:
            return projections.Sky2Pix_TAN()

    @classmethod
    def to_tree(cls, data, ctx):
        if isinstance(data, projections.Pix2Sky_TAN):
            return {'direction': 'forward'}
        else:
            return {'direction': 'backward'}
