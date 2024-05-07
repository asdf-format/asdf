import pytest

from asdf.commands import find_extensions
from asdf.versioning import supported_versions


@pytest.mark.parametrize("summary", [True, False])
@pytest.mark.parametrize("tags_only", [True, False])
def test_parameter_combinations(summary, tags_only):
    # Just confirming no errors:
    find_extensions(summary, tags_only)


@pytest.mark.parametrize("standard_version", supported_versions)
def test_builtin_extension_included(capsys, standard_version):
    find_extensions(True, False)
    captured = capsys.readouterr()
    assert f"core-{standard_version}" in captured.out
