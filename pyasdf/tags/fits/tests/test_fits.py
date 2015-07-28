# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True

import pytest

import os

from ....tests import helpers


@pytest.mark.skipif('not HAS_ASTROPY')
def test_complex_structure(tmpdir):
    from astropy.io import fits

    with fits.open(os.path.join(
            os.path.dirname(__file__), 'data', 'complex.fits'), memmap=False) as hdulist:
        tree = {
            'fits': hdulist
            }

        helpers.assert_roundtrip_tree(tree, tmpdir)
