import pytest

from asdf._commands import main


@pytest.mark.parametrize("type_string", ("numpy.ndarray", "asdf.tags.core.ndarray.NDArrayType"))
def test_search_array(capsys, test_data_path, type_string):
    """
    Test that both the lazy and non-lazy classes work for searches for arrays.
    """
    file_path = test_data_path / "ndarray_in_list0.asdf"

    assert main.main_from_args(["search", str(file_path), "--type", type_string]) == 0

    captured = capsys.readouterr()
    assert "list" in captured.out
    assert "a (NDArrayType)" in captured.out
    assert "history" not in captured.out


@pytest.mark.parametrize("limit_rows", (True, False))
@pytest.mark.parametrize("limit_cols", (True, False))
def test_search_rendering(capsys, test_data_path, limit_rows, limit_cols):
    """
    Test that search respects the rendering parameters common with info.
    """
    file_path = test_data_path / "ndarray_in_list0.asdf"

    max_rows = 5
    max_cols = 25

    args = ["search", str(file_path)]
    if limit_rows:
        args += ["--max-rows", str(max_rows)]
    if limit_cols:
        args += ["--max-cols", str(max_cols)]

    assert main.main_from_args(args) == 0

    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    if limit_rows:
        assert len(lines) <= max_rows
    else:
        assert len(lines) > max_rows
    if limit_cols:
        assert all(len(line.rstrip()) <= max_cols for line in lines)
    else:
        assert any(len(line) > max_cols for line in lines)


# The test file contains a number of tags that aren't part of the standard.
# This is useful for these tests as we want to handle this case gracefully.
@pytest.mark.filterwarnings("ignore::asdf.exceptions.AsdfConversionWarning")
@pytest.mark.parametrize(
    "query_type, query, expected, not_expected",
    (
        ("key", "axes", "axes_names", "reference_frame"),
        ("key", "^axes_names$", "axes_names", "axes_order"),
        ("value", "ICRS", "ICRS", "FK4"),
        ("value", '["lon", "lat"]', "axes_names", "reference_frame"),
        ("value", '{"type": "ICRS"}', "reference_frame", "axes_names"),
        ("type", "int", "axes_order", "axes_names"),
        ("type", "float", "reference_frame", "axes_names"),
        ("type", "dict", "reference_frame", "axes_names"),
        ("type", "list", "axes_names", "asdf_library"),
    ),
)
def test_search_command(capsys, test_data_path, query_type, query, expected, not_expected):
    """
    Test that for a query and query_type search returns the expected value and doesn't
    return the not_expected value. These are all tailored to this particular file.
    """
    file_path = test_data_path / "frames0.asdf"

    assert main.main_from_args(["search", str(file_path), f"--{query_type}", query]) == 0

    captured = capsys.readouterr()
    assert expected in captured.out
    assert not_expected not in captured.out
