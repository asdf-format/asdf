# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from astropy import modeling
from astropy.modeling import mappings

from ....tests import helpers


def test_transforms(tmpdir):
    tree = {
        'identity': mappings.Identity(2)
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_transforms_compound(tmpdir):
    tree = {
        'compound':
            modeling.projections.Sky2Pix_TAN() |
            modeling.rotations.Rotation2D() |
            modeling.projections.AffineTransformation2D([[2, 0], [0, 2]], [42, 32]) +
            modeling.rotations.Rotation2D(32)
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_inverse_transforms(tmpdir):
    rotation = modeling.rotations.Rotation2D(32)
    rotation.inverse = modeling.rotations.Rotation2D(45)

    real_rotation = modeling.rotations.Rotation2D(32)

    tree = {
        'rotation': rotation,
        'real_rotation': real_rotation
        }

    def check(ff):
        assert ff.tree['rotation'].inverse.angle == 45

    helpers.assert_roundtrip_tree(tree, tmpdir, check)
