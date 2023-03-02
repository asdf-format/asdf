from functools import partial

import pytest

from asdf._tests import _helpers as helpers
from asdf.commands import main

from . import data as test_data

get_test_data_path = partial(helpers.get_test_data_path, module=test_data)


# The test file we're using here contains objects whose schemas
# have been dropped from the ASDF Standard.  We should select
# a new file once the locations of schemas are more stable.
@pytest.mark.filterwarnings("ignore::asdf.exceptions.AsdfConversionWarning")
def test_info_command(capsys):
    file_path = get_test_data_path("frames0.asdf")

    assert main.main_from_args(["info", file_path]) == 0
    captured = capsys.readouterr()
    assert "root" in captured.out
    assert "frames" in captured.out
    original_len = len(captured.out.split("\n"))

    assert main.main_from_args(["info", "--max-rows", str(original_len - 5), file_path]) == 0
    captured = capsys.readouterr()
    assert "root" in captured.out
    assert "frames" in captured.out
    new_len = len(captured.out.split("\n"))
    assert new_len < original_len
