# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os

import numpy as np

from astropy.io import fits

from .. import asdf
from .. import fits_embed

from .helpers import assert_tree_match


def test_embed_asdf_in_fits_file(tmpdir):
    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='SCI'))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='DQ'))

    tree = {
        'model': {
            'sci': {
                'data': hdulist['SCI'].data,
                'wcs': 'WCS info'
            },
            'dq': {
                'data': hdulist['DQ'].data,
                'wcs': 'WCS info'
            }
        }
    }

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to(os.path.join(str(tmpdir), 'test.fits'))

    ff2 = asdf.AsdfFile(tree)
    ff2.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with fits.open(os.path.join(str(tmpdir), 'test.fits')) as hdulist2:
        assert len(hdulist2) == 3
        assert [x.name for x in hdulist2] == ['SCI', 'DQ', 'ASDF']
        assert hdulist2['ASDF'].data.tostring().strip().endswith("...")

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(ff2.tree)
            ff.write_to('test.asdf')

            with asdf.AsdfFile.open('test.asdf') as ff:
                assert_tree_match(tree, ff.tree)


def test_embed_asdf_in_fits_file_anonymous_extensions(tmpdir):
    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))

    tree = {
        'model': {
            'sci': {
                'data': hdulist[0].data,
                'wcs': 'WCS info'
            },
            'dq': {
                'data': hdulist[1].data,
                'wcs': 'WCS info'
            },
            'err': {
                'data': hdulist[1].data,
                'wcs': 'WCS info'
            }
        }
    }

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to(os.path.join(str(tmpdir), 'test.fits'))

    ff2 = asdf.AsdfFile(tree)
    ff2.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with fits.open(os.path.join(str(tmpdir), 'test.fits')) as hdulist2:
        assert len(hdulist2) == 4
        assert [x.name for x in hdulist2] == ['PRIMARY', '', '', 'ASDF']
        assert hdulist2['ASDF'].data.tostring().strip().endswith("...")

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(ff2.tree)
            ff.write_to('test.asdf')

            with asdf.AsdfFile.open('test.asdf') as ff:
                assert_tree_match(tree, ff.tree)
