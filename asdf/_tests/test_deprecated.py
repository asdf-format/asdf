import sys

import pytest

from asdf.exceptions import AsdfDeprecationWarning


def test_asdf_stream_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="asdf.stream is deprecated"):
        if "asdf.stream" in sys.modules:
            del sys.modules["asdf.stream"]
        import asdf.stream  # noqa: F401


def test_asdf_asdf_SerializationContext_import_deprecation():
    with pytest.warns(AsdfDeprecationWarning, match="importing SerializationContext from asdf.asdf"):
        from asdf.asdf import SerializationContext  # noqa: F401
