# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
    test_models = []
else:
    HAS_ASTROPY = True
    from astropy.modeling import models as astmodels

    test_models = [astmodels.Identity(2), astmodels.Polynomial1D(2, c0=1, c1=2, c2=3),
                   astmodels.Polynomial2D(1, c0_0=1, c0_1=2, c1_0=3), astmodels.Shift(2.),
                   astmodels.Scale(3.4), astmodels.RotateNative2Celestial(5.63, -72.5, 180),
                   astmodels.RotateCelestial2Native(5.63, -72.5, 180),
                   astmodels.EulerAngleRotation(23, 14, 2.3, axes_order='xzx')]

import pytest
from ....tests import helpers


@pytest.mark.skipif('not HAS_ASTROPY')
def test_transforms_compound(tmpdir):
    tree = {
        'compound':
            astmodels.Shift(1) & astmodels.Shift(2) |
            astmodels.Sky2Pix_TAN() |
            astmodels.Rotation2D() |
            astmodels.AffineTransformation2D([[2, 0], [0, 2]], [42, 32]) +
            astmodels.Rotation2D(32)
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_inverse_transforms(tmpdir):
    rotation = astmodels.Rotation2D(32)
    rotation.inverse = astmodels.Rotation2D(45)

    real_rotation = astmodels.Rotation2D(32)

    tree = {
        'rotation': rotation,
        'real_rotation': real_rotation
        }

    def check(ff):
        assert ff.tree['rotation'].inverse.angle == 45

    helpers.assert_roundtrip_tree(tree, tmpdir, check)


@pytest.mark.skipif('not HAS_ASTROPY')
@pytest.mark.parametrize(('model'), test_models)
def test_single_model(tmpdir, model):
    tree = {'single_model': model}
    helpers.assert_roundtrip_tree(tree, tmpdir)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_name(tmpdir):
    def check(ff):
        assert ff.tree['rot'].name == 'foo'

    tree = {'rot': astmodels.Rotation2D(23, name='foo')}
    helpers.assert_roundtrip_tree(tree, tmpdir, check)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_domain(tmpdir):
    def check(ff):
        assert ff.tree['rot'].meta['domain'] == {
            'lower': 0, 'upper': 1, 'includes_lower': True,
            'includes_upper': False}

    model = astmodels.Rotation2D(23)
    model.meta['domain'] = {'lower': 0, 'upper': 1, 'includes_lower': True}
    tree = {'rot': model}
    helpers.assert_roundtrip_tree(tree, tmpdir, check)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_zenithal_with_arguments(tmpdir):
    tree = {
        'azp': astmodels.Sky2Pix_AZP(0.5, 0.3)
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_naming_of_compound_model(tmpdir):
    """Issue #87"""
    def asdf_check(ff):
        assert ff.tree['model'].name == 'compound_model'

    offx = astmodels.Shift(1)
    scl = astmodels.Scale(2)
    model = (offx | scl).rename('compound_model')
    tree = {
        'model': model
    }
    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check)
