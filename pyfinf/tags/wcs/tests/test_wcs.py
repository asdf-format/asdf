# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from astropy import modeling
from astropy.modeling import projections
from astropy.modeling import functional_models

from ....tests import helpers

from ..wcs import WcsType


def test_composite_wcs(tmpdir):
    tree = {
        'wcs': WcsType({
            'pixel_to_world':
                modeling.SerialCompositeModel(
                    [
                     functional_models.Shift([1024, 1024]),
                     projections.Pix2Sky_TAN(),
                     projections.AffineTransformation2D([[2.0, 0.0], [0.0, 2.0]])
                 ])
            })
        }

    def check_finf(finf):
        print(finf.blocks._blocks)

    def check_raw_yaml(content):
        print(content)
        assert False
        assert b'OrderedDict' not in content

    helpers.assert_roundtrip_tree(tree, tmpdir, check_finf, check_raw_yaml)
