# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy import modeling

from ... import yamlutil

from .basic import TransformType


__all__ = ['AffineType', 'Rotate2DType', 'TangentType']


class AffineType(TransformType):
    name = "transform/affine"
    types = [modeling.projections.AffineTransformation2D]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        matrix = node['matrix']
        if matrix.shape != (3, 3):
            raise NotImplementedError(
                "pyasdf currently only supports 3x3 (2D) affine transformation "
                "matrices")

        return modeling.projections.AffineTransformation2D(
            matrix[:2, :2], matrix[2, :2])

    @classmethod
    def to_tree_transform(cls, model, ctx):
        matrix = np.zeros((3, 3))
        matrix[:2, :2] = model.matrix
        matrix[2, :2] = model.translation

        node = {'matrix': matrix}
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)


class Rotate2DType(TransformType):
    name = "transform/rotate2d"
    types = [modeling.rotations.Rotation2D]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        return modeling.rotations.Rotation2D(node['angle'])

    @classmethod
    def to_tree_transform(cls, model, ctx):
        return {'angle': model.angle}


class TangentType(TransformType):
    name = "transform/tangent"
    types = [modeling.projections.Pix2Sky_TAN, modeling.projections.Sky2Pix_TAN]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        if node['direction'] == 'forward':
            return modeling.projections.Pix2Sky_TAN()
        else:
            return modeling.projections.Sky2Pix_TAN()

    @classmethod
    def to_tree_transform(cls, model, ctx):
        if isinstance(model, modeling.Pix2Sky_TAN):
            return {'direction': 'forward'}
        else:
            return {'direction': 'backward'}
