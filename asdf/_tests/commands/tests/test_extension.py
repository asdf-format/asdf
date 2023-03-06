import pytest

from asdf.commands import find_extensions


@pytest.mark.parametrize("summary", [True, False])
@pytest.mark.parametrize("tags_only", [True, False])
def test_parameter_combinations(summary, tags_only):
    # Just confirming no errors:
    find_extensions(summary, tags_only)


def test_builtin_extension_included(capsys):
    find_extensions(True, False)
    captured = capsys.readouterr()
    assert "asdf.extension.BuiltinExtension" in captured.out
