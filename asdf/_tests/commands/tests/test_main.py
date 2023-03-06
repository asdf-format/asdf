import pytest

from asdf.commands import main


def test_help():
    # Just a smoke test, really
    main.main_from_args(["help"])


def test_invalid_command():
    with pytest.raises(SystemExit) as e:
        main.main([])
    assert e.value.code == 2

    with pytest.raises(SystemExit) as e:
        main.main(["foo"])
    if isinstance(e.value, int):
        assert e.value == 2
    else:
        assert e.value.code == 2
