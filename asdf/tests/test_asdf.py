import pytest

from asdf.asdf import is_asdf_file
from asdf.exceptions import AsdfWarning


@pytest.mark.parametrize("url,result", [
    ("http://example.com/some/path/to/file.asdf", True),
    ("https://example.com/some/path/to/file.asdf", True),
    ("http://example.com/some/path/to/file.fits", False),
    ("http://example.com/some/path/to/file.fits.gz", False),
    ("http://example.com/some/path/to/file.gz", False),
    ("http://example.com/some/path/to/file.zip", False),
])
def test_is_asdf_file_url(url, result):
    assert is_asdf_file(url) is result


@pytest.mark.parametrize("url", [
    "http://example.com/some/path/to/b5dbeef4-cc58-4290-939e-5c73041537fd",
    "http://example.com/some/path/to/file.txt",
    "https://example.com/some/path/to/file.txt",
])
def test_is_asdf_file_unrecognized_url_ext(url):
    with pytest.warns(AsdfWarning, match="does not include an obvious FITS or ASDF filename extension"):
        assert is_asdf_file(url) is True
