# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.modeling import models as astmodels
from astropy.tests.helper import pytest

from ....tests import helpers


test_models = [astmodels.Identity(2), astmodels.Polynomial1D(2, c0=1, c1=2, c2=3),
               astmodels.Polynomial2D(1, c0_0=1, c0_1=2, c1_0=3), astmodels.Shift(2.),
               astmodels.Scale(3.4)]


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


@pytest.mark.parametrize(('model'), test_models)
def test_single_model(tmpdir, model):
    tree = {'single_model': model}
    helpers.assert_roundtrip_tree(tree, tmpdir)
