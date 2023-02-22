import copy
import sys

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from jsonschema.exceptions import ValidationError
from numpy.testing import assert_array_equal

import asdf
from asdf import get_config
from asdf import open as asdf_open
from asdf.exceptions import AsdfConversionWarning, AsdfDeprecationWarning, AsdfWarning

with pytest.warns(AsdfDeprecationWarning, match="AsdfInFits has been deprecated.*"):
    if "asdf.fits_embed" in sys.modules:
        del sys.modules["asdf.fits_embed"]
    import asdf.fits_embed

from ._helpers import assert_no_warnings, assert_tree_match, get_test_data_path, yaml_to_asdf

TEST_DTYPES = ["<f8", ">f8", "<u4", ">u4", "<i4", ">i4"]


def create_asdf_in_fits(dtype):
    """Test fixture to create AsdfInFits object to use for testing"""
    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype)))

    tree = {
        "model": {
            "sci": {"data": hdulist[0].data, "wcs": "WCS info"},
            "dq": {"data": hdulist[1].data, "wcs": "WCS info"},
            "err": {"data": hdulist[2].data, "wcs": "WCS info"},
        },
    }

    return asdf.fits_embed.AsdfInFits(hdulist, tree)


# Testing backwards compatibility ensures that we can continue to read and
# write files that use the old convention of ImageHDU to store the ASDF file.
@pytest.mark.parametrize("backwards_compat", [False, True])
@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_embed_asdf_in_fits_file(tmp_path, backwards_compat, dtype):
    fits_testfile = str(tmp_path / "test.fits")
    asdf_testfile = str(tmp_path / "test.asdf")

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name="SCI"))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name="DQ"))
    # Test a name with underscores to make sure it works
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=dtype), name="WITH_UNDERSCORE"))

    tree = {
        "model": {
            "sci": {"data": hdulist["SCI"].data, "wcs": "WCS info"},
            "dq": {"data": hdulist["DQ"].data, "wcs": "WCS info"},
            "with_underscore": {"data": hdulist["WITH_UNDERSCORE"].data, "wcs": "WCS info"},
        },
    }

    ff = asdf.fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to(fits_testfile, use_image_hdu=backwards_compat)

    with fits.open(fits_testfile) as hdulist2:
        assert len(hdulist2) == 4
        assert [x.name for x in hdulist2] == ["SCI", "DQ", "WITH_UNDERSCORE", "ASDF"]
        assert_array_equal(hdulist2[0].data, np.arange(512, dtype=dtype))
        asdf_hdu = hdulist2["ASDF"]
        assert asdf_hdu.data.tobytes().startswith(b"#ASDF")
        # When in backwards compatibility mode, the ASDF file will be contained
        # in an ImageHDU
        if backwards_compat:
            assert isinstance(asdf_hdu, fits.ImageHDU)
            assert asdf_hdu.data.tobytes().strip().endswith(b"...")
        else:
            assert isinstance(asdf_hdu, fits.BinTableHDU)

        with asdf.fits_embed.AsdfInFits.open(hdulist2) as ff2:
            assert_tree_match(tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(asdf_testfile)

    with asdf.open(asdf_testfile) as ff:
        assert_tree_match(tree, ff.tree)


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_embed_asdf_in_fits_file_anonymous_extensions(tmp_path, dtype):
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(str(tmp_path / "test.fits"))

    ff2 = asdf.AsdfFile(asdf_in_fits.tree)
    ff2.write_to(str(tmp_path / "plain.asdf"))

    with fits.open(str(tmp_path / "test.fits")) as hdulist:
        assert len(hdulist) == 4
        assert [x.name for x in hdulist] == ["PRIMARY", "", "", "ASDF"]
        asdf_hdu = hdulist["ASDF"]
        assert isinstance(asdf_hdu, fits.BinTableHDU)
        assert asdf_hdu.data.tobytes().startswith(b"#ASDF")

        with asdf.fits_embed.AsdfInFits.open(hdulist) as ff2:
            assert_tree_match(asdf_in_fits.tree, ff2.tree)

            ff = asdf.AsdfFile(copy.deepcopy(ff2.tree))
            ff.write_to(str(tmp_path / "test.asdf"))

    with asdf.open(str(tmp_path / "test.asdf")) as ff:
        assert_tree_match(asdf_in_fits.tree, ff.tree)


@pytest.mark.xfail(reason="In-place update for ASDF-in-FITS does not currently work")
@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_update_in_place(tmp_path, dtype):
    tempfile = str(tmp_path / "test.fits")

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tempfile)

    # Open the file and add data so it needs to be updated
    with asdf.fits_embed.AsdfInFits.open(tempfile) as ff:
        ff.tree["new_stuff"] = "A String"
        ff.update()

    # Open the updated file and make sure everything looks okay
    with asdf.fits_embed.AsdfInFits.open(tempfile) as ff:
        assert ff.tree["new_stuff"] == "A String"
        assert_tree_match(ff.tree["model"], asdf_in_fits.tree["model"])


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_update_and_write_new(tmp_path, dtype):
    tempfile = str(tmp_path / "test.fits")
    newfile = str(tmp_path / "new.fits")

    # Create a file and write it out
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tempfile)

    # Open the file and add data so it needs to be updated
    with asdf.fits_embed.AsdfInFits.open(tempfile) as ff:
        ff.tree["new_stuff"] = "A String"
        ff.write_to(newfile)

    # Open the updated file and make sure everything looks okay
    with asdf.fits_embed.AsdfInFits.open(newfile) as ff:
        assert ff.tree["new_stuff"] == "A String"
        assert_tree_match(ff.tree["model"], asdf_in_fits.tree["model"])


@pytest.mark.xfail(reason="ASDF HDU implementation does not currently reseek after writing")
@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_access_hdu_data_after_write(tmp_path, dtype):
    # There is actually probably not a great reason to support this kind of
    # functionality, but I am adding a test here to record the failure for
    # posterity.
    tempfile = str(tmp_path / "test.fits")

    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tempfile)
    asdf_hdu = asdf_in_fits._hdulist["ASDF"]

    assert asdf_hdu.data.tobytes().startswith("#ASDF")


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_create_in_tree_first(tmp_path, dtype):
    tree = {
        "model": {
            "sci": {"data": np.arange(512, dtype=dtype), "wcs": "WCS info"},
            "dq": {"data": np.arange(512, dtype=dtype), "wcs": "WCS info"},
            "err": {"data": np.arange(512, dtype=dtype), "wcs": "WCS info"},
        },
    }

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(tree["model"]["sci"]["data"]))
    hdulist.append(fits.ImageHDU(tree["model"]["dq"]["data"]))
    hdulist.append(fits.ImageHDU(tree["model"]["err"]["data"]))

    tmpfile = str(tmp_path / "test.fits")
    with asdf.fits_embed.AsdfInFits(hdulist, tree) as ff:
        ff.write_to(tmpfile)

    with asdf.AsdfFile(tree) as ff:
        ff.write_to(str(tmp_path / "plain.asdf"))

    with asdf.open(str(tmp_path / "plain.asdf")) as ff:
        assert_array_equal(ff.tree["model"]["sci"]["data"], np.arange(512, dtype=dtype))

    # This tests the changes that allow FITS files with ASDF extensions to be
    # opened directly by the top-level asdf.open API
    with asdf_open(tmpfile) as ff:
        assert_array_equal(ff.tree["model"]["sci"]["data"], np.arange(512, dtype=dtype))


def compare_asdfs(asdf0, asdf1):
    # Make sure the trees match
    assert_tree_match(asdf0.tree, asdf1.tree)
    # Compare the data blocks
    for key in asdf0.tree["model"]:
        assert_array_equal(asdf0.tree["model"][key]["data"], asdf1.tree["model"][key]["data"])


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_asdf_in_fits_open(tmp_path, dtype):
    """Test the open method of AsdfInFits"""
    tmpfile = str(tmp_path / "test.fits")
    # Write the AsdfInFits object out as a FITS file with ASDF extension
    asdf_in_fits = create_asdf_in_fits(dtype)
    asdf_in_fits.write_to(tmpfile)

    # Test opening the file directly from the URI
    with asdf.fits_embed.AsdfInFits.open(tmpfile) as ff:
        compare_asdfs(asdf_in_fits, ff)

    # Test open/close without context handler
    ff = asdf.fits_embed.AsdfInFits.open(tmpfile)
    compare_asdfs(asdf_in_fits, ff)
    ff.close()

    # Test reading in the file from an already-opened file handle
    with open(tmpfile, "rb") as handle, asdf.fits_embed.AsdfInFits.open(handle) as ff:
        compare_asdfs(asdf_in_fits, ff)

    # Test opening the file as a FITS file first and passing the HDUList
    with fits.open(tmpfile) as hdulist, asdf.fits_embed.AsdfInFits.open(hdulist) as ff:
        compare_asdfs(asdf_in_fits, ff)


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_asdf_open(tmp_path, dtype):
    """Test the top-level open method of the asdf module"""
    tmpfile = str(tmp_path / "test.fits")
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
    with open(tmpfile, "rb") as handle, asdf_open(handle) as ff:
        compare_asdfs(asdf_in_fits, ff)


def test_validate_on_read(tmp_path):
    tmpfile = str(tmp_path / "invalid.fits")

    content = """
invalid_software: !core/software-1.0.0
  name: Minesweeper
  version: 3
"""
    buff = yaml_to_asdf(content)
    hdul = fits.HDUList()
    data = np.array(buff.getbuffer(), dtype=np.uint8)[None, :]
    fmt = f"{len(data[0])}B"
    column = fits.Column(array=data, format=fmt, name="ASDF_METADATA")
    hdu = fits.BinTableHDU.from_columns([column], name="ASDF")
    hdul.append(hdu)
    hdul.writeto(tmpfile)

    for open_method in [asdf.open, asdf.fits_embed.AsdfInFits.open]:
        get_config().validate_on_read = True
        with pytest.raises(ValidationError, match=r".* is not of type .*"), open_method(tmpfile):
            pass

        get_config().validate_on_read = False
        with open_method(tmpfile) as af:
            assert af["invalid_software"]["name"] == "Minesweeper"
            assert af["invalid_software"]["version"] == 3


def test_bad_fits_input(tmp_path):
    path = tmp_path / "test.fits"
    # create an empty fits file
    with open(path, "wb") as f:
        f.write(asdf.constants.FITS_MAGIC)

    with pytest.raises(
        ValueError,
        match=r"Input object does not appear to be an ASDF file or a FITS with ASDF extension",
    ), asdf_open(path):
        pass


def test_open_gzipped():
    testfile = get_test_data_path("asdf.fits.gz")

    with asdf.fits_embed.AsdfInFits.open(testfile) as af:
        assert af.tree["stuff"].shape == (20, 20)


def test_version_mismatch_file():
    testfile = str(get_test_data_path("version_mismatch.fits"))

    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.open(
        testfile,
        ignore_version_mismatch=False,
    ) as fits_handle:
        assert fits_handle.tree["a"] == complex(0j)

    # Make sure warning does not occur when warning is ignored (default)
    with assert_no_warnings(AsdfConversionWarning), asdf.open(testfile) as fits_handle:
        assert fits_handle.tree["a"] == complex(0j)

    with pytest.warns(AsdfConversionWarning, match=r"tag:stsci.edu:asdf/core/complex"), asdf.fits_embed.AsdfInFits.open(
        testfile,
        ignore_version_mismatch=False,
    ) as fits_handle:
        assert fits_handle.tree["a"] == complex(0j)

    # Make sure warning does not occur when warning is ignored (default)
    with assert_no_warnings(AsdfConversionWarning), asdf.fits_embed.AsdfInFits.open(testfile) as fits_handle:
        assert fits_handle.tree["a"] == complex(0j)


def test_serialize_table(tmp_path):
    tmpfile = str(tmp_path / "table.fits")

    data = np.random.random((10, 10))
    table = Table(data)

    hdu = fits.BinTableHDU(table)
    hdulist = fits.HDUList()
    hdulist.append(hdu)

    tree = {"my_table": hdulist[1].data}
    with asdf.fits_embed.AsdfInFits(hdulist, tree) as ff:
        ff.write_to(tmpfile)

    with asdf.open(tmpfile) as ff:
        data = ff.tree["my_table"]
        assert data._source.startswith("fits:")


def test_extension_check():
    testfile = get_test_data_path("extension_check.fits")

    with pytest.warns(AsdfWarning, match=r"was created with extension class 'foo.bar.FooBar'"), asdf.open(testfile):
        pass

    # Make sure that suppressing the warning works as well
    with assert_no_warnings(), asdf.open(testfile, ignore_missing_extensions=True):
        pass

    with pytest.raises(
        RuntimeError,
        match=r"File.* was created with extension class .*, which is not currently installed",
    ), asdf.open(testfile, strict_extension_check=True):
        pass


@pytest.mark.parametrize("dtype", TEST_DTYPES)
def test_verify_with_astropy(tmp_path, dtype):
    tmpfile = str(tmp_path / "asdf.fits")

    with create_asdf_in_fits(dtype) as aif:
        aif.write_to(tmpfile)

    with fits.open(tmpfile) as hdu:
        hdu.verify("exception")


def test_dangling_file_handle(tmp_path):
    """
    This tests the bug fix introduced in #533. Without the bug fix, this test
    will fail when running the test suite with pytest-openfiles.
    """
    import gc

    fits_filename = str(tmp_path / "dangling.fits")

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

    ctx._blocks.find_or_create_block_for_array(hdul[0].data, ctx)
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
    file_path = tmp_path / "test.fits"

    data = np.arange(100, dtype=np.float64).reshape(5, 20)
    data_view = data[:, :10]

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
    file_path = tmp_path / "test.fits"

    data = np.arange(100, dtype=np.float64).reshape(5, 20)
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

    data = np.arange(100, dtype=np.float64)
    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data)])
    with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
        af["view"] = hdul[-1].data.view(np.int64)
        with pytest.raises(
            ValueError,
            match=r"ASDF has only limited support for serializing views over arrays stored in FITS HDUs",
        ):
            af.write_to(file_path)


def test_hdu_link_independence(tmp_path):
    """
    As links between arrays and hdu items are made during
    saving, it's possible that if this goes wrong links
    might be made between multiple arrays and a single hdu.
    In this case, modifying one array will change memory
    shared with another array. This test creates a file
    with multiple arrays, writes it to a fits file,
    reads it back in and then modifies the contents of
    each array to check for this possible errort.
    """
    asdf_in_fits = create_asdf_in_fits("f4")
    # set all arrays to same values
    asdf_in_fits["model"]["sci"]["data"][:] = 0
    asdf_in_fits["model"]["dq"]["data"][:] = 0
    asdf_in_fits["model"]["err"]["data"][:] = 0

    fn0 = tmp_path / "test0.fits"

    # write out the asdf in fits file
    asdf_in_fits.write_to(str(fn0))

    with asdf.open(fn0, mode="r") as aif:
        # assign new values
        aif["model"]["sci"]["data"][:] = 1
        aif["model"]["dq"]["data"][:] = 2
        aif["model"]["err"]["data"][:] = 3

        assert np.all(aif["model"]["sci"]["data"] == 1)
        assert np.all(aif["model"]["dq"]["data"] == 2)
        assert np.all(aif["model"]["err"]["data"] == 3)


def test_array_view_different_layout(tmp_path):
    """
    A view over the FITS array with a different memory layout
    might end up corrupted when astropy.io.fits changes the
    array to C-contiguous and big-endian on write.
    """
    file_path = tmp_path / "test.fits"

    data = np.arange(100, dtype=np.float64).reshape(5, 20)
    data_view = data[:, :10]
    other_view = data_view[:, 10:]

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data_view)])
    with asdf.fits_embed.AsdfInFits(hdulist=hdul) as af:
        af["data"] = hdul[-1].data
        af["other"] = other_view
        with pytest.raises(
            ValueError,
            match=r"ASDF has only limited support for serializing views over arrays stored in FITS HDUs",
        ):
            af.write_to(file_path)


def test_resave_breaks_hdulist_tree_array_link(tmp_path):
    """
    Test that writing, reading and rewriting an AsdfInFits file
    maintains links between hdus and arrays in the asdf tree

    If the link is broken, data can be duplicated (exist both
    as a hdu and as an internal block in the asdf tree).

    See issues:
        https://github.com/asdf-format/asdf/issues/1232
        https://github.com/spacetelescope/jwst/issues/7354
        https://github.com/spacetelescope/jwst/issues/7274
    """
    file_path_1 = tmp_path / "test1.fits"
    file_path_2 = tmp_path / "test2.fits"

    af = create_asdf_in_fits("f4")
    af.write_to(file_path_1)

    with asdf.open(file_path_1) as af1:
        af1.write_to(file_path_2)

    # check that af1 (original write) and af2 (rewrite) do not contain internal blocks
    with fits.open(file_path_1) as af1, fits.open(file_path_2) as af2:
        for f in (af1, af2):
            block_bytes = f["ASDF"].data.tobytes().split(b"...")[1].strip()
            assert len(block_bytes) == 0
