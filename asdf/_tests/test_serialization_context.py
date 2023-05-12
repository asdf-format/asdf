import pytest

from asdf import get_config
from asdf._serialization_context import SerializationContext
from asdf.extension import ExtensionManager


def test_serialization_context():
    extension_manager = ExtensionManager([])
    context = SerializationContext("1.4.0", extension_manager, "file://test.asdf", None)
    assert context.version == "1.4.0"
    assert context.extension_manager is extension_manager
    assert context._extensions_used == set()

    extension = get_config().extensions[0]
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension.delegate)
    assert context._extensions_used == {extension}

    assert context.url == context._url == "file://test.asdf"

    with pytest.raises(TypeError, match=r"Extension must implement the Extension interface"):
        context._mark_extension_used(object())

    with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
        SerializationContext("0.5.4", extension_manager, None, None)
