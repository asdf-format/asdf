import pytest

from asdf.commands import main


# The test file we're using here contains objects whose schemas
# have been dropped from the ASDF Standard.  We should select
# a new file once the locations of schemas are more stable.
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
