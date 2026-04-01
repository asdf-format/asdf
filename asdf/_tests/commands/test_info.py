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


def test_info_command_blocks_show(capsys, test_data_path):
    """Verify blocks are printed when `--show-blocks` is passed."""

    file_path = test_data_path / "ndarray0.asdf"
    assert main.main_from_args(["info", "--show-blocks", str(file_path)]) == 0
    captured = capsys.readouterr()
    assert "Block #0" in captured.out


def test_info_command_blocks_hide(capsys, test_data_path):
    """Verify no block output is shown by default when the file contains blocks."""

    file_path = test_data_path / "ndarray0.asdf"
    assert main.main_from_args(["info", str(file_path)]) == 0
    captured = capsys.readouterr()
    assert "Block" not in captured.out


def test_info_command_no_blocks(capsys, test_data_path):
    """Verify no block output is shown even with `--show-blocks` if file contains no blocks."""

    file_path = test_data_path / "simple_inline_array0.asdf"
    assert main.main_from_args(["info", "--show-blocks", str(file_path)]) == 0
    captured = capsys.readouterr()
    assert "Block" not in captured.out
