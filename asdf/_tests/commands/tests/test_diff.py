import io
from functools import partial

import pytest

from asdf._tests import _helpers as helpers
from asdf.commands import diff, main

from . import data as test_data

get_test_data_path = partial(helpers.get_test_data_path, module=test_data)


def _assert_diffs_equal(filenames, result_file, minimal=False, ignore=None):
    iostream = io.StringIO()

    file_paths = [get_test_data_path(name) for name in filenames]
    diff(file_paths, minimal=minimal, iostream=iostream, ignore=ignore)
    iostream.seek(0)

    result_path = get_test_data_path(result_file)
    with open(result_path) as handle:
        assert handle.read() == iostream.read()


def test_diff():
    filenames = ["frames0.asdf", "frames1.asdf"]
    result_file = "frames.diff"
    _assert_diffs_equal(filenames, result_file, minimal=False)


def test_diff_minimal():
    filenames = ["frames0.asdf", "frames1.asdf"]
    result_file = "frames_minimal.diff"
    _assert_diffs_equal(filenames, result_file, minimal=True)


@pytest.mark.parametrize(
    ("result_file", "ignore"),
    [
        ("frames_ignore_asdf_library.diff", ["asdf_library"]),
        ("frames_ignore_reference_frame.diff", ["frames[*].reference_frame"]),
        ("frames_ignore_both.diff", ["asdf_library", "frames[*].reference_frame"]),
    ],
)
def test_diff_ignore(result_file, ignore):
    filenames = ["frames0.asdf", "frames1.asdf"]
    _assert_diffs_equal(filenames, result_file, minimal=False, ignore=ignore)


def test_diff_block():
    filenames = ["block0.asdf", "block1.asdf"]
    result_file = "blocks.diff"
    _assert_diffs_equal(filenames, result_file, minimal=False)


def test_diff_simple_inline_array():
    filenames = ["simple_inline_array0.asdf", "simple_inline_array1.asdf"]
    result_file = "simple_inline_array.diff"
    _assert_diffs_equal(filenames, result_file, minimal=False)


@pytest.mark.filterwarnings("ignore:unclosed file .*")
def test_file_not_found():
    # Try to open files that exist but are not valid asdf
    filenames = ["frames.diff", "blocks.diff"]
    with pytest.raises(
        RuntimeError,
        match=r"Input object does not appear to be an ASDF file or a FITS with ASDF extension",
    ):
        diff([get_test_data_path(name) for name in filenames], False)


def test_diff_command():
    filenames = ["frames0.asdf", "frames1.asdf"]
    paths = [get_test_data_path(name) for name in filenames]

    assert main.main_from_args(["diff", *paths]) == 0
