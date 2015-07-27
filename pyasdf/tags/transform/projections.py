# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from numpy.testing import assert_array_equal

from ... import yamlutil

from .basic import TransformType


__all__ = ['AffineType', 'Rotate2DType', 'Rotate3DType', 'ZenithalPerspectiveType',
           'GnomonicType', 'StereographicType', 'SlantOrthographicType',
           'CylindricalPerspectiveType', 'CylindricalEqualAreaType',
           'PlateCarreeType', 'MercatorType']


class AffineType(TransformType):
    name = "transform/affine"
    types = ['astropy.modeling.projections.AffineTransformation2D']

    @classmethod
    def from_tree_transform(cls, node, ctx):
        from astropy import modeling

        matrix = node['matrix']
        translation = node['translation']
        if matrix.shape != (2, 2):
            raise NotImplementedError(
                "pyasdf currently only supports 2x2 (2D) rotation transformation "
                "matrices")
        if translation.shape != (2,):
            raise NotImplementedError(
                "pyasdf currently only supports 2D translation transformations.")

        return modeling.projections.AffineTransformation2D(
            matrix=matrix, translation=translation)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {'matrix': model.matrix.value, 'translation': model.translation.value}
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        TransformType.assert_equal(a, b)
        assert (a.__class__ == b.__class__)
        assert_array_equal(a.matrix, b.matrix)
        assert_array_equal(a.translation, b.translation)


class Rotate2DType(TransformType):
    name = "transform/rotate2d"
    types = ['astropy.modeling.rotations.Rotation2D']

    @classmethod
    def from_tree_transform(cls, node, ctx):
        from astropy import modeling

        return modeling.rotations.Rotation2D(node['angle'])

    @classmethod
    def to_tree_transform(cls, model, ctx):
        return {'angle': model.angle.value}

    @classmethod
    def assert_equal(cls, a, b):
        from astropy import modeling

        # TODO: If models become comparable themselves, remove this.
        TransformType.assert_equal(a, b)
        assert (isinstance(a, modeling.rotations.Rotation2D) and
                isinstance(b, modeling.rotations.Rotation2D))
        assert_array_equal(a.angle, b.angle)


class Rotate3DType(TransformType):
    name = "transform/rotate3d"
    types = ['astropy.modeling.rotations.RotateNative2Celestial',
             'astropy.modeling.rotations.RotateCelestial2Native',
             'astropy.modeling.rotations.EulerAngleRotation']

    @classmethod
    def from_tree_transform(cls, node, ctx):
        from astropy import modeling

        if node['direction'] == 'native2celestial':
            return modeling.rotations.RotateNative2Celestial(node["phi"],
                                                             node["theta"],
                                                             node["psi"])
        elif node['direction'] == 'celestial2native':
            return modeling.rotations.RotateCelestial2Native(node["phi"],
                                                             node["theta"],
                                                             node["psi"])
        else:
            return modeling.rotations.EulerAngleRotation(node["phi"],
                                                         node["theta"],
                                                         node["psi"],
                                                         axes_order=node["direction"])


    @classmethod
    def to_tree_transform(cls, model, ctx):
        from astropy import modeling

        if isinstance(model, modeling.rotations.RotateNative2Celestial):
            return {"phi": model.lon.value,
                    "theta": model.lat.value,
                    "psi": model.lon_pole.value,
                    "direction": "native2celestial"
                    }
        elif isinstance(model, modeling.rotations.RotateCelestial2Native):
            return {"phi": model.lon.value,
                    "theta": model.lat.value,
                    "psi": model.lon_pole.value,
                    "direction": "celestial2native"
                    }
        else:
            return {"phi": model.phi.value,
                    "theta": model.theta.value,
                    "psi": model.psi.value,
                    "direction": model.axes_order
                    }

    @classmethod
    def assert_equal(cls, a, b):
        # TODO: If models become comparable themselves, remove this.
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__
        if a.__class__.__name__ == "EulerAngleRotation":
            assert_array_equal(a.phi, b.phi)
            assert_array_equal(a.psi, b.psi)
            assert_array_equal(a.theta, b.theta)
        else:
            assert_array_equal(a.lon, b.lon)
            assert_array_equal(a.lat, b.lat)
            assert_array_equal(a.lon_pole, b.lon_pole)


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
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__


class ZenithalPerspectiveType(ZenithalType):
    name = "transform/zenithal_perspective"
    types = ['astropy.modeling.projections.Pix2Sky_AZP',
             'astropy.modeling.projections.Sky2Pix_AZP']

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
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__
        assert a.mu.value == b.mu.value
        assert a.gamma.value == b.gamma.value


class GnomonicType(ZenithalType):
    name = "transform/gnomonic"
    types = ['astropy.modeling.projections.Pix2Sky_TAN',
             'astropy.modeling.projections.Sky2Pix_TAN']


class StereographicType(ZenithalType):
    name = "transform/stereographic"
    types = ['astropy.modeling.projections.Pix2Sky_STG',
             'astropy.modeling.projections.Sky2Pix_STG']


class SlantOrthographicType(ZenithalType):
    name = "transform/slant_orthographic"
    types = ['astropy.modeling.projections.Pix2Sky_SIN',
             'astropy.modeling.projections.Sky2Pix_SIN']


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
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__


class CylindricalPerspectiveType(CylindricalType):
    name = "transform/cylindrical_perspective"
    types = ['astropy.modeling.projections.Pix2Sky_CYP',
             'astropy.modeling.projections.Sky2Pix_CYP']

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
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__
        assert a.mu.value == b.mu.value
        assert a.lam.value == b.lam.value


class CylindricalEqualAreaType(CylindricalType):
    name = "transform/cylindrical_equal_area"
    types = ['astropy.modeling.projections.Pix2Sky_CEA',
             'astropy.modeling.projections.Sky2Pix_CEA']

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
        TransformType.assert_equal(a, b)
        assert a.__class__ == b.__class__
        assert a.lam.value == b.lam.value


class PlateCarreeType(CylindricalType):
    name = "transforms/plate_carree"
    types = ['astropy.modeling.projections.Pix2Sky_CAR',
             'astropy.modeling.projections.Sky2Pix_CAR']


class MercatorType(CylindricalType):
    name = "transforms/mercator"
    types = ['astropy.modeling.projections.Pix2Sky_MER',
             'astropy.modeling.projections.Sky2Pix_MER']
