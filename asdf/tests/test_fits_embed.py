# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import copy
import os
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
from asdf.exceptions import AsdfWarning, AsdfConversionWarning

from .helpers import (
    assert_tree_match,
    get_test_data_path,
    yaml_to_asdf,
    assert_no_warnings,
)


TEST_DTYPES = ['<f8', '<f8', '<u4', '>u4', '<i4', '>i4']


def create_asdf_in_fits(dtype):
    """Test fixture to create AsdfInFits object to use for testing"""
    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))

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
@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_embed_asdf_in_fits_file(tmpdir, backwards_compat, dtype):
    fits_testfile = str(tmpdir.join('test.fits'))
    asdf_testfile = str(tmpdir.join('test.asdf'))

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name='SCI'))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name='DQ'))
    # Test a name with underscores to make sure it works
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name='WITH_UNDERSCORE'))

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
        assert_array_equal(hdulist2[0].data, np.arange(512, dtype=dtype))
        asdf_hdu = hdulist2['ASDF']
        assert asdf_hdu.data.tobytes().startswith(b'#ASDF')
        # When in backwards compatibility mode, the ASDF file will be contained
        # in an ImageHDU
        if backwards_compat:
            assert isinstance(asdf_hdu, fits.ImageHDU)
            assert asdf_hdu.data.tobytes().strip().endswith(b'...')
        else:
            assert isinstance(asdf_hdu, fits.BinTableHDU)

        with fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(asdf_testfile)

    with asdf.open(asdf_testfile) as ff:
        assert_tree_match(tree, ff.tree)


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_embed_asdf_in_fits_file_anonymous_extensions(tmpdir, dtype):
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(os.path.join(str(tmpdir), 'test.fits'))

    ff2 = asdf.AsdfFile(asdf_in_fits.tree)
    ff2.write_to(os.path.join(str(tmpdir), 'plain.asdf'))

    with fits.open(os.path.join(str(tmpdir), 'test.fits')) as hdulist:
        assert len(hdulist) == 4
        assert [x.name for x in hdulist] == ['PRIMARY', '', '', 'ASDF']
        asdf_hdu = hdulist['ASDF']
        assert isinstance(asdf_hdu, fits.BinTableHDU)
        assert asdf_hdu.data.tobytes().startswith(b'#ASDF')

        with fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(asdf_in_fits.tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(os.path.join(str(tmpdir), 'test.asdf'))

    with asdf.open(os.path.join(str(tmpdir), 'test.asdf')) as ff:
        assert_tree_match(asdf_in_fits.tree, ff.tree)


@pytest.mark.xfail(
    reason="In-place update for ASDF-in-FITS does not currently work")
@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_update_in_place(tmpdir, dtype):
    tempfile = str(tmpdir.join('test.fits'))

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tempfile)

    # Open the file and add data so it needs to be updated
    with fits_embed.AsdfInFits.open(tempfile) as ff:
        ff.tree['new_stuff'] = "A String"
        ff.update()

    # Open the updated file and make sure everything looks okay
    with fits_embed.AsdfInFits.open(tempfile) as ff:
        assert ff.tree['new_stuff'] == "A String"
        assert_tree_match(ff.tree['model'], asdf_in_fits.tree['model'])


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_update_and_write_new(tmpdir, dtype):
    tempfile = str(tmpdir.join('test.fits'))
    newfile = str(tmpdir.join('new.fits'))

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits(dtype)
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
@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_access_hdu_data_after_write(tmpdir, dtype):
    # There is actually probably not a great reason to support this kind of
    # functionality, but I am adding a test here to record the failure for
    # posterity.
    tempfile = str(tmpdir.join('test.fits'))

    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tempfile)
    asdf_hdu = asdf_in_fits._hdulist['ASDF']

    assert asdf_hdu.data.tobytes().startswith('#ASDF')


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_create_in_tree_first(tmpdir, dtype):
    tree = {
        'model': {
            'sci': {
                'data': np.arange(512, dtype=dtype),
                'wcs': 'WCS info'
            },
            'dq': {
                'data': np.arange(512, dtype=dtype),
                'wcs': 'WCS info'
            },
            'err': {
                'data': np.arange(512, dtype=dtype),
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
                           np.arange(512, dtype=dtype))

    # This tests the changes that allow FITS files with ASDF extensions to be
    # opened directly by the top-level asdf.open API
    with asdf_open(tmpfile) as ff:
        assert_array_equal(ff.tree['model']['sci']['data'],
                           np.arange(512, dtype=dtype))

def compare_asdfs(asdf0, asdf1):
    # Make sure the trees match
    assert_tree_match(asdf0.tree, asdf1.tree)
    # Compare the data blocks
    for key in asdf0.tree['model'].keys():
        assert_array_equal(
            asdf0.tree['model'][key]['data'],
            asdf1.tree['model'][key]['data'])


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_asdf_in_fits_open(tmpdir, dtype):
    """Test the open method of AsdfInFits"""
    tmpfile = os.path.join(str(tmpdir), 'test.fits')
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits(dtype)
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


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_asdf_open(tmpdir, dtype):
    """Test the top-level open method of the asdf module"""
    tmpfile = os.path.join(str(tmpdir), 'test.fits')
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits(dtype)
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


@pytest.mark.filterwarnings('ignore::astropy.io.fits.verify.VerifyWarning')
def test_bad_input(tmpdir):
    """Make sure these functions behave properly with bad input"""
    text_file = os.path.join(str(tmpdir), 'test.txt')

    with open(text_file, 'w') as fh:
        fh.write('I <3 ASDF!!!!!')

    with pytest.raises(ValueError):
        asdf_open(text_file)

def test_version_mismatch_file():
    testfile = str(get_test_data_path('version_mismatch.fits'))

    with pytest.warns(AsdfConversionWarning, match="tag:stsci.edu:asdf/core/complex"):
        with asdf.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)

    # Make sure warning does not occur when warning is ignored (default)
    with assert_no_warnings(AsdfConversionWarning):
        with asdf.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)

    with pytest.warns(AsdfConversionWarning, match="tag:stsci.edu:asdf/core/complex"):
        with fits_embed.AsdfInFits.open(testfile,
                ignore_version_mismatch=False) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)

    # Make sure warning does not occur when warning is ignored (default)
    with assert_no_warnings(AsdfConversionWarning):
        with fits_embed.AsdfInFits.open(testfile) as fits_handle:
            assert fits_handle.tree['a'] == complex(0j)


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

    with pytest.warns(AsdfWarning, match="was created with extension 'foo.bar.FooBar'"):
        with asdf.open(testfile):
            pass

    # Make sure that suppressing the warning works as well
    with assert_no_warnings():
        with asdf.open(testfile, ignore_missing_extensions=True):
            pass

    with pytest.raises(RuntimeError):
        with asdf.open(testfile, strict_extension_check=True):
            pass


@pytest.mark.parametrize('dtype', TEST_DTYPES)
def test_verify_with_astropy(tmpdir, dtype):
    tmpfile = str(tmpdir.join('asdf.fits'))

    with create_asdf_in_fits(dtype) as aif:
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
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=float)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=float)))
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


def test_array_view(tmp_path):
    """
    Special handling is required when a view over a larger array
    is assigned to an HDU and referenced from the ASDF tree.
    """
    file_path = str(tmp_path / "test.fits")

    data = np.arange(400, dtype=np.float64).reshape(20, 20)
    data_view = data[:, :20]

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data_view)])
    with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
        af["data"] = hdul[-1].data
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert_array_equal(af["data"], data_view)


def test_array_view_compatible_layout(tmp_path):
    """
    We should be able to serialize additional views that have
    the same memory layout.
    """
    file_path = str(tmp_path / "test.fits")

    data = np.arange(400, dtype=np.float64).reshape(20, 20)
    data_view = data[:, :10]
    other_view = data_view[:, :]

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data_view)])
    with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
        af["data"] = hdul[-1].data
        af["other"] = other_view
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert_array_equal(af["data"], data_view)
        assert_array_equal(af["other"], other_view)


def test_array_view_compatible_dtype(tmp_path):
    """
    Changing the dtype of a view over a FITS array is prohibited.
    """
    file_path = tmp_path / "test.fits"

    data = np.arange(400, dtype=np.float64)
    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data)])
    with pytest.raises(ValueError, match="ASDF has only limited support for serializing views over arrays stored in FITS HDUs"):
        with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
            af["view"] = hdul[-1].data.view(np.int64)
            af.write_to(file_path)


def test_array_view_different_layout(tmp_path):
    """
    A view over the FITS array with a different memory layout
    might end up corrupted when astropy.io.fits changes the
    array to C-contiguous and big-endian on write.
    """
    file_path = str(tmp_path / "test.fits")

    data = np.arange(400, dtype=np.float64).reshape(20, 20)
    data_view = data[:, :10]
    other_view = data_view[:, 10:]

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data_view)])
    with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
        af["data"] = hdul[-1].data
        af["other"] = other_view
        with pytest.raises(ValueError, match="ASDF has only limited support for serializing views over arrays stored in FITS HDUs"):
            af.write_to(file_path)
