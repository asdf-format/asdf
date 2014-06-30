# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

from astropy.modeling import projections, rotations

from ...finftypes import FinfType


__all__ = ['AffineType', 'TangentType']


class TangentType(FinfType):
    name = "transform/tangent"
    types = [projections.Pix2Sky_TAN, projections.Sky2Pix_TAN]

    @classmethod
    def from_tree(cls, node, ctx):
        if node.get('direction', 'forward') == 'forward':
            return projections.Pix2Sky_TAN()
        else:
            return projections.Sky2Pix_TAN()

    @classmethod
    def to_tree(cls, data, ctx):
        if isinstance(data, projections.Pix2Sky_TAN):
            return {'direction': 'forward'}
        else:
            return {'direction': 'backward'}


# TODO: We should replace this with a more generic n-dimensional
# affine transformation.

class AffineType(FinfType):
    name = "transform/affine"
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
        ctx.finffile.set_block_type(matrix, 'inline')
        return {'matrix': ctx.to_tree(matrix)}


class Rotate2DType(FinfType):
    name = "transform/rotate2d"
    types = [rotations.Rotation2D]

    @classmethod
    def from_tree(cls, node, ctx):
        return rotations.Rotation2D(node['angle'])

    @classmethod
    def to_tree(cls, data, ctx):
        return {'angle': data.angle}
