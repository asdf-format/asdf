# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import copy
import os
import sys
import pytest

import numpy as np
from numpy.testing import assert_array_equal

astropy = pytest.importorskip('astropy')
from astropy.io import fits
from astropy.table import Table

import asdf
from asdf import fits_embed
from asdf import open as asdf_open

from .helpers import assert_tree_match, display_warnings


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

# Testing backwards compatibility ensures that we can continue to read and
# write files that use the old convention of ImageHDU to store the ASDF file.
@pytest.mark.parametrize('backwards_compat', [False, True])
def test_embed_asdf_in_fits_file(tmpdir, backwards_compat):
    fits_testfile = str(tmpdir.join('test.fits'))
    asdf_testfile = str(tmpdir.join('test.asdf'))

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
    ff.write_to(fits_testfile, use_image_hdu=backwards_compat)

    with fits.open(fits_testfile) as hdulist2:
        assert len(hdulist2) == 3
        assert [x.name for x in hdulist2] == ['SCI', 'DQ', 'ASDF']
        assert_array_equal(hdulist2[0].data, np.arange(512, dtype=np.float))
        asdf_hdu = hdulist2['ASDF']
        assert asdf_hdu.data.tostring().startswith(b'#ASDF')
        # When in backwards compatibility mode, the ASDF file will be contained
        # in an ImageHDU
        if backwards_compat:
            assert isinstance(asdf_hdu, fits.ImageHDU)
            assert asdf_hdu.data.tostring().strip().endswith(b'...')
        else:
            assert isinstance(asdf_hdu, fits_embed._AsdfHDU)

        with fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(asdf_testfile)

    with asdf.AsdfFile.open(asdf_testfile) as ff:
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
        asdf_hdu = hdulist['ASDF']
        assert isinstance(asdf_hdu, fits_embed._AsdfHDU)
        assert asdf_hdu.data.tostring().startswith(b'#ASDF')

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(asdf_in_fits.tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(os.path.join(str(tmpdir), 'test.asdf'))

    with asdf.AsdfFile.open(os.path.join(str(tmpdir), 'test.asdf')) as ff:
        assert_tree_match(asdf_in_fits.tree, ff.tree)


@pytest.mark.xfail(
    reason="In-place update for ASDF-in-FITS does not currently work")
def test_update_in_place(tmpdir):
    tempfile = str(tmpdir.join('test.fits'))

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(tempfile)

    # Open the file and add data so it needs to be updated
    with fits_embed.AsdfInFits.open(tempfile) as ff:
        ff.tree['new_stuff'] = "A String"
        ff.update()

    # Open the updated file and make sure everything looks okay
    with fits_embed.AsdfInFits.open(tempfile) as ff:
        assert ff.tree['new_stuff'] == "A String"
        assert_tree_match(ff.tree['model'], asdf_in_fits.tree['model'])


def test_update_and_write_new(tmpdir):
    tempfile = str(tmpdir.join('test.fits'))
    newfile = str(tmpdir.join('new.fits'))

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(tempfile)

    # Open the file and add data so it needs to be updated
    with fits_embed.AsdfInFits.open(tempfile) as ff:
        ff.tree['new_stuff'] = "A String"
        ff.write_to(newfile)

    # Open the updated file and make sure everything looks okay
    with fits_embed.AsdfInFits.open(newfile) as ff:
        assert ff.tree['new_stuff'] == "A String"
        assert_tree_match(ff.tree['model'], asdf_in_fits.tree['model'])


@pytest.mark.xfail(
    reason="ASDF HDU implementation does not currently reseek after writing")
def test_access_hdu_data_after_write(tmpdir):
    # There is actually probably not a great reason to support this kind of
    # functionality, but I am adding a test here to record the failure for
    # posterity.
    tempfile = str(tmpdir.join('test.fits'))

    asdf_in_fits = create_asdf_in_fits()
    asdf_in_fits.write_to(tempfile)
    asdf_hdu = asdf_in_fits._hdulist['ASDF']

    assert asdf_hdu.data.tostring().startswith('#ASDF')


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

def test_open_gzipped():
    testfile = os.path.join(TEST_DATA_PATH, 'asdf.fits.gz')

    # Opening as an HDU should work
    with fits.open(testfile) as ff:
        with asdf.AsdfFile.open(ff) as af:
            assert af.tree['stuff'].shape == (20, 20)

    with fits_embed.AsdfInFits.open(testfile) as af:
        assert af.tree['stuff'].shape == (20, 20)

    with asdf.AsdfFile.open(testfile) as af:
        assert af.tree['stuff'].shape == (20, 20)

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

    with pytest.warns(None) as w:
        with asdf.AsdfFile.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    # This is the warning that we expect from opening the FITS file
    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
        "'{}', but latest supported version is 1.0.0".format(testfile))

    # Make sure warning does not occur when warning is ignored (default)
    with pytest.warns(None) as w:
        with asdf.AsdfFile.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 0, display_warnings(w)

    with pytest.warns(None) as w:
        with fits_embed.AsdfInFits.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
        "'{}', but latest supported version is 1.0.0".format(testfile))

    # Make sure warning does not occur when warning is ignored (default)
    with pytest.warns(None) as w:
        with fits_embed.AsdfInFits.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 0, display_warnings(w)

def test_serialize_table(tmpdir):
    tmpfile = str(tmpdir.join('table.fits'))

    data = np.random.random((10, 10))
    table = Table(data)

    hdu = fits.BinTableHDU(table)
    hdulist = fits.HDUList()
    hdulist.append(hdu)

    tree = {'my_table': hdulist[1].data}
    with fits_embed.AsdfInFits(hdulist, tree) as ff:
        ff.write_to(tmpfile)

    with asdf.AsdfFile.open(tmpfile) as ff:
        data = ff.tree['my_table']
        assert data._source.startswith('fits:')

def test_extension_check():
    testfile = os.path.join(TEST_DATA_PATH, 'extension_check.fits')

    with pytest.warns(None) as warnings:
        with asdf.AsdfFile.open(testfile) as ff:
            pass

    assert len(warnings) == 1, display_warnings(warnings)
    assert ("was created with extension 'foo.bar.FooBar', which is not "
        "currently installed (from package foo-1.2.3)") in str(warnings[0].message)

    # Make sure that suppressing the warning works as well
    with pytest.warns(None) as warnings:
        with asdf.AsdfFile.open(testfile, ignore_missing_extensions=True) as ff:
            pass

    assert len(warnings) == 0, display_warnings(warnings)

    with pytest.raises(RuntimeError):
        with asdf.AsdfFile.open(testfile, strict_extension_check=True) as ff:
            pass
