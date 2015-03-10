# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np
from numpy.testing import assert_array_equal

from astropy import modeling

from ... import yamlutil

from .basic import TransformType


__all__ = ['AffineType', 'Rotate2DType', 'ZenithalPerspectiveType',
           'GnomonicType', 'StereographicType', 'SlantOrthographicType',
           'CylindricalPerspectiveType', 'CylindricalEqualAreaType',
           'PlateCarreeType', 'MercatorType']


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


class ZenithalType(TransformType):
    @classmethod
    def from_tree_transform(cls, node, ctx, *args):
        if node['direction'] == 'pix2sky':
            return cls.types[0](*args)
        else:
            return cls.types[1](*args)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        if isinstance(model, cls.types[0]):
            return {'direction': 'pix2sky'}
        else:
            return {'direction': 'sky2pix'}

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__


class ZenithalPerspectiveType(ZenithalType):
    name = "transform/zenithal_perspective"
    types = [modeling.projections.Pix2Sky_AZP, modeling.projections.Sky2Pix_AZP]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        mu = node.get('mu', 0.0)
        gamma = node.get('gamma', 0.0)
        if node['direction'] == 'pix2sky':
            return cls.types[0](mu, gamma)
        else:
            return cls.types[1](mu, gamma)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {}
        if isinstance(model, cls.types[0]):
            node['direction'] = 'pix2sky'
        else:
            node['direction'] = 'sky2pix'
        if model.mu != 0.0:
            node['mu'] = model.mu.value
        if model.gamma != 0.0:
            node['gamma'] = model.gamma.value
        return node

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__
        assert a.mu.value == b.mu.value
        assert a.gamma.value == b.gamma.value


class GnomonicType(ZenithalType):
    name = "transform/gnomonic"
    types = [modeling.projections.Pix2Sky_TAN, modeling.projections.Sky2Pix_TAN]


class StereographicType(ZenithalType):
    name = "transform/stereographic"
    types = [modeling.projections.Pix2Sky_STG, modeling.projections.Sky2Pix_STG]


class SlantOrthographicType(ZenithalType):
    name = "transform/slant_orthographic"
    types = [modeling.projections.Pix2Sky_SIN, modeling.projections.Sky2Pix_SIN]


class CylindricalType(TransformType):
    @classmethod
    def from_tree_transform(cls, node, ctx, *args):
        if node['direction'] == 'pix2sky':
            return cls.types[0](*args)
        else:
            return cls.types[1](*args)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        if isinstance(model, cls.types[0]):
            return {'direction': 'pix2sky'}
        else:
            return {'direction': 'sky2pix'}

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__


class CylindricalPerspectiveType(CylindricalType):
    name = "transform/cylindrical_perspective"
    types = [modeling.projections.Pix2Sky_CYP, modeling.projections.Sky2Pix_CYP]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        mu = node.get('mu', 0.0)
        lam = node.get('lambda', 0.0)
        if node['direction'] == 'pix2sky':
            return cls.types[0](mu, lam)
        else:
            return cls.types[1](mu, lam)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {}
        if isinstance(model, cls.types[0]):
            node['direction'] = 'pix2sky'
        else:
            node['direction'] = 'sky2pix'
        if model.mu != 0.0:
            node['mu'] = model.mu.value
        if model.lam != 0.0:
            node['lambda'] = model.lam.value
        return node

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__
        assert a.mu.value == b.mu.value
        assert a.lam.value == b.lam.value


class CylindricalEqualAreaType(CylindricalType):
    name = "transform/cylindrical_equal_area"
    types = [modeling.projections.Pix2Sky_CEA, modeling.projections.Sky2Pix_CEA]

    @classmethod
    def from_tree_transform(cls, node, ctx):
        lam = node.get('lambda', 0.0)
        if node['direction'] == 'pix2sky':
            return cls.types[0](lam)
        else:
            return cls.types[1](lam)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {}
        if isinstance(model, cls.types[0]):
            node['direction'] = 'pix2sky'
        else:
            node['direction'] = 'sky2pix'
        if model.lam != 0.0:
            node['lambda'] = model.lam.value
        return node

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        assert a.__class__ == b.__class__
        assert a.lam.value == b.lam.value


class PlateCarreeType(CylindricalType):
    name = "transforms/plate_carree"
    types = [modeling.projections.Pix2Sky_CAR, modeling.projections.Sky2Pix_CAR]


class MercatorType(CylindricalType):
    name = "transforms/mercator"
    types = [modeling.projections.Pix2Sky_MER, modeling.projections.Sky2Pix_MER]
