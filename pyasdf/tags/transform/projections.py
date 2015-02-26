# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np
from numpy.testing import assert_array_equal

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

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (isinstance(a, modeling.projections.AffineTransformation2D) and
                isinstance(b, modeling.projections.AffineTransformation2D))
        assert_array_equal(a.matrix, b.matrix)
        assert_array_equal(a.translation, b.translation)


class Rotate2DType(TransformType):
    name = "transform/rotate2d"
    types = [modeling.rotations.Rotation2D]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        return modeling.rotations.Rotation2D(node['angle'])

    @classmethod
    def to_tree_transform(cls, model, ctx):
        return {'angle': model.angle.value}

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (isinstance(a, modeling.rotations.Rotation2D) and
                isinstance(b, modeling.rotations.Rotation2D))
        assert_array_equal(a.angle, b.angle)


class RotateSky(TransformType):
    name = "transform/rotate3d"
    types = [modeling.rotations.RotateNative2Celestial,
             modeling.rotations.RotateCelestial2Native]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        if node['direction'] == 'native2celestial':
            return modeling.rotations.RotateNative2Celestial(node["phi"],
                                                             node["theta"],
                                                             node["psi"])
        else:
            return modeling.rotations.RotateCelestial2Native(node["phi"],
                                                             node["theta"],
                                                             node["psi"])


    @classmethod
    def to_tree_transform(cls, model, ctx):
        if isinstance(model, modeling.rotations.RotateNative2Celestial):
            direction = "native2celestial"
        else:
            direction = "celestial2native"

        return {"phi": model.phi.value,
                "theta": model.theta.value,
                "psi": model.psi.value,
                "direction": direction
                }

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert (isinstance(a, modeling.rotations.RotateNative2Celestial) and
                isinstance(b, modeling.rotations.RotateNative2Celestial))
        assert_array_equal(a.phi, b.phi)
        assert_array_equal(a.psi, b.psi)
        assert_array_equal(a.theta, b.theta)


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
        if isinstance(model, modeling.projections.Pix2Sky_TAN):
            return {'direction': 'forward'}
        else:
            return {'direction': 'backward'}

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__
