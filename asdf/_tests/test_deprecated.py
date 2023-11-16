import sys

import pytest

import asdf
from asdf.exceptions import AsdfDeprecationWarning


def test_asdf_stream_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.stream is deprecated"):
        if "asdf.stream" in sys.modules:
            del sys.modules["asdf.stream"]
        import asdf.stream  # noqa: F401


def test_asdf_asdf_SerializationContext_import_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="importing SerializationContext from asdf.asdf"):
        from asdf.asdf import SerializationContext  # noqa: F401


def test_asdf_util_human_list_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.human_list is deprecated"):
        asdf.util.human_list("a")


def test_asdf_util_resolve_name_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.resolve_name is deprecated"):
        asdf.util.resolve_name("asdf.AsdfFile")


def test_asdf_util_minversion_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.minversion is deprecated"):
        asdf.util.minversion("yaml", "3.1")


def test_asdf_util_iter_subclasses_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.util.iter_subclasses is deprecated"):
        list(asdf.util.iter_subclasses(asdf.AsdfFile))


def test_asdf_asdf_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.asdf is deprecated"):
        if "asdf.asdf" in sys.modules:
            del sys.modules["asdf.asdf"]
        import asdf.asdf  # noqa: F401
