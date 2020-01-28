from asdf import util


def test_is_primitive():
    for value in [None, "foo", 1, 1.39, 1 + 1j, True]:
        assert util.is_primitive(value) is True

    for value in [[], tuple(), {}, set()]:
        assert util.is_primitive(value) is False


def test_not_set():
    assert util.NotSet != None

    assert repr(util.NotSet) == "NotSet"
