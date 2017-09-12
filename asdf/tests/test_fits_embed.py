# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import copy
import os
import sys
import pytest

import numpy as np
from numpy.testing import assert_array_equal

astropy = pytest.importorskip('astropy')
from astropy.io import fits
from astropy.tests.helper import catch_warnings

from .. import asdf
from .. import fits_embed
from .. import open as asdf_open
from .helpers import assert_tree_match, yaml_to_asdf, display_warnings


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


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

def test_bad_input(tmpdir):
    """Make sure these functions behave properly with bad input"""
    text_file = os.path.join(str(tmpdir), 'test.txt')

    with open(text_file, 'w') as fh:
        fh.write('I <3 ASDF!!!!!')

    with pytest.raises(ValueError):
        asdf_open(text_file)

@pytest.mark.skipif(sys.platform.startswith('win'),
    reason='Avoid path manipulation on Windows')
def test_version_mismatch_file():
    testfile = os.path.join(TEST_DATA_PATH, 'version_mismatch.fits')

    with catch_warnings() as w:
        with asdf.AsdfFile.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    # This is the warning that we expect from opening the FITS file
    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
        "'file://{}', but latest supported version is 1.0.0".format(testfile))

    # Make sure warning does not occur when warning is ignored (default)
    with catch_warnings() as w:
        with asdf.AsdfFile.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 0, display_warnings(w)

    with catch_warnings() as w:
        with fits_embed.AsdfInFits.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
        "'file://{}', but latest supported version is 1.0.0".format(testfile))

    # Make sure warning does not occur when warning is ignored (default)
    with catch_warnings() as w:
        with fits_embed.AsdfInFits.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 0, display_warnings(w)
