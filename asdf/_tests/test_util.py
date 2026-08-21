import contextlib
import io

import numpy as np
import pytest

import asdf
from asdf import generic_io, util
from asdf.exceptions import ChangingDefaultWarning
from asdf.util import changing_default


def test_not_set():
    assert util.NOT_SET is not None

    assert repr(util.NOT_SET) == "NotSet"

    assert util.NotSet is util.NOT_SET


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


def test_patched_urllib_parse():
    assert "asdf" in util._patched_urllib_parse.uses_relative
    assert "asdf" in util._patched_urllib_parse.uses_netloc

    import urllib.parse

    assert urllib.parse is not util._patched_urllib_parse
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

    with pytest.deprecated_call():
        fd = generic_io.get_file(OnlyHasAReadMethod(content))
    assert util.get_file_type(fd) == expected_type
    assert fd.read() == content


@pytest.mark.parametrize("input_type", ["filename", "binary_file", "generic_file"])
@pytest.mark.parametrize("tagged", [True, False])
def test_load_yaml(tmp_path, input_type, tagged):
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"a": np.zeros(3)}).write_to(fn)

    if input_type == "filename":
        init = fn
        ctx = contextlib.nullcontext()
    elif input_type == "binary_file":
        init = open(fn, "rb")
        ctx = init
    elif input_type == "generic_file":
        init = generic_io.get_file(fn, "r")
        ctx = init

    with ctx:
        tree = util.load_yaml(init, tagged=tagged)
    if tagged:
        assert isinstance(tree["a"], asdf.tagged.TaggedDict)
    else:
        assert not isinstance(tree["a"], asdf.tagged.TaggedDict)


@pytest.mark.parametrize("tagged", [True, False])
def test_load_yaml_recursion(tmp_path, tagged):
    fn = tmp_path / "test.asdf"
    tree = {}
    tree["d"] = {}
    tree["d"]["d"] = tree["d"]
    tree["l"] = []
    tree["l"].append(tree["l"])
    asdf.AsdfFile(tree).write_to(fn)
    tree = util.load_yaml(fn, tagged=tagged)
    assert tree["d"]["d"] is tree["d"]
    assert tree["l"][0] is tree["l"]


@pytest.mark.parametrize("tagged", [True, False])
def test_load_yaml_recursion_with_tags(tagged):
    contents = b"""#ASDF 1.0.0
#ASDF_STANDARD 1.6.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.1.0
o: &id001 !some/tag-1.0.0
  inverse: !some/tag-1.0.0
    inverse: *id001
l: &id002 !some/tag-1.0.0
  - *id002
..."""
    tree = util.load_yaml(io.BytesIO(contents), tagged=tagged)
    assert tree["o"] is tree["o"]["inverse"]["inverse"]
    assert tree["l"] is tree["l"][0]


# Need to enable ChangingDefaultWarning exceptions since they are off by default
@pytest.mark.filterwarnings("error::asdf.exceptions.ChangingDefaultWarning")
def test_changing_default():
    """Test that changing_default works as expected."""

    class CustomWarning(ChangingDefaultWarning): ...

    class Config:
        def __init__(self):
            self._value = 1
            self._other = None

        @changing_default(2, CustomWarning)
        @property
        def value(self) -> int:
            return self._value

        @value.setter
        def value(self, value: int) -> None:
            self._value = value

        @value.deleter
        def value(self) -> None:
            self._value = 1

        @changing_default("foo")
        @property
        def other(self) -> str | None:
            return self._other

        @other.setter
        def other(self, value: str) -> None:
            self._other = value

    cfg = Config()

    # Verify accessing the value emits the custom warning
    with pytest.warns(CustomWarning):
        assert cfg.value == 1

    # Verify accessing the value with no warning specified falls back to the default warning
    with pytest.warns(ChangingDefaultWarning):
        assert cfg.other is None

    cfg.value = 2
    cfg.other = "bar"

    # Verify accessing the values once they've been manually set doesn't emit a warning
    assert cfg.value == 2
    assert cfg.other == "bar"

    # Verify warning doesn't trigger even if value is deleted
    del cfg.value
    assert cfg.value == 1

    class Subconfig(Config):
        @Config.value.getter
        def value(self) -> int:  # pyrefly: ignore [bad-override]
            return self._value + 1

    # Verify that overriding property getters works correctly
    cfg = Subconfig()
    cfg.value = 3
    assert cfg.value == 4
