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

from jsonschema.exceptions import ValidationError

import asdf
from asdf import fits_embed
from asdf import open as asdf_open

from .helpers import assert_tree_match, display_warnings, get_test_data_path, yaml_to_asdf


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
    # Test a name with underscores to make sure it works
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='WITH_UNDERSCORE'))

    tree = {
        'model': {
            'sci': {
                'data': hdulist['SCI'].data,
                'wcs': 'WCS info'
            },
            'dq': {
                'data': hdulist['DQ'].data,
                'wcs': 'WCS info'
            },
            'with_underscore': {
                'data': hdulist['WITH_UNDERSCORE'].data,
                'wcs': 'WCS info'
            }
        }
    }

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to(fits_testfile, use_image_hdu=backwards_compat)

    with fits.open(fits_testfile) as hdulist2:
        assert len(hdulist2) == 4
        assert [x.name for x in hdulist2] == ['SCI', 'DQ', 'WITH_UNDERSCORE', 'ASDF']
        assert_array_equal(hdulist2[0].data, np.arange(512, dtype=np.float))
        asdf_hdu = hdulist2['ASDF']
        assert asdf_hdu.data.tostring().startswith(b'#ASDF')
        # When in backwards compatibility mode, the ASDF file will be contained
        # in an ImageHDU
        if backwards_compat:
            assert isinstance(asdf_hdu, fits.ImageHDU)
            assert asdf_hdu.data.tostring().strip().endswith(b'...')
        else:
            assert isinstance(asdf_hdu, fits.BinTableHDU)

        with fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(asdf_testfile)

    with asdf.open(asdf_testfile) as ff:
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
        assert isinstance(asdf_hdu, fits.BinTableHDU)
        assert asdf_hdu.data.tostring().startswith(b'#ASDF')

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(asdf_in_fits.tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(os.path.join(str(tmpdir), 'test.asdf'))

    with asdf.open(os.path.join(str(tmpdir), 'test.asdf')) as ff:
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

    with asdf.open(os.path.join(str(tmpdir), 'plain.asdf')) as ff:
        assert_array_equal(ff.tree['model']['sci']['data'],
                           np.arange(512, dtype=np.float))

    # This tests the changes that allow FITS files with ASDF extensions to be
    # opened directly by the top-level asdf.open API
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

def test_validate_on_read(tmpdir):
    tmpfile = str(tmpdir.join('invalid.fits'))

    content = """
invalid_software: !core/software-1.0.0
  name: Minesweeper
  version: 3
"""
    buff = yaml_to_asdf(content)
    hdul = fits.HDUList()
    data = np.array(buff.getbuffer(), dtype=np.uint8)[None, :]
    fmt = '{}B'.format(len(data[0]))
    column = fits.Column(array=data, format=fmt, name='ASDF_METADATA')
    hdu = fits.BinTableHDU.from_columns([column], name='ASDF')
    hdul.append(hdu)
    hdul.writeto(tmpfile)

    for open_method in [asdf.open, fits_embed.AsdfInFits.open]:
        with pytest.raises(ValidationError):
            with open_method(tmpfile, validate_on_read=True):
                pass

        with open_method(tmpfile, validate_on_read=False) as af:
            assert af["invalid_software"]["name"] == "Minesweeper"
            assert af["invalid_software"]["version"] == 3


def test_open_gzipped():
    testfile = get_test_data_path('asdf.fits.gz')

    # Opening as an HDU should work
    with fits.open(testfile) as ff:
        with asdf.open(ff) as af:
            assert af.tree['stuff'].shape == (20, 20)

    with fits_embed.AsdfInFits.open(testfile) as af:
        assert af.tree['stuff'].shape == (20, 20)

    with asdf.open(testfile) as af:
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

    testfile = str(get_test_data_path('version_mismatch.fits'))

    with pytest.warns(None) as w:
        with asdf.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    # This is the warning that we expect from opening the FITS file
    expected_messages = {
        (
            "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
            "'{}', but latest supported version is 1.0.0".format(testfile)
        ),
        (
            "'tag:stsci.edu:asdf/core/asdf' with version 1.0.0 found in file "
            "'{}', but latest supported version is 1.1.0".format(testfile)
        ),
    }
    assert expected_messages == {warn.message.args[0] for warn in w}, display_warnings(w)

    # Make sure warning does not occur when warning is ignored (default)
    with pytest.warns(None) as w:
        with asdf.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    assert len(w) == 0, display_warnings(w)

    with pytest.warns(None) as w:
        with fits_embed.AsdfInFits.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)
    expected_messages = {
        (
            "'tag:stsci.edu:asdf/core/complex' with version 7.0.0 found in file "
            "'{}', but latest supported version is 1.0.0".format(testfile)
        ),
        (
            "'tag:stsci.edu:asdf/core/asdf' with version 1.0.0 found in file "
            "'{}', but latest supported version is 1.1.0".format(testfile)
        ),
    }
    assert expected_messages == {warn.message.args[0] for warn in w}, display_warnings(w)

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

    with asdf.open(tmpfile) as ff:
        data = ff.tree['my_table']
        assert data._source.startswith('fits:')

def test_extension_check():
    testfile = get_test_data_path('extension_check.fits')

    with pytest.warns(None) as warnings:
        with asdf.open(testfile):
            pass

    assert len(warnings) == 1, display_warnings(warnings)
    assert ("was created with extension 'foo.bar.FooBar', which is not "
        "currently installed (from package foo-1.2.3)") in str(warnings[0].message)

    # Make sure that suppressing the warning works as well
    with pytest.warns(None) as warnings:
        with asdf.open(testfile, ignore_missing_extensions=True):
            pass

    assert len(warnings) == 0, display_warnings(warnings)

    with pytest.raises(RuntimeError):
        with asdf.open(testfile, strict_extension_check=True):
            pass

def test_verify_with_astropy(tmpdir):
    tmpfile = str(tmpdir.join('asdf.fits'))

    with create_asdf_in_fits() as aif:
        aif.write_to(tmpfile)

    with fits.open(tmpfile) as hdu:
        hdu.verify('exception')

def test_dangling_file_handle(tmpdir):
    """
    This tests the bug fix introduced in #533. Without the bug fix, this test
    will fail when running the test suite with pytest-openfiles.
    """
    import gc

    fits_filename = str(tmpdir.join('dangling.fits'))

    # Create FITS file to use for test
    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float)))
    hdulist.writeto(fits_filename)
    hdulist.close()

    hdul = fits.open(fits_filename)
    gc.collect()

    ctx = asdf.AsdfFile()
    gc.collect()

    ctx.blocks.find_or_create_block_for_array(hdul[0].data, ctx)
    gc.collect()

    hdul.close()
    gc.collect()

    ctx.close()
    gc.collect()

    del ctx
