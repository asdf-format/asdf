import io
import sys

import pytest

from asdf.commands import diff, main


@pytest.fixture(autouse=True)
def force_isatty(monkeypatch):
    def _isatty():
        return True

    monkeypatch.setattr(sys.stdout, "isatty", _isatty)
    yield


def _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False, ignore=None):
    iostream = io.StringIO()

    file_paths = [test_data_path / name for name in filenames]
    diff(file_paths, minimal=minimal, iostream=iostream, ignore=ignore)
    iostream.seek(0)

    result_path = test_data_path / result_file
    with open(result_path) as handle:
        assert handle.read() == iostream.read()


def test_diff(test_data_path):
    filenames = ["frames0.asdf", "frames1.asdf"]
    result_file = "frames.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False)


def test_diff_minimal(test_data_path):
    filenames = ["frames0.asdf", "frames1.asdf"]
    result_file = "frames_minimal.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=True)


@pytest.mark.parametrize(
    ("result_file", "ignore"),
    [
        ("frames_ignore_asdf_library.diff", ["asdf_library"]),
        ("frames_ignore_reference_frame.diff", ["frames[*].reference_frame"]),
        ("frames_ignore_both.diff", ["asdf_library", "frames[*].reference_frame"]),
    ],
)
def test_diff_ignore(test_data_path, result_file, ignore):
    filenames = ["frames0.asdf", "frames1.asdf"]
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False, ignore=ignore)


def test_diff_ndarray(test_data_path):
    filenames = ["ndarray0.asdf", "ndarray1.asdf"]
    result_file = "ndarrays.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False)


def test_diff_ndarray_in_list(test_data_path):
    filenames = ["ndarray_in_list0.asdf", "ndarray_in_list1.asdf"]
    result_file = "ndarray_in_list.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False)


def test_diff_block(test_data_path):
    filenames = ["block0.asdf", "block1.asdf"]
    result_file = "blocks.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False)


def test_diff_simple_inline_array(test_data_path):
    filenames = ["simple_inline_array0.asdf", "simple_inline_array1.asdf"]
    result_file = "simple_inline_array.diff"
    _assert_diffs_equal(test_data_path, filenames, result_file, minimal=False)


@pytest.mark.filterwarnings("ignore:unclosed file .*")
def test_file_not_found(test_data_path):
    # Try to open files that exist but are not valid asdf
    filenames = ["frames.diff", "blocks.diff"]
    with pytest.raises(
        RuntimeError,
        match=r"Does not appear to be a ASDF file.",
    ):
        diff([test_data_path / name for name in filenames], False)


def test_diff_command(test_data_path):
    filenames = ["frames0.asdf", "frames1.asdf"]
    path_strings = [str(test_data_path / name) for name in filenames]

    assert main.main_from_args(["diff", *path_strings]) == 0
