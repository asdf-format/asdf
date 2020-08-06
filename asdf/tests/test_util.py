from asdf import util
from asdf.extension import BuiltinExtension


def test_is_primitive():
    for value in [None, "foo", 1, 1.39, 1 + 1j, True]:
        assert util.is_primitive(value) is True

    for value in [[], tuple(), {}, set()]:
        assert util.is_primitive(value) is False


def test_not_set():
    assert util.NotSet != None

    assert repr(util.NotSet) == "NotSet"


class SomeClass:
    class SomeInnerClass:
        pass


def test_get_class_name():
    assert util.get_class_name(SomeClass()) == "asdf.tests.test_util.SomeClass"
    assert util.get_class_name(SomeClass, instance=False) == "asdf.tests.test_util.SomeClass"
    assert util.get_class_name(SomeClass.SomeInnerClass()) == "asdf.tests.test_util.SomeClass.SomeInnerClass"
    assert util.get_class_name(SomeClass.SomeInnerClass, instance=False) == "asdf.tests.test_util.SomeClass.SomeInnerClass"


def test_get_class_name_override():
    assert util.get_class_name(BuiltinExtension, instance=False) == "asdf.extension.BuiltinExtension"


def test_patched_urllib_parse():
    assert "asdf" in util.patched_urllib_parse.uses_relative
    assert "asdf" in util.patched_urllib_parse.uses_netloc

    import urllib.parse
    assert urllib.parse is not util.patched_urllib_parse
    assert "asdf" not in urllib.parse.uses_relative
    assert "asdf" not in urllib.parse.uses_netloc
