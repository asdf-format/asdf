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
from .. import open as asdf_open
from .helpers import assert_tree_match


def create_asdf_in_fits():
    """Test fixture to create AsdfInFits object to use for testing"""
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
                'data': hdulist[2].data,
                'wcs': 'WCS info'
            }
        }
    }

    return fits_embed.AsdfInFits(hdulist, tree)

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
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(os.path.join(str(tmpdir), 'test.fits'))

    ff2 = asdf.AsdfFile(asdf_in_fits.tree)
    ff2.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with fits.open(os.path.join(str(tmpdir), 'test.fits')) as hdulist:
        assert len(hdulist) == 4
        assert [x.name for x in hdulist] == ['PRIMARY', '', '', 'ASDF']
        assert hdulist['ASDF'].data.tostring().strip().endswith(b"...")

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(asdf_in_fits.tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to('test.asdf')

    with asdf.AsdfFile.open('test.asdf') as ff:
        assert_tree_match(asdf_in_fits.tree, ff.tree)


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

    tmpfile = os.path.join(str(tmpdir), 'test.fits')
    with fits_embed.AsdfInFits(hdulist, tree) as ff:
        ff.write_to(tmpfile)

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with asdf.AsdfFile.open(os.path.join(str(tmpdir), 'plain.asdf')) as ff:
        assert_array_equal(ff.tree['model']['sci']['data'],
                           np.arange(512, dtype=np.float))

    # This tests the changes that allow FITS files with ASDF extensions to be
    # opened directly by the top-level AsdfFile.open API
    with asdf_open(tmpfile) as ff:
        assert_array_equal(ff.tree['model']['sci']['data'],
                           np.arange(512, dtype=np.float))

def compare_asdfs(asdf0, asdf1):
    # Make sure the trees match
    assert_tree_match(asdf0.tree, asdf1.tree)
    # Compare the data blocks
    for key in asdf0.tree['model'].keys():
        assert_array_equal(
            asdf0.tree['model'][key]['data'],
            asdf1.tree['model'][key]['data'])

@pytest.mark.skipif('not HAS_ASTROPY')
def test_asdf_in_fits_open(tmpdir):
    """Test the open method of AsdfInFits"""
    tmpfile = os.path.join(str(tmpdir), 'test.fits')
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(tmpfile)

    # Test opening the file directly from the URI
    with fits_embed.AsdfInFits.open(tmpfile) as ff:
        compare_asdfs(asdf_in_fits, ff)

    # Test open/close without context handler
    ff = fits_embed.AsdfInFits.open(tmpfile)
    compare_asdfs(asdf_in_fits, ff)
    ff.close()

    # Test reading in the file from an already-opened file handle
    with open(tmpfile, 'rb') as handle:
        with fits_embed.AsdfInFits.open(handle) as ff:
            compare_asdfs(asdf_in_fits, ff)

    # Test opening the file as a FITS file first and passing the HDUList
    with fits.open(tmpfile) as hdulist:
        with fits_embed.AsdfInFits.open(hdulist) as ff:
            compare_asdfs(asdf_in_fits, ff)

@pytest.mark.skipif('not HAS_ASTROPY')
def test_asdf_open(tmpdir):
    """Test the top-level open method of the asdf module"""
    tmpfile = os.path.join(str(tmpdir), 'test.fits')
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(tmpfile)

    # Test opening the file directly from the URI
    with asdf_open(tmpfile) as ff:
        compare_asdfs(asdf_in_fits, ff)

    # Test open/close without context handler
    ff = asdf_open(tmpfile)
    compare_asdfs(asdf_in_fits, ff)
    ff.close()

    # Test reading in the file from an already-opened file handle
    with open(tmpfile, 'rb') as handle:
        with asdf_open(handle) as ff:
            compare_asdfs(asdf_in_fits, ff)

    # Test opening the file as a FITS file first and passing the HDUList
    with fits.open(tmpfile) as hdulist:
        with asdf_open(hdulist) as ff:
            compare_asdfs(asdf_in_fits, ff)

@pytest.mark.skipif('not HAS_ASTROPY')
def test_bad_input(tmpdir):
    """Make sure these functions behave properly with bad input"""
    text_file = os.path.join(str(tmpdir), 'test.txt')

    with open(text_file, 'w') as fh:
        fh.write('I <3 ASDF!!!!!')

    with pytest.raises(ValueError):
        asdf_open(text_file)
