import sys

import pytest

import asdf
import asdf._types
import asdf.extension
import asdf.testing.helpers
from asdf._types import CustomType
from asdf.exceptions import AsdfDeprecationWarning


def test_custom_type_warning():
    with pytest.warns(AsdfDeprecationWarning, match=r"^.* subclasses the deprecated CustomType .*$"):

        class NewCustomType(CustomType):
            pass


def test_asdf_type_format_tag():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.types.format_tag is deprecated"):
        asdf._types.format_tag
    asdf.testing.helpers.format_tag


def test_asdf_stream_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.stream is deprecated"):
        if "asdf.stream" in sys.modules:
            del sys.modules["asdf.stream"]
        import asdf.stream  # noqa: F401


def test_asdf_asdf_SerializationContext_import_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="importing SerializationContext from asdf.asdf"):
        from asdf.asdf import SerializationContext  # noqa: F401
