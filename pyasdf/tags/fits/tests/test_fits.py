# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename

from ....tests import helpers


def test_complex_structure(tmpdir):
    with fits.open(get_pkg_data_filename('data/complex.fits'), memmap=False) as hdulist:
        tree = {
            'fits': hdulist
            }

        helpers.assert_roundtrip_tree(tree, tmpdir)
