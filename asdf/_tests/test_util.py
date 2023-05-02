import io

import pytest

from asdf import generic_io, util
from asdf.extension._legacy import BuiltinExtension


def test_is_primitive():
    for value in [None, "foo", 1, 1.39, 1 + 1j, True]:
        assert util.is_primitive(value) is True

    for value in [[], (), {}, set()]:
        assert util.is_primitive(value) is False


def test_not_set():
    assert util.NotSet is not None

    assert repr(util.NotSet) == "NotSet"


class SomeClass:
    class SomeInnerClass:
        pass


def test_get_class_name():
    assert util.get_class_name(SomeClass()) == "asdf._tests.test_util.SomeClass"
    assert util.get_class_name(SomeClass, instance=False) == "asdf._tests.test_util.SomeClass"
    assert util.get_class_name(SomeClass.SomeInnerClass()) == "asdf._tests.test_util.SomeClass.SomeInnerClass"
    assert (
        util.get_class_name(SomeClass.SomeInnerClass, instance=False)
        == "asdf._tests.test_util.SomeClass.SomeInnerClass"
    )


def test_get_class_name_override():
    assert util.get_class_name(BuiltinExtension, instance=False) == "asdf.extension.BuiltinExtension"


def test_patched_urllib_parse():
    assert "asdf" in util.patched_urllib_parse.uses_relative
    assert "asdf" in util.patched_urllib_parse.uses_netloc

    import urllib.parse

    assert urllib.parse is not util.patched_urllib_parse
    assert "asdf" not in urllib.parse.uses_relative
    assert "asdf" not in urllib.parse.uses_netloc


@pytest.mark.parametrize(
    ("pattern", "uri", "result"),
    [
        ("asdf://somewhere.org/tags/foo-1.0", "asdf://somewhere.org/tags/foo-1.0", True),
        ("asdf://somewhere.org/tags/foo-1.0", "asdf://somewhere.org/tags/bar-1.0", False),
        ("asdf://somewhere.org/tags/foo-*", "asdf://somewhere.org/tags/foo-1.0", True),
        ("asdf://somewhere.org/tags/foo-*", "asdf://somewhere.org/tags/bar-1.0", False),
        ("asdf://somewhere.org/tags/foo-*", "asdf://somewhere.org/tags/foo-extras/bar-1.0", False),
        ("asdf://*/tags/foo-*", "asdf://anywhere.org/tags/foo-4.9", True),
        ("asdf://*/tags/foo-*", "asdf://anywhere.org/tags/bar-4.9", False),
        ("asdf://*/tags/foo-*", "asdf://somewhere.org/tags/foo-extras/bar-4.9", False),
        ("asdf://**/*-1.0", "asdf://somewhere.org/tags/foo-1.0", True),
        ("asdf://**/*-1.0", "asdf://somewhere.org/tags/foo-2.0", False),
        ("asdf://**/*-1.0", "asdf://somewhere.org/tags/foo-extras/bar-1.0", True),
        ("asdf://**/*-1.0", "asdf://somewhere.org/tags/foo-extras/bar-2.0", False),
        ("asdf://somewhere.org/tags/foo-*", None, False),
        ("**", None, False),
    ],
)
def test_uri_match(pattern, uri, result):
    assert util.uri_match(pattern, uri) is result


@pytest.mark.parametrize(
    ("content", "expected_type"),
    [
        (b"#ASDF blahblahblah", util.FileType.ASDF),
        (b"SIMPLE = T blah blah blah blah", util.FileType.FITS),
        (b"SIMPLY NOT A FITS FILE", util.FileType.UNKNOWN),
        (b"#ASDQ", util.FileType.UNKNOWN),
    ],
)
def test_get_file_type(content, expected_type):
    fd = generic_io.get_file(io.BytesIO(content))
    assert util.get_file_type(fd) == expected_type
    # Confirm that no content was lost
    assert fd.read() == content

    # We've historically had a problem detecting file type
    # of generic_io.InputStream:
    class OnlyHasAReadMethod:
        def __init__(self, content):
            self._fd = io.BytesIO(content)

        def read(self, size=-1):
            return self._fd.read(size)

    fd = generic_io.get_file(OnlyHasAReadMethod(content))
    assert util.get_file_type(fd) == expected_type
    assert fd.read() == content


def test_minversion():
    import numpy as np
    import yaml

    good_versions = ["1.16", "1.16.1", "1.16.0.dev", "1.16dev"]
    bad_versions = ["100000", "100000.2rc1"]
    for version in good_versions:
        assert util.minversion(np, version)
        assert util.minversion("numpy", version)
    for version in bad_versions:
        assert not util.minversion(np, version)
        assert not util.minversion("numpy", version)

    assert util.minversion(yaml, "3.1")
    assert util.minversion("yaml", "3.1")
