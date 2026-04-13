import pytest

from asdf._commands import main


# The test file contains a number of tags that aren't part of the standard.
# This is useful for these tests as we want to handle this case gracefully.
@pytest.mark.filterwarnings("ignore::asdf.exceptions.AsdfConversionWarning")
def test_info_command(capsys, test_data_path):
    file_path = test_data_path / "frames0.asdf"

    assert main.main_from_args(["info", str(file_path)]) == 0
    captured = capsys.readouterr()
    assert "root" in captured.out
    assert "frames" in captured.out
    original_len = len(captured.out.split("\n"))

    assert main.main_from_args(["info", "--max-rows", str(original_len - 5), str(file_path)]) == 0
    captured = capsys.readouterr()
    assert "root" in captured.out
    assert "frames" in captured.out
    new_len = len(captured.out.split("\n"))
    assert new_len < original_len


@pytest.mark.parametrize("filename", ["ndarray0.asdf", "ndarray2.asdf", "simple_inline_array0.asdf"])
def test_info_command_blocks_show(capsys, test_data_path, filename, snapshot):
    """Verify block output for files with different numbers and types of blocks."""

    file_path = test_data_path / filename
    assert main.main_from_args(["info", "--show-blocks", str(file_path)]) == 0
    captured = capsys.readouterr()
    # Run `pytest --snapshot-update` to update stored snapshot
    assert captured.out == snapshot


def test_info_command_blocks_hide(capsys, test_data_path, snapshot):
    """Verify no block output is shown by default when the file contains blocks."""

    file_path = test_data_path / "ndarray0.asdf"
    assert main.main_from_args(["info", str(file_path)]) == 0
    captured = capsys.readouterr()
    # Run `pytest --snapshot-update` to update stored snapshot
    assert captured.out == snapshot
