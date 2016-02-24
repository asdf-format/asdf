# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import copy
import os

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True
    from astropy.io import fits
    from .. import fits_embed

import numpy as np
from numpy.testing import assert_array_equal

import pytest

from .. import asdf

from .helpers import assert_tree_match


@pytest.mark.skipif('not HAS_ASTROPY')
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
        assert_array_equal(hdulist2[0].data, np.arange(512, dtype=np.float))
        assert hdulist2['ASDF'].data.tostring().strip().endswith(b"...")

        with fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to('test.asdf')

    with asdf.AsdfFile.open('test.asdf') as ff:
        assert_tree_match(tree, ff.tree)


@pytest.mark.skipif('not HAS_ASTROPY')
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
        assert hdulist2['ASDF'].data.tostring().strip().endswith(b"...")

        with fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to('test.asdf')

    with asdf.AsdfFile.open('test.asdf') as ff:
        assert_tree_match(tree, ff.tree)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_create_in_tree_first(tmpdir):
    tree = {
        'model': {
            'sci': {
                'data': np.arange(512, dtype=np.float),
                'wcs': 'WCS info'
            },
            'dq': {
                'data': np.arange(512, dtype=np.float),
                'wcs': 'WCS info'
            },
            'err': {
                'data': np.arange(512, dtype=np.float),
                'wcs': 'WCS info'
            }
        }
    }

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(tree['model']['sci']['data']))
    hdulist.append(fits.ImageHDU(tree['model']['dq']['data']))
    hdulist.append(fits.ImageHDU(tree['model']['err']['data']))

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to(os.path.join(str(tmpdir), 'test.fits'))

    ff2 = asdf.AsdfFile(tree)
    ff2.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with asdf.AsdfFile.open(os.path.join(str(tmpdir), 'plain.asdf')) as ff3:
        assert_array_equal(ff3.tree['model']['sci']['data'],
                           np.arange(512, dtype=np.float))

    with fits.open(os.path.join(str(tmpdir), 'test.fits')) as hdulist:
        with fits_embed.AsdfInFits.open(hdulist) as ff4:
            assert_array_equal(ff4.tree['model']['sci']['data'],
                               np.arange(512, dtype=np.float))
