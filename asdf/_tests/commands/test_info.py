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


@pytest.mark.parametrize("hide_blocks", (True, False))
def test_hide_blocks(capsys, test_data_path, hide_blocks):
    file_path = test_data_path / "ndarray0.asdf"

    args = ["info", str(file_path)]
    if hide_blocks:
        args.append("--hide-blocks")
    assert main.main_from_args(args) == 0
    captured = capsys.readouterr()
    if hide_blocks:
        assert "Block 0:" not in captured.out
    else:
        assert "Block 0:" in captured.out
